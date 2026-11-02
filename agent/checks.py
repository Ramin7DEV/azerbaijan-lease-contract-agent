"""Texniki yoxlamalar — modelsiz, yalnız kodla. Uydurma riski sıfırdır.

Vəkillərin tez-tez qaçırdığı mexaniki səhvləri tapır:
1. rəqəm-söz uyğunsuzluğu: "800 (yeddi yüz) manat";
2. müqavilədə olmayan bəndə istinad: "7.2-ci bəndə uyğun olaraq";
3. tərəfin fərqli adlandırılması: "İcarəçi" müəyyən edilib, amma "Kirayəçi" də işlənir;
4. tarixlər: mövcud olmayan gün ("31 iyun"), bitmə tarixi başlanğıcdan əvvəl.

Bu yoxlamalar mətni dəyişmir — Word faylında yalnız şərh kimi göstərilir.
"""

import re
from dataclasses import dataclass
from datetime import date

UNITS = {"bir": 1, "iki": 2, "üç": 3, "dörd": 4, "beş": 5, "altı": 6, "yeddi": 7, "səkkiz": 8,
         "doqquz": 9, "on": 10, "iyirmi": 20, "otuz": 30, "qırx": 40, "əlli": 50, "altmış": 60,
         "yetmiş": 70, "səksən": 80, "doxsan": 90}  # fmt: skip
SCALES = {"min": 1_000, "milyon": 1_000_000}
FILLER = {"manat", "qəpik", "faiz", "gün", "ay", "il", "aylıq", "illik", "günlük", "azn"}

MONTHS = {"yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6, "iyul": 7,
          "avqust": 8, "sentyabr": 9, "oktyabr": 10, "noyabr": 11, "dekabr": 12}  # fmt: skip

TENANT = ["İcarəçi", "Kirayəçi", "İcarəyə götürən", "Kirayəyə götürən"]
LANDLORD = ["İcarəyə verən", "Kirayəyə verən", "Mülkiyyətçi", "Ev sahibi", "İcarədar"]

NUMBER_WITH_WORDS = re.compile(r"(\d[\d\s.,]*\d|\d)\s*\(([^()\d]{2,60})\)")
CLAUSE_REF = re.compile(r"(\d{1,2}(?:\.\d{1,2}){1,3})[-‑]?(?:ci|cı|cu|cü)?\s+bənd", re.IGNORECASE)
DATE = re.compile(r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(\d{4})", re.IGNORECASE)
PERIOD = re.compile(
    rf"{DATE.pattern}[^.]*?tarixdən[^.]*?{DATE.pattern}[^.]*?tarixədək", re.IGNORECASE
)


@dataclass
class Check:
    bend_no: str
    basliq: str
    izah: str


def words_to_number(text: str) -> int | None:
    """ "səkkiz yüz" → 800, "iki min dörd yüz" → 2400. Tanınmayan söz varsa None."""
    total = current = 0
    seen = False
    for word in re.findall(r"[^\W\d_]+", text.lower()):
        if word in UNITS:
            current += UNITS[word]
        elif word == "yüz":
            current = (current or 1) * 100
        elif word in SCALES:
            total += (current or 1) * SCALES[word]
            current = 0
        elif word in FILLER:
            continue
        else:
            return None
        seen = True
    return total + current if seen else None


def number_mismatches(clauses: dict[str, str]) -> list[Check]:
    out = []
    for key, text in clauses.items():
        for digits, words in NUMBER_WITH_WORDS.findall(text):
            value = words_to_number(words)
            number = re.sub(r"[\s.,]", "", digits)
            if value is not None and number.isdigit() and int(number) != value:
                out.append(Check(
                    key, "Rəqəm sözlə uyğun gəlmir",
                    f"\"{digits.strip()} ({words.strip()})\": rəqəmlə {int(number)}, sözlə {value} yazılıb. "
                    "Mübahisədə hansının keçərli olduğu şübhə yaradır — hər ikisini eyniləşdirin.",
                ))  # fmt: skip
    return out


def broken_references(clauses: dict[str, str]) -> list[Check]:
    out = []
    for key, text in clauses.items():
        for ref in CLAUSE_REF.findall(text):
            if ref not in clauses and ref != key:
                out.append(Check(
                    key, "Mövcud olmayan bəndə istinad",
                    f"Mətndə {ref}-ci bəndə istinad var, amma müqavilədə belə bənd yoxdur. "
                    "Nömrələmə dəyişib və ya istinad səhvdir.",
                ))  # fmt: skip
    return out


def inconsistent_parties(clauses: dict[str, str]) -> list[Check]:
    """Müqavilə bir adı müəyyən edib ("bundan sonra "İcarəçi""), amma eyni tərəfə başqa ad da işlədir."""
    text = "\n".join(clauses.values())
    defined = set(re.findall(r"bundan sonra\s+[\"“«„']([^\"”»“']+)[\"”»“']", text))
    out = []
    for group in (TENANT, LANDLORD):
        chosen = [name for name in group if name in defined]
        if not chosen:
            continue
        for other in group:
            if other in defined:
                continue
            for key, clause in clauses.items():
                if re.search(rf"(?<!\w){re.escape(other)}(?!\w)", clause):
                    out.append(Check(
                        key, "Tərəf fərqli adlandırılıb",
                        f"Müqavilə tərəfi \"{chosen[0]}\" kimi müəyyən edib, bu bənddə isə "
                        f"\"{other}\" yazılıb. Termini vahid saxlayın.",
                    ))  # fmt: skip
                    break
    return out


def parse_date(day: str, month: str, year: str) -> date | None:
    try:
        return date(int(year), MONTHS[month.lower()], int(day))
    except ValueError:
        return None


def bad_dates(clauses: dict[str, str]) -> list[Check]:
    out = []
    for key, text in clauses.items():
        for day, month, year in DATE.findall(text):
            if parse_date(day, month, year) is None:
                out.append(Check(key, "Mövcud olmayan tarix",
                                 f"\"{day} {month} {year}\" təqvimdə yoxdur."))  # fmt: skip
        for m in PERIOD.finditer(text):
            start, end = parse_date(*m.groups()[:3]), parse_date(*m.groups()[3:])
            if start and end and end <= start:
                out.append(Check(key, "Bitmə tarixi başlanğıcdan əvvəldir",
                                 f"Müddət {start:%d.%m.%Y}-dən {end:%d.%m.%Y}-dək göstərilib."))  # fmt: skip
    return out


def run(clauses: dict[str, str]) -> list[Check]:
    from agent.parser import detect_language

    if (
        detect_language(clauses) != "az"
    ):  # rəqəm sözləri, ay adları, "bundan sonra" — Azərbaycan dili
        return []
    return (
        number_mismatches(clauses)
        + broken_references(clauses)
        + inconsistent_parties(clauses)
        + bad_dates(clauses)
    )
