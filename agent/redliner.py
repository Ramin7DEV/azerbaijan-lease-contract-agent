"""Düzəlişləri DOCX-ə Word-un track changes formatında yazır.

python-docx track changes bilmir, ona görə <w:del> / <w:ins> elementlərini özümüz qururuq:
köhnə mətn silinmiş kimi, təklif isə əlavə edilmiş kimi görünür, vəkil hər birini Word-da
qəbul və ya rədd edir. Hər düzəlişə problemin izahı və qanun maddəsi ilə şərh (comment) qoşulur.

Təmiz versiya (clean=True): eyni düzəlişlər qurulur, sonra hamısı qəbul edilir — şərhsiz,
izsiz, müştəriyə və ya qarşı tərəfə göndərməyə hazır mətn.
"""

import copy
import io
import itertools
import re
from datetime import UTC, datetime
from difflib import SequenceMatcher

import docx
from docx.document import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from agent import parser
from agent.numbering import paragraph_lines
from agent.score import score
from agent.verifier import Finding, Result

AUTHOR = "Müqavilə agenti"
# Köhnə və yeni mətn bu qədərdən az oxşardırsa, söz-söz yox, bənd tam əvəz olunur —
# əks halda redline qırıq-qırıq, oxunmaz olur.
MIN_SIMILARITY = 0.5
TOKEN = re.compile(r"\s+|\w+|[^\w\s]")
INITIALS = "MA"
TIP_LABEL = {
    "qanuna_zidd": "Qanuna zidd",
    "birterefli": "Birtərəfli şərt",
    "catismayan": "Çatışmayan bənd",
}


def merge_small_gaps(opcodes: list, old: list[str]) -> list:
    """İki dəyişiklik arasında yalnız boşluq və ya bir söz qalıbsa, onları bir blokda birləşdirir.

    Əks halda redline "[-Təminat-]{+İcarəyə+} [-pulu-]{+verən+}" kimi söz-söz dama olur.
    """
    ops = [list(op) for op in opcodes]
    merged = True
    while merged:
        merged = False
        for k in range(1, len(ops) - 1):
            tag, i1, i2, _, _ = ops[k]
            words = [t for t in old[i1:i2] if not t.isspace()]
            if tag == "equal" and len(words) <= 1 and ops[k - 1][0] != "equal" != ops[k + 1][0]:
                before, after = ops[k - 1], ops[k + 1]
                ops[k - 1 : k + 2] = [["replace", before[1], after[2], before[3], after[4]]]
                merged = True
                break
    return [tuple(op) for op in ops]


