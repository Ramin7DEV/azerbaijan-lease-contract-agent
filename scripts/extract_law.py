"""Mülki Məcəllənin DOCX-indən (e-qanun.az) 33-cü (Əmlak kirayəsi) və 34-cü (İcarə)
fəsilləri çıxarıb data/law/icare.txt-ə yazır.

İstifadə: uv run python scripts/extract_law.py
"""

import re
from pathlib import Path

import docx

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data/law/mulki_mecelle.docx"
TARGET = ROOT / "data/law/icare.txt"

if not SOURCE.exists():
    raise SystemExit(f"{SOURCE} tapılmadı. Mülki Məcəllənin DOCX-ini e-qanun.az-dan endirib bu yola qoyun.")

# Maddə 700.3: icarəyə kirayə haqqındakı müddəalar da tətbiq edilir, ona görə hər iki fəsil lazımdır.
START, END = "33-cü fəsil.", "35-ci fəsil."

paragraphs = [p.text.strip() for p in docx.Document(SOURCE).paragraphs]
start = paragraphs.index(START)
end = paragraphs.index(END, start)

# [123] — izah qeydlərinin nömrələri
lines = [re.sub(r"\[\d+\]", "", p).strip() for p in paragraphs[start:end]]
lines = [line for line in lines if line]
TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8")

articles = sum(1 for line in lines if re.match(r"Maddə \d+\.", line))
print(f"{TARGET.relative_to(ROOT)}: {articles} maddə, {sum(map(len, lines))} simvol")
