"""Versiya müqayisəsi: qarşı tərəf yeni versiya göndərəndə nə dəyişdi, təkliflərimizin taleyi nədir.

1. Bəndlər **mətnə görə** uyğunlaşdırılır (nömrələmə sürüşsə də): eyni mətn — "eyni";
   dəyişiklik bloklarında ən oxşar cütlər — "dəyişib"; qalanlar — "silinib" / "əlavə".
2. Hər təklifimiz üçün status: qəbul edilib / güzəşt qəbul edilib / qismən / rədd edilib / ...
3. Word: köhnə versiyadan yeniyə dəyişikliklər track changes kimi (söz səviyyəsində).
"""

import io
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from docx.document import Document

from agent.numbering import paragraph_lines
from agent.redliner import TOKEN, Redliner, clause_bodies, merge_small_gaps
from agent.verifier import Finding

PAIR_MIN = 0.3  # bundan az oxşar bəndlər "dəyişib" yox, "silinib + əlavə" sayılır


@dataclass
class ClauseChange:
    status: str  # eyni | dəyişib | silinib | əlavə
    old_key: str | None
    new_key: str | None
    old_text: str = ""
    new_text: str = ""


@dataclass
class ProposalStatus:
    finding: Finding
    status: str
    new_key: str | None = None


STOP = {"və", "ilə", "üçün", "bu", "bir", "the", "and", "of", "и", "в"}


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _body(text: str) -> str:
    """Müqayisə üçün bəndin mətni: imza / rekvizit cədvəlinin sətirləri (" | ") atılır —
    onlar hər versiyada sonuncu bəndə yapışır və uyğunlaşdırmanı çaşdırır."""
    return "\n".join(line for line in text.split("\n") if " | " not in line)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _words(a), _words(b), autojunk=False).ratio()


def align(old: dict[str, str], new: dict[str, str]) -> list[ClauseChange]:
    """Köhnə və yeni bəndləri uyğunlaşdırır, yeni versiyanın sırası ilə qaytarır."""
    old_items = [(k, _body(t)) for k, t in old.items()]
    new_items = [(k, _body(t)) for k, t in new.items()]
    norm = lambda text: " ".join(_words(text))
    matcher = SequenceMatcher(
        None, [norm(t) for _, t in old_items], [norm(t) for _, t in new_items], autojunk=False
    )
    out: list[ClauseChange] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        olds, news = old_items[i1:i2], new_items[j1:j2]
        if tag == "equal":
            out += [
                ClauseChange("eyni", o[0], n[0], o[1], n[1])
                for o, n in zip(olds, news, strict=True)
            ]
            continue
        # dəyişiklik bloku: ən oxşar cütləri tap (acgöz), qalanlar silinib / əlavə
        pairs = sorted(
            (
                (similarity(o[1], n[1]), a, b)
                for a, o in enumerate(olds)
                for b, n in enumerate(news)
            ),
            reverse=True,
        )
        used_old, used_new, matched = set(), set(), {}
        for score, a, b in pairs:
            if score >= PAIR_MIN and a not in used_old and b not in used_new:
                used_old.add(a), used_new.add(b)
                matched[b] = a
        block = []
        for b, (key, text) in enumerate(news):
            if b in matched:
                o = olds[matched[b]]
                block.append(ClauseChange("dəyişib", o[0], key, o[1], text))
            else:
                block.append(ClauseChange("əlavə", None, key, "", text))
        # silinənlər köhnə mövqeyinə yaxın yerə
        for a, (key, text) in enumerate(olds):
            if a not in used_old:
                position = sum(
                    1 for c in block if c.old_key and list(old).index(c.old_key) < i1 + a
                )
                block.insert(position, ClauseChange("silinib", key, None, text, ""))
        out += block
    return out