class Redliner:
    def __init__(self, document: Document, comments: bool = True, author: str = AUTHOR):
        self.doc = document
        self.comments = comments
        self.author = author
        self.date = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.ids = itertools.count(9001)  # w:ins / w:del üçün unikal id

    # --- aşağı səviyyəli XML ---

    def _mark(self, tag: str):
        element = OxmlElement(tag)
        element.set(qn("w:id"), str(next(self.ids)))
        element.set(qn("w:author"), self.author)
        element.set(qn("w:date"), self.date)
        return element

    def _delete_runs(self, runs: list) -> None:
        """Run-ları <w:del> içinə köçürür; mətn <w:delText> olur."""
        if not runs:
            return
        wrapper = self._mark("w:del")
        runs[0].addprevious(wrapper)
        for r in runs:
            for t in r.findall(qn("w:t")):
                t.tag = qn("w:delText")
            for t in r.findall(qn("w:instrText")):
                t.tag = qn("w:delInstrText")
            wrapper.append(r)

    def _insert_run(self, after, text: str, rpr=None, bold: bool = False) -> Run:
        """`after` elementindən sonra <w:ins><w:r>text</w:r></w:ins> qoyur."""
        wrapper = self._mark("w:ins")
        r = OxmlElement("w:r")
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
        wrapper.append(r)
        after.addnext(wrapper)
        run = Run(r, None)
        run.text = text  # \n → <w:br/>, \t → <w:tab/>
        if bold:
            run.bold = True
        return run

    def _mark_paragraph(self, p, tag: str) -> None:
        """Abzas işarəsini silinmiş (w:del) və ya əlavə edilmiş (w:ins) kimi qeyd edir."""
        ppr = p.get_or_add_pPr()
        rpr = ppr.find(qn("w:rPr"))
        if rpr is None:
            rpr = OxmlElement("w:rPr")
            ppr.append(rpr)
        rpr.insert(0, self._mark(tag))  # sxemə görə rPr-ın ilk uşağı olmalıdır

    @staticmethod
    def _split_run(r, offset: int):
        """Run-ı `offset` simvolda ikiyə bölür, ikinci hissəni qaytarır."""
        text = Run(r, None).text
        tail = copy.deepcopy(r)
        r.addnext(tail)
        Run(r, None).text = text[:offset]
        Run(tail, None).text = text[offset:]
        return tail

    # --- bəndlər ---

    def replace_clause(self, paragraphs: list[Paragraph], key: str, new_text: str) -> list[Run]:
        """Bəndin mətnini silir, yerinə yenisini yazır. Nömrə ("3.3.") toxunulmaz qalır.

        Şərhin bağlanacağı run-ları qaytarır.
        """
        first = paragraphs[0]._p
        runs = first.xpath("./w:r")
        text = "".join(Run(r, None).text for r in runs)

        number = key.rstrip("'")
        m = parser.CLAUSE.match(new_text)
        if m and m[1] == number:  # model nömrəni təkrarlayıbsa
            new_text = m[2]

        # Nömrə mətnin içindədirsə ("3.3. İcarəçi..."), onu saxlayırıq. Avtomatik nömrədə
        # (Word özü qoyur) mətn "3 (üç) aylıq..." ola bilər — bu, nömrə deyil.
        match = parser.CLAUSE.match(text)
        prefix = match.start(2) if match and match[1] == number else 0

        kept, pos = [], 0
        for r in list(runs):
            length = len(Run(r, None).text)
            if pos + length <= prefix:
                kept.append(r)
            elif pos < prefix:
                kept.append(r)
                self._split_run(r, prefix - pos)
            pos += length
        to_delete = [r for r in first.xpath("./w:r") if r not in kept]

        if new_text and len(paragraphs) == 1 and to_delete:
            after = kept[-1] if kept else first.get_or_add_pPr()
            changed = self._diff_replace(to_delete, after, new_text)
            if changed:
                return [Run(kept[-1], paragraphs[0])] if kept else changed

        rpr = to_delete[0].find(qn("w:rPr")) if to_delete else None
        self._delete_runs(to_delete)
        last = (
            first.xpath("./w:del")[-1]
            if to_delete
            else (kept[-1] if kept else first.get_or_add_pPr())
        )

        anchor = [Run(kept[-1], paragraphs[0])] if kept else []
        if new_text:
            inserted = self._insert_run(last, new_text, rpr)
            anchor = anchor or [inserted]
        elif not kept:
            anchor = []

        for p in paragraphs[1:]:  # bəndin davamı olan abzaslar tam silinir
            self._delete_runs(p._p.xpath("./w:r"))
            self._mark_paragraph(p._p, "w:del")

        if not new_text:  # bəndin tam çıxarılması: nömrə də silinir, şərh silinən mətnə bağlanır
            self._delete_runs(kept)
            self._mark_paragraph(first, "w:del")
            anchor = [Run(r, paragraphs[0]) for r in first.xpath("./w:del/w:r")][:1]
        return anchor

    def _diff_replace(self, runs: list, after, new_text: str) -> list[Run] | None:
        """Söz səviyyəsində redline: yalnız dəyişən sözlər silinir / əlavə olunur.

        `runs` — bəndin (nömrədən sonrakı) run-ları, `after` — onlardan əvvəlki element.
        Mətnlər çox fərqlidirsə, None qaytarır (çağıran bəndi tam əvəz edir).
        Şərhin bağlanacağı run-ları qaytarır.
        """
        old_text = "".join(Run(r, None).text for r in runs)
        old, new = TOKEN.findall(old_text), TOKEN.findall(new_text)
        matcher = SequenceMatcher(None, old, new, autojunk=False)
        if matcher.ratio() < MIN_SIMILARITY:
            return None

        starts = [0]  # hər tokenin simvol mövqeyi
        for token in old:
            starts.append(starts[-1] + len(token))
        opcodes = merge_small_gaps(matcher.get_opcodes(), old)

        # run-ları dəyişiklik sərhədlərində böl ki, hər run tam bir hissəyə düşsün
        cuts = sorted({starts[i] for _, i1, i2, _, _ in opcodes for i in (i1, i2)})
        pieces, pos = [], 0
        for r in runs:
            length = len(Run(r, None).text)
            inner = [c - pos for c in cuts if pos < c < pos + length]
            for offset in reversed(inner):
                self._split_run(r, offset)
            piece = r
            for _ in range(len(inner) + 1):
                text_len = len(Run(piece, None).text)
                pieces.append((pos, pos + text_len, piece))
                pos += text_len
                piece = piece.getnext()

        anchor, last, rpr = [], after, runs[0].find(qn("w:rPr"))
        for tag, i1, i2, j1, j2 in opcodes:
            segment = [r for start, end, r in pieces if starts[i1] <= start and end <= starts[i2]]
            segment = [r for r in segment if Run(r, None).text]
            if segment:
                rpr = segment[0].find(qn("w:rPr"))
            if tag == "equal":
                last = segment[-1] if segment else last
                anchor = anchor or [Run(r, None) for r in segment[:1]]
                continue
            if tag in ("delete", "replace") and segment:
                self._delete_runs(segment)
                last = segment[0].getparent()  # <w:del>
            if tag in ("insert", "replace"):
                inserted = self._insert_run(last, "".join(new[j1:j2]), rpr)
                last = inserted._r.getparent()  # <w:ins>
                anchor = anchor or [inserted]
        return anchor

    def add_clause(self, after: Paragraph, title: str, text: str) -> Paragraph:
        """`after`-dən sonra yeni (əlavə edilmiş) abzas qoyur: qalın başlıq + mətn."""
        p = OxmlElement("w:p")
        ppr = after._p.pPr
        if ppr is not None:
            ppr = copy.deepcopy(ppr)
            for child in ppr.findall(qn("w:numPr")) + ppr.findall(qn("w:rPr")):
                ppr.remove(child)
            p.append(ppr)
        after._p.addnext(p)
        self._mark_paragraph(p, "w:ins")
        after_ppr = p.get_or_add_pPr()
        if title:
            title_run = self._insert_run(after_ppr, f"{title}. ", bold=True)
            after_ppr = title_run._r.getparent()
        self._insert_run(after_ppr, text)
        return Paragraph(p, after._parent)

    def comment(self, runs: list[Run], finding: Finding) -> None:
        if not runs or not self.comments:
            return
        head = f"{TIP_LABEL[finding.tip]} · risk: {finding.risk} — {finding.basliq}"
        note = self.doc.add_comment(runs, text=head, author=AUTHOR, initials=INITIALS)
        note.add_paragraph(finding.izah)
        if finding.madde_basliq:
            ref = f" (bənd {finding.madde_no})" if "." in (finding.madde_no or "") else ""
            note.add_paragraph(f"Mülki Məcəllə, {finding.madde_basliq}{ref}")
        if finding.qeyd:
            note.add_paragraph(f"Verifier: {finding.qeyd}")


