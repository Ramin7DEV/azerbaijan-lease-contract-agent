"""Gemma-ya bir sorğuda bütün qanunu və bütün müqaviləni verir, xam JSON tapıntıları qaytarır."""

import hashlib
import json
import re
from pathlib import Path

from agent import law, llm, parser

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
CACHE = ROOT / ".cache/analysis"  # model cavabları: eyni müqavilə + prompt + model → eyni fayl

PARTIES = {
    "icarəçi": "Sən icarəçinin (kirayəçinin) vəkilisən. Riskləri onun maraqlarına görə qiymətləndir.",
    "icarəyə verən": "Sən icarəyə verənin (kirayəyə verənin) vəkilisən. Riskləri onun maraqlarına görə qiymətləndir.",
    "neytral": "Sən neytral ekspertsən. Hər iki tərəf üçün riskləri göstər.",
}


def system_prompt() -> str:
    """Sabit hissə: hər sorğuda eynidir, provayder onu keşləyə bilər."""
    return "\n\n".join(
        [
            (PROMPTS / "system.md").read_text(encoding="utf-8"),
            "# Yoxlama siyahısı\n\n" + (PROMPTS / "checklist.md").read_text(encoding="utf-8"),
            "# Mülki Məcəllə: 33-cü və 34-cü fəsillər\n\n" + law.full_text(),
        ]
    )


def parse_json(text: str) -> dict:
    """Model JSON-u ```json ... ``` içində və ya əlavə mətnlə qaytara bilər."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


LANGUAGE_NOTE = (
    "Müqavilənin dili: {dil}. `teklif`, `guzest` və `xulase` dəyərlərini müqavilənin öz dilində "
    "({dil}) yaz — onlar birbaşa müqaviləyə düşür. `basliq`, `izah`, `arqument` Azərbaycan dilində "
    "qalır (vəkil üçün). Tərəflərin adları: {rollar}. Müqavilə Azərbaycan Respublikasının "
    "qanunvericiliyi ilə tənzimlənir, ona görə Mülki Məcəllənin maddələri tətbiq edilir."
)
ROLES = {
    "ru": "Арендодатель / Наймодатель = icarəyə verən, Арендатор / Наниматель = icarəçi",
    "en": "Landlord / Lessor = icarəyə verən, Tenant / Lessee = icarəçi",
}


def user_prompt(clauses: dict[str, str], party: str) -> str:
    lang = parser.detect_language(clauses)
    note = ""
    if lang != "az":  # Azərbaycan dilli müqavilələrin prompt-u (və keşi) dəyişmir
        note = LANGUAGE_NOTE.format(dil=parser.LANGUAGES[lang], rollar=ROLES[lang]) + "\n\n"
    return f"{PARTIES[party]}\n\n{note}# Müqavilə\n\n{parser.as_prompt(clauses)}"


def _cache_file(system: str, user: str) -> Path:
    text = f"{llm.MODEL}\n{system}\n{user}"
    return CACHE / f"{hashlib.sha256(text.encode()).hexdigest()[:24]}.json"


def cache_path(clauses: dict[str, str], party: str) -> Path:
    return _cache_file(system_prompt(), user_prompt(clauses, party))


def ask_json(system: str, user: str, refresh: bool = False) -> dict:
    """Modelin JSON cavabı. Keşdə varsa, dərhal oradan (refresh=True keşi keçir).

    Keş açarına prompt, qanun, müqavilə və model daxildir — biri dəyişsə, təzədən soruşulur.
    Model səhv JSON qaytararsa, bir dəfə təkrar soruşulur.
    """
    cached = _cache_file(system, user)
    if cached.exists() and not refresh:
        return json.loads(cached.read_text(encoding="utf-8"))

    for attempt in range(2):
        try:
            raw = parse_json(llm.ask(system, user, json_mode=True))
            break
        except (ValueError, json.JSONDecodeError):  # json.loads və ya index("{") uğursuz oldu
            if attempt:
                raise
            user += "\n\nVACİB: cavab yalnız etibarlı JSON olmalıdır, başqa mətn yazma."

    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    return raw


FOCUS_NOTE = (
    "\n\n# Diqqət: bu, müqavilənin qarşı tərəfdən gələn yeni versiyasıdır\n\n"
    "Bu bəndlər əvvəlki versiyaya nisbətən əlavə edilib və ya dəyişdirilib: {keys}. "
    "Onların hər birini xüsusi diqqətlə yoxla — qarşı tərəf yeni birtərəfli şərt, cərimə və ya "
    "öhdəlik əlavə edə bilər. Normaldırsa, tapıntı yaratma."
)


def analyze(
    clauses: dict[str, str], party: str, refresh: bool = False, focus: list[str] | None = None
) -> dict:
    """Müqavilənin tam təhlili: bir sorğu, bütöv qanun + bütöv müqavilə.

    focus — versiya müqayisəsində dəyişən / əlavə olunan bəndlər (model onlara xüsusi baxır).
    """
    user = user_prompt(clauses, party)
    if focus:
        user += FOCUS_NOTE.format(keys=", ".join(focus))
    return ask_json(system_prompt(), user, refresh)


if __name__ == "__main__":
    import sys
    import time

    path = Path(sys.argv[1])
    clauses = parser.parse(path.read_bytes(), path.name)
    print(f"{len(clauses)} bənd, model işləyir...")
    t = time.time()
    print(json.dumps(analyze(clauses, "icarəçi"), ensure_ascii=False, indent=2))
    print(f"{time.time() - t:.0f} san")
