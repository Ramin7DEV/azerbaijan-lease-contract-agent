"""Keyfiyyət ölçümü: test müqavilələrini real modellə yoxlayır və düzgün cavablarla müqayisə edir.

Metodologiya (Screens / contract-review-pipeline kimi):
- Recall — tapılmalı problemlərin neçəsi tapıldı
- Precision — agentin göstərdiyi problemlərin neçəsi həqiqətən problemdir
- Tip dəqiqliyi — "qanuna zidd" / "birtərəfli" təsnifatı düzgündürmü
- Çatışmayan mövzular — yoxlama siyahısında "yoxdur" düzgün deyilibmi
- Uydurma — model bazada olmayan maddəyə / müqavilədə olmayan bəndə istinad edibmi (Verifier atıb)

Düzgün cavablar: data/contracts/gozlenilen.json. Nəticə terminalda və output/eval.md-də.
Model cavabları keşlənir; təzədən soruşmaq üçün --refresh.

İstifadə: uv run python scripts/evaluate.py [--refresh]
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent import analyzer, llm, parser, score, verifier

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "data/contracts"
PARTY = "icarəçi"


def clauses_of(name: str) -> dict[str, str]:
    path = CONTRACTS / name
    if path.suffix == ".txt":
        return parser.parse_text(path.read_text(encoding="utf-8"))
    return parser.parse(path.read_bytes(), name)


def evaluate(name: str, truth: dict, refresh: bool) -> dict:
    clauses = clauses_of(name)
    started = time.time()
    raw = analyzer.analyze(clauses, PARTY, refresh=refresh)
    result = verifier.verify(raw, clauses)

    found: dict[str, set[str]] = {}
    for f in result.findings:
        if f.bend_no:
            found.setdefault(f.bend_no, set()).add(f.tip)
    expected, acceptable, traps = truth["expected"], set(truth["acceptable"]), set(truth["traps"])

    hits = [b for b in expected if b in found]
    typed = [b for b in hits if expected[b]]
    correct_type = [b for b in typed if expected[b] in found[b]]
    wrong = [b for b in found if b not in expected and b not in acceptable]
    missing_said = {i.movzu for i in result.checklist if not i.var}
    fabricated = [r for _, r in result.rejected if "yoxdur" in r]
    language = truth.get("dil", "az")
    texts = [t for f in result.findings for t in (f.teklif, f.guzest) if t]
    in_language = [t for t in texts if parser.detect_language({"t": t}) == language]

    return {
        "name": name,
        "seconds": round(time.time() - started),
        "emlak_ok": result.emlak_novu == truth["emlak_novu"],
        "recall": (len(hits), len(expected)),
        "precision": (len(found) - len(wrong), len(found)),
        "type": (len(correct_type), len(typed)),
        "missing": (len(set(truth["missing"]) & missing_said), len(truth["missing"])),
        "false_missing": sorted(missing_said - set(truth["missing"])),
        "missed": [b for b in expected if b not in found],
        "wrong": wrong,
        "traps_hit": [b for b in wrong if b in traps],
        "wrong_type": [
            f"{b} ({expected[b]} → {'/'.join(sorted(found[b]))})"
            for b in typed
            if b not in correct_type
        ],
        "fabricated": len(fabricated),
        "language": (len(in_language), len(texts)),
        "raw_total": len(raw.get("tapintilar", [])),
        "downgraded": sum(bool(f.qeyd) for f in result.findings),
        "score": score.score(result.findings).value,
    }


def pct(pair: tuple[int, int]) -> str:
    done, total = pair
    return f"{done}/{total} ({100 * done / total:.0f}%)" if total else "—"


def main() -> None:
    refresh = "--refresh" in sys.argv
    truth = json.loads((CONTRACTS / "gozlenilen.json").read_text(encoding="utf-8"))
    names = [n for n in truth if not n.startswith("_")]
    with ThreadPoolExecutor(
        max_workers=3
    ) as pool:  # provayder limiti — çox paralel sorğu xəta verir
        rows = list(pool.map(lambda n: evaluate(n, truth[n], refresh), names))

    def total(key: str) -> tuple[int, int]:
        return sum(r[key][0] for r in rows), sum(r[key][1] for r in rows)

    lines = [
        f"# Keyfiyyət ölçümü — {time.strftime('%d.%m.%Y %H:%M')}",
        "",
        f"Model: `{llm.MODEL}` · tərəf: {PARTY} · {len(rows)} müqavilə",
        "",
        "| Müqavilə | Növ | Recall | Precision | Tip | Çatışmayan | Dil | Uydurma | Bal | Vaxt |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['name']} | {'✅' if r['emlak_ok'] else '❌'} | {pct(r['recall'])} | "
            f"{pct(r['precision'])} | {pct(r['type'])} | {pct(r['missing'])} | "
            f"{pct(r['language'])} | {r['fabricated']}/{r['raw_total']} | {r['score']} | "
            f"{r['seconds']} san |"
        )
    fabricated = sum(r["fabricated"] for r in rows)
    raw_total = sum(r["raw_total"] for r in rows)
    lines += [
        (
            f"| **Cəmi** | {sum(r['emlak_ok'] for r in rows)}/{len(rows)} | "
            f"**{pct(total('recall'))}** | **{pct(total('precision'))}** | "
            f"**{pct(total('type'))}** | {pct(total('missing'))} | {pct(total('language'))} | "
            f"{fabricated}/{raw_total} | | |"
        ),
        "",
        "- **Recall** — tapılmalı problemlərdən neçəsi tapıldı.",
        (
            "- **Precision** — agentin göstərdiyi bəndlərdən neçəsi həqiqətən problemdir "
            "(normal bəndi problem saymaq səhvdir)."
        ),
        '- **Tip** — "qanuna zidd" / "birtərəfli" təsnifatı düzgündürmü (imperativ norma yoxlaması).',
        "- **Çatışmayan** — yoxlama siyahısında olmayan mövzular düzgün tapıldımı.",
        "- **Dil** — düzəliş və güzəşt mətnləri müqavilənin öz dilindədirmi (rus / ingilis müqavilələr).",
        (
            "- **Uydurma** — model bazada olmayan maddəyə / müqavilədə olmayan bəndə istinad edib, "
            "Verifier atıb. İstifadəçiyə heç biri göstərilmir."
        ),
        "",
        "## Detallar",
        "",
    ]
    for r in rows:
        notes = []
        if r["missed"]:
            notes.append(f"qaçırılıb: {', '.join(r['missed'])}")
        if r["wrong"]:
            notes.append(f"artıq tapıntı: {', '.join(r['wrong'])}")
        if r["traps_hit"]:
            notes.append(f"**tələyə düşüb**: {', '.join(r['traps_hit'])}")
        if r["wrong_type"]:
            notes.append(f"tip səhvi: {', '.join(r['wrong_type'])}")
        if r["false_missing"]:
            notes.append(f"səhvən 'yoxdur' deyilib: {', '.join(r['false_missing'])}")
        if r["downgraded"]:
            notes.append(f"Verifier {r['downgraded']} tapıntının tipini düzəldib")
        lines.append(f"- **{r['name']}**: {'; '.join(notes) or 'səhv yoxdur ✅'}")

    report = "\n".join(lines) + "\n"
    out = ROOT / "output/eval.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"📄 {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