def clause_bodies(lines: list[str]) -> dict[str, list[int]]:
    """Parser-in bölgüsü, amma silinməsi təhlükəli abzaslar çıxarılmaqla.

    Nömrəsiz abzas əvvəlki bəndə aid sayılır. Amma böyük hərfli başlıq bəndin davamı deyil,
    son bəndin arxasındakı abzaslar isə çox vaxt imza/rekvizitdir — onlara toxunmuruq.
    """
    spans = parser.clause_spans(lines)
    last = next((k for k in reversed(spans) if k[0].isdigit()), None)
    bodies = {}
    for key, indexes in spans.items():
        body = indexes[:1]
        if key != last:
            for i in indexes[1:]:
                if lines[i].isupper():
                    break
                body.append(i)
        bodies[key] = body
    return bodies


def summary(result: Result, party: str) -> list[str]:
    """Sənədin başlığına qoşulan xülasə şərhinin abzasları."""
    risk = score(result.findings)
    counts = {r: sum(f.risk == r for f in result.findings) for r in ("kritik", "orta", "aşağı")}
    lines = [
        f"Risk balı: {risk.value}/100 — {risk.level} (tərəf: {party})",
        (
            f"Əmlak növü: {result.emlak_novu}. Tapıntılar: {counts['kritik']} kritik, "
            f"{counts['orta']} orta, {counts['aşağı']} aşağı."
        ),
    ]
    missing = [item.movzu for item in result.checklist if not item.var]
    if missing:
        lines.append("Çatışmayan mövzular: " + ", ".join(missing) + ".")
    lines.append(
        "Hər düzəliş Review → Track Changes ilə qəbul və ya rədd edilə bilər. "
        "Qanun istinadları Mülki Məcəllənin mətni ilə avtomatik yoxlanılıb."
    )
    return lines


