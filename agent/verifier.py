"""Modelin cavabını yoxlayır: istinad edilən maddə və bənd həqiqətən varmı?

Maddənin və bəndin mətni modeldən yox, bazadan / müqavilədən götürülür.
Uydurma istinadlı tapıntılar atılır və səbəbi ilə birlikdə ayrıca qaytarılır.
"Qanuna zidd" iddiası yalnız imperativ normaya istinad edirsə qəbul olunur, əks halda
tapıntı "birtərəfli" kimi düzəldilir.
"""

import re
from dataclasses import dataclass, field
from datetime import date

from agent import law, parser

TYPES = {"qanuna_zidd", "birterefli", "catismayan"}
RISKS = ["kritik", "orta", "aşağı"]


@dataclass
class Finding:
    tip: str
    risk: str
    basliq: str
    izah: str
    teklif: str
    bend_no: str | None = None
    bend_metni: str | None = None  # müqavilədən
    madde_no: str | None = None
    madde_basliq: str | None = None  # bazadan
    madde_metni: str | None = None  # bazadan
    qeyd: str | None = None  # Verifier-in düzəlişi
    guzest: str = ""  # danışıq: kompromis variant
    arqument: str = ""  # danışıq: qarşı tərəfə deyiləcək


@dataclass
class ChecklistItem:
    movzu: str
    var: bool
    bend_no: str | None = None


# Müqavilə kartının sahələri — ekranda bu sıra ilə göstərilir
SUMMARY_LABELS = {
    "icareye_veren": "İcarəyə verən",
    "icareci": "İcarəçi",
    "emlak": "Əmlak",
    "icare_haqqi": "İcarə haqqı",
    "teminat": "Təminat",
    "muddet": "Müddət",
    "legvetme": "Ləğvetmə",
}


@dataclass
class SummaryField:
    label: str
    deyer: str
    bend_no: str | None
    yoxlanildi: bool  # dəyərdəki bütün rəqəmlər müqavilənin mətnində varmı


@dataclass
class Summary:
    fields: list[SummaryField] = field(default_factory=list)
    baslangic: date | None = None
    bitme: date | None = None
    odenis_gunu: int | None = None


@dataclass
class Result:
    emlak_novu: str
    findings: list[Finding] = field(default_factory=list)
    checklist: list[ChecklistItem] = field(default_factory=list)
    # (xam tapıntı, atılma səbəbi)
    rejected: list[tuple[dict, str]] = field(default_factory=list)
    summary: Summary = field(default_factory=Summary)
    dil: str = "az"  # müqavilənin dili: az / ru / en
    checks: list = field(default_factory=list)  # agent.checks.Check — kodla tapılan texniki səhvlər


def clean_bend(value) -> str | None:
    return str(value).strip("[] ") if value else None


def check(raw: dict, clauses: dict[str, str], emlak_novu: str) -> Finding | str:
    """Tapıntı keçərlidirsə Finding, yoxsa atılma səbəbi (str)."""
    tip = raw.get("tip")
    if tip not in TYPES:
        return f"naməlum tip: {tip!r}"

    bend_no = clean_bend(raw.get("bend_no")) if tip != "catismayan" else None
    if tip != "catismayan":
        if not bend_no:
            return "bənd nömrəsi göstərilməyib"
        if bend_no not in clauses:
            return f"müqavilədə [{bend_no}] bəndi yoxdur"

    finding = Finding(
        tip=tip,
        risk=raw.get("risk") if raw.get("risk") in RISKS else "orta",
        basliq=raw.get("basliq") or "",
        izah=raw.get("izah") or "",
        teklif=raw.get("teklif") or "",
        bend_no=bend_no,
        bend_metni=clauses.get(bend_no) if bend_no else None,
        guzest=raw.get("guzest") or "",
        arqument=raw.get("arqument") or "",
    )

    madde_no = str(raw.get("madde_no") or "").removeprefix("Maddə").strip()
    if madde_no:
        hit = law.lookup(madde_no)
        if not hit:
            return f"Maddə {madde_no} bazada yoxdur (uydurma istinad)"
        article, text = hit
        finding.madde_no = madde_no
        finding.madde_basliq = f"Maddə {article.number}. {article.title}"
        finding.madde_metni = text
    elif tip == "qanuna_zidd":
        return "qanuna ziddir deyilib, amma maddə göstərilməyib"

    if tip == "qanuna_zidd" and not law.is_imperative(madde_no, emlak_novu):
        finding.tip = "birterefli"
        finding.qeyd = (
            f"Maddə {madde_no} {emlak_novu} əmlak üçün məcburi norma deyil: tərəflər ondan "
            "kənara çıxa bilər. Bənd qüvvədədir, amma qanundakı standart qaydadan pisdir."
        )
    return finding


def _digits(text: str) -> list[str]:
    return re.findall(r"\d+", re.sub(r"(?<=\d)[\s.,](?=\d{3}\b)", "", text))


def verify_summary(raw: dict | None, clauses: dict[str, str]) -> Summary:
    """Müqavilə kartı: dəyərlər modeldən gəlir, amma rəqəmləri müqavilənin mətnində yoxlanılır.

    Tarix yalnız ili müqavilədə yazılıbsa qəbul edilir (model müddətdən tarix hesablamasın).
    """
    raw = raw if isinstance(raw, dict) else {}
    summary = Summary()
    text = "\n".join(clauses.values())
    contract_digits = set(_digits(text))
    for key, label in SUMMARY_LABELS.items():
        item = raw.get(key)
        if not isinstance(item, dict) or not item.get("deyer"):
            continue
        refs = [
            r.strip("[] ") for r in re.split(r"[,;]\s*|\s+və\s+", str(item.get("bend_no") or ""))
        ]
        bend_no = ", ".join(r for r in refs if r in clauses) or None  # "3.1, 3.2" də ola bilər
        ok = all(d in contract_digits for d in _digits(str(item["deyer"])))
        summary.fields.append(SummaryField(label, str(item["deyer"]), bend_no, ok))
    for key in ("baslangic_tarixi", "bitme_tarixi"):
        try:
            value = date.fromisoformat(str(raw.get(key)))
        except ValueError:
            continue
        if str(value.year) in text:
            setattr(summary, "baslangic" if key.startswith("bas") else "bitme", value)
    day = raw.get("odenis_gunu")
    if isinstance(day, int) and 1 <= day <= 31:
        summary.odenis_gunu = day
    return summary


def verify(raw: dict, clauses: dict[str, str]) -> Result:
    result = Result(emlak_novu=raw.get("emlak_novu") or "müəyyən deyil")
    result.dil = parser.detect_language(clauses)
    for item in raw.get("tapintilar", []):
        outcome = check(item, clauses, result.emlak_novu) if isinstance(item, dict) else "format"
        if isinstance(outcome, Finding):
            result.findings.append(outcome)
        else:
            result.rejected.append((item, outcome))
    result.findings.sort(key=lambda f: RISKS.index(f.risk))
    result.summary = verify_summary(raw.get("xulase"), clauses)

    for item in raw.get("siyahi", []):
        if isinstance(item, dict) and item.get("movzu"):
            bend_no = clean_bend(item.get("bend_no"))
            result.checklist.append(
                ChecklistItem(
                    movzu=item["movzu"],
                    var=bool(item.get("var")),
                    bend_no=bend_no if bend_no in clauses else None,
                )
            )
    return result
