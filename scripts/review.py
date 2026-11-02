"""Müqaviləni terminalda yoxlayır — UI olmadan test üçün. Düzəldilmiş DOCX output/ qovluğuna yazılır.

İstifadə: uv run python scripts/review.py data/contracts/xarab_01.docx [icarəçi|icarəyə verən|neytral]
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent import analyzer, checks, memo, parser, redliner, score, verifier

path = Path(sys.argv[1])
party = sys.argv[2] if len(sys.argv) > 2 else "icarəçi"
if path.suffix == ".txt":
    data, lines = (
        None,
        [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()],
    )
else:
    data, lines = path.read_bytes(), parser.read_lines(path.read_bytes(), path.name)
clauses = parser.split_clauses(lines)

started = time.time()
result = verifier.verify(analyzer.analyze(clauses, party), clauses)
print(f"{path.name} · {party} · {result.emlak_novu} · {time.time() - started:.0f} san\n")
risk = score.score(result.findings)
print(f"Risk balı: {risk.value}/100 — {risk.level}")

missing = [item.movzu for item in result.checklist if not item.var]
print(
    f"Siyahı: {len(result.checklist) - len(missing)}/{len(result.checklist)} var, yoxdur: {missing}"
)
for f in result.findings:
    print(f"\n[{f.risk}] {f.tip} · bənd {f.bend_no} · maddə {f.madde_no} · {f.basliq}")
    print(f"  izah:   {f.izah}")
    print(f"  təklif: {f.teklif}")
    if f.qeyd:
        print(f"  🛡️ {f.qeyd}")
for item, reason in result.rejected:
    print(f"\n✘ ATILDI: {reason} · {item.get('basliq') if isinstance(item, dict) else item}")

result.checks = checks.run(clauses)
out = Path("output") / f"{path.stem}_düzəliş.docx"
out.parent.mkdir(exist_ok=True)
out.write_bytes(redliner.redline(redliner.load(data, path.name, lines), result, party))
print(f"\n📥 {out}")
memo_path = out.with_name(f"{path.stem}_hüquqi_rəy.docx")
memo_path.write_bytes(memo.build(result, party, path.name))
print(f"📝 {memo_path}")
