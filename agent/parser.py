"""Müqaviləni (DOCX/PDF) oxuyur və nömrələnmiş bəndlərə bölür: {"4.2": "bəndin mətni"}."""

import io
import re

import docx
from pypdf import PdfReader

from agent.numbering import paragraph_lines

# "4.2. Mətn", "4.2) Mətn", "4 Mətn" — bəndin nömrəsi sətrin əvvəlində
CLAUSE = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){0,3})[.)]?\s+(\S.*)$")


def read_lines(data: bytes, filename: str) -> list[str]:
    if filename.lower().endswith(".txt"):
        return [l.strip() for l in data.decode("utf-8").splitlines() if l.strip()]
    if filename.lower().endswith(".pdf"):
        text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
        return [l.strip() for l in text.splitlines() if l.strip()]
    document = docx.Document(io.BytesIO(data))
    lines = [line for _, line in paragraph_lines(document)]  # Word-un avtomatik nömrələri daxil
    for table in document.tables:  # rekvizitlər çox vaxt cədvəldə olur
        for row in table.rows:
            lines.append(
                " | ".join(dict.fromkeys(c.text.strip() for c in row.cells if c.text.strip()))
            )
    return [l for l in lines if l]


def clause_spans(lines: list[str]) -> dict[str, list[int]]:
    """Bənd nömrəsi → onun sətirlərinin indeksləri. Redliner eyni bölgünü DOCX abzaslarına tətbiq edir.

    Nömrəsiz sətirlər əvvəlki bəndə birləşir. Nömrələnməmiş müqavilədə abzaslar P1, P2... olur.
    """
    if sum(bool(CLAUSE.match(l)) for l in lines) < 3:
        return {f"P{i}": [i - 1] for i in range(1, len(lines) + 1)}

    spans: dict[str, list[int]] = {}
    key = "Başlıq"
    for i, line in enumerate(lines):
        match = CLAUSE.match(line)
        if match:
            key = match[1]
            while key in spans:  # təkrar nömrə — itməsin
                key += "'"
            spans[key] = [i]
        else:
            spans.setdefault(key, []).append(i)
    return spans


def split_clauses(lines: list[str]) -> dict[str, str]:
    clauses = {}
    for key, indexes in clause_spans(lines).items():
        parts = [lines[i] for i in indexes]
        if key[0].isdigit():  # nömrəni mətndən çıxar: "4.2. Mətn" → "Mətn"
            parts[0] = CLAUSE.match(parts[0])[2]
        clauses[key] = "\n".join(parts)
    return clauses


def parse(data: bytes, filename: str) -> dict[str, str]:
    return split_clauses(read_lines(data, filename))


def parse_text(text: str) -> dict[str, str]:
    """Yapışdırılmış mətn üçün: hər sətir bir abzas sayılır."""
    return split_clauses([l.strip() for l in text.splitlines() if l.strip()])


LANGUAGES = {"az": "Azərbaycan dili", "ru": "rus dili", "en": "ingilis dili"}


def detect_language(clauses: dict[str, str]) -> str:
    """Müqavilənin dili: "az", "ru" və ya "en" (hərf statistikası ilə, modelsiz)."""
    text = " ".join(clauses.values())
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "az"
    cyrillic = sum("\u0400" <= c <= "\u04ff" for c in letters) / len(letters)
    if cyrillic > 0.3:
        return "ru"
    azerbaijani = sum(c in "əƏğĞıİöÖüÜşŞçÇ" for c in letters) / len(letters)
    return "az" if azerbaijani > 0.01 else "en"


def as_prompt(clauses: dict[str, str]) -> str:
    return "\n".join(f"[{no}] {text}" for no, text in clauses.items())
