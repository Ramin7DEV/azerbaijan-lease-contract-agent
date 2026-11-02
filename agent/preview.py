"""Sənəd görünüşü: müqavilənin bəndləri sənəd sırası ilə + hər bəndə aid tapıntı.

Vəkil ekranda bütöv müqaviləni görür, düzəlişləri elə orada qəbul edir, ləğv edir və ya
redaktə edir. Bu modul o görünüşün sətirlərini qurur — Streamlit-dən asılı deyil, saf məntiqdir.
"""

from dataclasses import dataclass

from agent.verifier import Finding


@dataclass(frozen=True)
class Row:
    kind: str  # "metn" | "basliq" | "bend" | "elave"
    key: str | None  # bəndin açarı; "elave" üçün None
    text: str  # bəndin ORİJİNAL mətni; "elave" üçün ""
    finding: int | None = None  # bu bəndin mətnini dəyişən tapıntının indeksi (result.findings-də)
    notes: tuple[int, ...] = ()  # həmin bəndə aid DİGƏR tapıntıların indeksləri


def rows(clauses: dict[str, str], findings: list[Finding]) -> list[Row]:
    """Müqavilənin sətirləri sənəd sırası ilə, sonda əlavə ediləcək bəndlər."""
    if not clauses:
        return []

    # 1. Tapıntıları bəndlərə payla (ən yüksək riskli tapıntı mətni dəyişir, qalanları qeyd)
    assigned_finding: dict[str, int] = {}
    assigned_notes: dict[str, list[int]] = {}

    for i, f in enumerate(findings):
        if f.bend_no is None or f.bend_no not in clauses:
            continue
        if f.bend_no == "Başlıq":
            assigned_notes.setdefault(f.bend_no, []).append(i)
        elif f.bend_no not in assigned_finding:
            assigned_finding[f.bend_no] = i
        else:
            assigned_notes.setdefault(f.bend_no, []).append(i)

    # 2. Müqavilənin sətirlərini sənəd sırası ilə qur
    result: list[Row] = []
    for key, text in clauses.items():
        if key == "Başlıq":
            kind = "metn"
        elif text.isupper():
            kind = "basliq"
        else:
            kind = "bend"

        if kind in ("metn", "basliq"):
            # Başlıq və bölmə adlarında mətn dəyişdirilmir, tapıntılar yalnız qeyd kimi qalır
            clause_notes: list[int] = []
            if key in assigned_finding:
                clause_notes.append(assigned_finding[key])
            clause_notes.extend(assigned_notes.get(key, []))
            result.append(
                Row(kind=kind, key=key, text=text, finding=None, notes=tuple(clause_notes))
            )
        else:
            result.append(
                Row(
                    kind=kind,
                    key=key,
                    text=text,
                    finding=assigned_finding.get(key),
                    notes=tuple(assigned_notes.get(key, [])),
                )
            )

    # 3. Çatışmayan bəndlər (sonda əlavə ediləcək yeni bəndlər)
    for i, f in enumerate(findings):
        if f.tip == "catismayan" and f.teklif:
            result.append(Row(kind="elave", key=None, text="", finding=i, notes=()))

    return result