def track(findings: list[Finding], changes: list[ClauseChange]) -> list[ProposalStatus]:
    """Hər təklifimiz yeni versiyada qəbul edilibmi?"""
    by_old = {c.old_key: c for c in changes if c.old_key}
    candidates = [c for c in changes if c.new_key]
    out = []
    for f in findings:
        if f.tip == "catismayan":
            fresh = [c for c in candidates if c.status in ("əlavə", "dəyişib")]
            best = max(fresh, key=lambda c: similarity(c.new_text, f.teklif), default=None)
            if best and similarity(best.new_text, f.teklif) >= 0.6:
                out.append(ProposalStatus(f, "qəbul edilib", best.new_key))
                continue
            topic = set(_words(f.basliq)) - STOP  # "Fors-major" → yeni bənddə eyni açar sözlər
            related = [c for c in fresh if topic & set(_words(c.new_text))]
            if related:
                closest = max(related, key=lambda c: similarity(c.new_text, f.teklif))
                out.append(ProposalStatus(f, "qismən qəbul edilib", closest.new_key))
            else:
                out.append(ProposalStatus(f, "əlavə edilməyib"))
            continue

        change = by_old.get(f.bend_no)
        if change is None:
            continue
        if not f.teklif:  # bəndin silinməsini təklif etmişdik
            status = {"silinib": "qəbul edilib", "eyni": "rədd edilib"}.get(
                change.status, "başqa cür dəyişdirilib"
            )
            out.append(ProposalStatus(f, status, change.new_key))
            continue

        def best_match(text: str) -> tuple[float, ClauseChange | None]:
            if not text:
                return 0.0, None
            scored = [(similarity(c.new_text, text), c) for c in candidates]
            return max(scored, key=lambda x: x[0], default=(0.0, None))

        ideal, ideal_at = best_match(f.teklif)
        compromise, compromise_at = best_match(f.guzest)
        if ideal >= 0.85:
            out.append(ProposalStatus(f, "qəbul edilib", ideal_at.new_key))
        elif compromise >= 0.85:
            out.append(ProposalStatus(f, "güzəşt variantı qəbul edilib", compromise_at.new_key))
        elif change.status == "eyni":
            out.append(ProposalStatus(f, "rədd edilib", change.new_key))
        elif change.status == "dəyişib" and similarity(change.new_text, f.teklif) >= 0.5:
            out.append(ProposalStatus(f, "qismən qəbul edilib", change.new_key))
        elif change.status == "silinib":
            out.append(ProposalStatus(f, "bənd silinib", None))
        else:
            out.append(ProposalStatus(f, "başqa cür dəyişdirilib", change.new_key))
    return out


def diff_markdown(old: str, new: str) -> str:
    """Streamlit üçün söz səviyyəsində diff: silinən — qırmızı üstündən xətt, əlavə — yaşıl."""

    def esc(text: str) -> str:
        return re.sub(r"([\\`*_{}\[\]<>#+\-!|~:$])", r"\\\1", text)

    a, b = TOKEN.findall(old), TOKEN.findall(new)
    parts = []
    for tag, i1, i2, j1, j2 in merge_small_gaps(
        SequenceMatcher(None, a, b, autojunk=False).get_opcodes(), a
    ):
        if tag == "equal":
            parts.append(esc("".join(a[i1:i2])))
            continue
        removed, added = "".join(a[i1:i2]).strip(), "".join(b[j1:j2]).strip()
        if removed:
            parts.append(f" :red[~~{esc(removed)}~~] ")
        if added:
            parts.append(f" :green[**{esc(added)}**] ")
    return "".join(parts)


def redline(old_document: Document, changes: list[ClauseChange]) -> bytes:
    """Köhnə versiya üzərində yeni versiyaya qədər dəyişikliklər — track changes (şərhsiz)."""
    editor = Redliner(old_document, comments=False, author="Yeni versiya (qarşı tərəf)")
    pairs = paragraph_lines(old_document)
    paragraphs = [p for p, _ in pairs]
    spans = clause_bodies([line for _, line in pairs])

    anchor = paragraphs[-1] if paragraphs else None
    for change in changes:
        if change.old_key in spans:
            anchor = paragraphs[spans[change.old_key][-1]]
        if change.status == "dəyişib" and change.old_key in spans:
            new_text = change.new_text.split("\n")[0]
            editor.replace_clause(
                [paragraphs[i] for i in spans[change.old_key]], change.old_key, new_text
            )
        elif change.status == "silinib" and change.old_key in spans:
            editor.replace_clause(
                [paragraphs[i] for i in spans[change.old_key]], change.old_key, ""
            )
        elif change.status == "əlavə" and anchor is not None:
            label = change.new_key if change.new_key and change.new_key[0].isdigit() else ""
            anchor = editor.add_clause(anchor, label, change.new_text)

    out = io.BytesIO()
    old_document.save(out)
    return out.getvalue()
