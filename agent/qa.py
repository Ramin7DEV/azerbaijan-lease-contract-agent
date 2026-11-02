"""Müqavilə ilə sual-cavab: cavab bənd və qanun maddəsi ilə, istinadlar Verifier-dən keçir.

Qanun + müqavilə system mesajındadır (hər sual üçün eyni — provayder keşləyə bilər),
sual isə user mesajında. Cavablar da diskdə keşlənir.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from agent import analyzer, law, parser

PROMPT = Path(__file__).resolve().parent.parent / "prompts/qa.md"
# cavab mətnində qanun istinadı: "Maddə 687", "691.3-cü maddə"
LAW_REF = re.compile(r"[Mm]addə\s+(\d{3}(?:\.\d+)*)|(\d{3}(?:\.\d+)+)[-‑]?(?:ci|cı|cu|cü)\s+maddə")

EXAMPLES = [
    "Müştərim müqavilədən vaxtından əvvəl necə çıxa bilər?",
    "Təminat pulu nə vaxt və necə qaytarılmalıdır?",
    "İcarə haqqı gecikərsə nə baş verir?",
    "Əmlak satılsa, müqavilə davam edirmi?",
]


@dataclass
class Answer:
    sual: str
    cavab: str
    bendler: list[tuple[str, str]] = field(default_factory=list)  # (nömrə, mətn — müqavilədən)
    maddeler: list[tuple[str, str, str]] = field(default_factory=list)  # (nömrə, başlıq, mətn)
    atildi: list[str] = field(default_factory=list)  # Verifier-in təsdiqləmədiyi istinadlar


def system_prompt(clauses: dict[str, str]) -> str:
    return "\n\n".join([
        PROMPT.read_text(encoding="utf-8"),
        "# Yoxlama siyahısı\n\n" + (analyzer.PROMPTS / "checklist.md").read_text(encoding="utf-8"),
        "# Mülki Məcəllə: 33-cü və 34-cü fəsillər\n\n" + law.full_text(),
        "# Müqavilə\n\n" + parser.as_prompt(clauses),
    ])  # fmt: skip


def ask(question: str, clauses: dict[str, str], party: str, refresh: bool = False) -> Answer:
    user = f"{analyzer.PARTIES[party]}\n\n# Sual\n\n{question.strip()}"
    raw = analyzer.ask_json(system_prompt(clauses), user, refresh)

    answer = Answer(sual=question.strip(), cavab=str(raw.get("cavab") or "").strip())
    for ref in raw.get("bendler") or []:
        key = str(ref).strip("[] ")
        if key in clauses:
            answer.bendler.append((key, clauses[key]))
        else:
            answer.atildi.append(f"bənd {key} (müqavilədə yoxdur)")

    refs = [str(r) for r in raw.get("maddeler") or []]
    refs += [a or b for a, b in LAW_REF.findall(answer.cavab)]  # mətndə adı çəkilən maddələr də
    for ref in dict.fromkeys(r.removeprefix("Maddə").strip() for r in refs):
        hit = law.lookup(ref)
        if hit:
            article, text = hit
            answer.maddeler.append((ref, f"Maddə {article.number}. {article.title}", text))
        else:
            answer.atildi.append(f"Maddə {ref} (bazada yoxdur)")
    return answer