def accept_all(document: Document) -> None:
    """Word-un "Accept All Changes" əməliyyatı: silinənlər gedir, əlavələr adi mətnə çevrilir."""
    body = document.element.body
    mark = f"{qn('w:pPr')}/{qn('w:rPr')}/"
    removed_paragraphs = []
    for p in body.iter(qn("w:p")):
        deleted = p.find(mark + qn("w:del"))
        if deleted is not None:  # abzas işarəsi silinib — abzas özü də gedir
            removed_paragraphs.append(p)
        for marker in (deleted, p.find(mark + qn("w:ins"))):
            if marker is not None:
                marker.getparent().remove(marker)
    for element in list(body.iter(qn("w:del"))):
        element.getparent().remove(element)
    for element in list(body.iter(qn("w:ins"))):
        for child in list(element):
            element.addprevious(child)
        element.getparent().remove(element)
    for p in removed_paragraphs:
        if not "".join(t.text or "" for t in p.iter(qn("w:t"))).strip():
            p.getparent().remove(p)


def redline(
    document: Document, result: Result, party: str = "icarəçi", clean: bool = False
) -> bytes:
    """Nəticələri sənədə track changes + şərh kimi yazır, DOCX bayt-larını qaytarır.

    clean=True: şərhsiz və bütün düzəlişlər qəbul edilmiş təmiz versiya.
    """
    editor = Redliner(document, comments=not clean)
    pairs = paragraph_lines(document)
    paragraphs = [p for p, _ in pairs]
    spans = clause_bodies([line for _, line in pairs])

    first_runs = [Run(r, paragraphs[0]) for r in paragraphs[0]._p.xpath("./w:r")][:1]
    if first_runs and not clean:  # xülasə şərhi — sənədin ən başında
        head, *rest = summary(result, party)
        note = document.add_comment(first_runs, text=head, author=AUTHOR, initials=INITIALS)
        for line in rest:
            note.add_paragraph(line)

    done: set[str] = set()
    for f in result.findings:
        if f.tip == "catismayan" or f.bend_no not in spans:
            continue
        clause = [paragraphs[i] for i in spans[f.bend_no]]
        if f.bend_no in done or f.bend_no == "Başlıq":
            # eyni bəndə ikinci tapıntı və ya giriş hissəsi: mətni dəyişmirik, yalnız şərh
            editor.comment([Run(r, clause[0]) for r in clause[0]._p.xpath("./w:r")][:1], f)
            continue
        editor.comment(editor.replace_clause(clause, f.bend_no, f.teklif), f)
        done.add(f.bend_no)

    # çatışmayan bəndlər — sonuncu nömrəli bəndin arxasına
    numbered = [i for key, idx in spans.items() if key[0].isdigit() for i in idx]
    anchor = paragraphs[max(numbered)] if numbered else paragraphs[-1]
    for f in result.findings:
        if f.tip == "catismayan" and f.teklif:
            title = {"ru": "Дополнительный пункт", "en": "Additional clause"}.get(
                result.dil, f"Əlavə bənd — {f.basliq}"
            )  # başlıq müqavilənin öz dilində
            anchor = editor.add_clause(anchor, title, f.teklif)
            editor.comment([Run(r, anchor) for r in anchor._p.xpath(".//w:r")][:1], f)

    # texniki yoxlamalar (agent.checks) — mətni dəyişmir, yalnız şərh
    for check in result.checks if not clean else []:
        if check.bend_no in spans:
            p = paragraphs[spans[check.bend_no][0]]
            runs = [Run(r, p) for r in p._p.xpath(".//w:r")][:1]
            if runs:
                note = document.add_comment(
                    runs, text=f"Texniki yoxlama — {check.basliq}", author=AUTHOR, initials=INITIALS
                )
                note.add_paragraph(check.izah)

    if clean:
        accept_all(document)
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


def new_document() -> Document:
    """Boş sənəd — python-docx şablonunun sxem xətası düzəldilmiş (w:zoom-da w:percent yoxdur)."""
    document = docx.Document()
    zoom = document.settings.element.find(qn("w:zoom"))
    if zoom is not None and zoom.get(qn("w:percent")) is None:
        zoom.set(qn("w:percent"), "100")
    return document


def load(data: bytes | None, filename: str, lines: list[str]) -> Document:
    """Orijinal DOCX-i açır; PDF və ya yapışdırılmış mətn üçün sətirlərdən yeni sənəd qurur."""
    if data is not None and filename.lower().endswith(".docx"):
        return docx.Document(io.BytesIO(data))
    document = new_document()
    for line in lines:
        document.add_paragraph(line)
    return document
