"""Qanun bazası: icare.txt-i maddələrə bölür. Verifier maddə mətnini yalnız buradan götürür."""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

LAW_PATH = Path(__file__).resolve().parent.parent / "data/law/icare.txt"

# İmperativ normalar: qanun "razılaşmanın qüvvəsi yoxdur" deyir, tərəflər dəyişə bilməz.
# Açar — maddə/bənd, dəyər — kimə şamil olunur. prompts/checklist.md-nin B cədvəli ilə eyni olmalıdır.
# Burada olmayan norma dispozitivdir: ondan kənaraçıxma "qanuna zidd" yox, ən çoxu "birtərəfli"dir.
ALL, RESIDENTIAL = "hamı", "yaşayış"
IMPERATIVE = {
    "677.4": ALL,  # qəsdən gizlədilmiş qüsur üçün məsuliyyətdən azadolma
    "686": ALL,  # ağır pozuntuda dərhal ləğv hüququ (otaqlar)
    "691.3": ALL,  # icarəyə verənin xəbərdarlıq müddətini qısaltmaq
    "695": ALL,  # kirayəçinin ölümü
    "677.1.1": RESIDENTIAL,  # qüsur dövründə haqqın azaldılması
    "677.1.4": RESIDENTIAL,  # qüsura görə ləğv hüququ
    "678": RESIDENTIAL,  # əsaslı təmir tədbirləri
    "681": RESIDENTIAL,  # qurğuları götürmək hüququ
    "683.2": RESIDENTIAL,  # otağın bir hissəsini subicarəyə vermək
    "687": RESIDENTIAL,  # qanundan kənar əsaslarla dərhal ləğv
    "691.2": RESIDENTIAL,  # yaşayışda ləğv bildirişi müddəti (691.3: qısaldılması qüvvəsizdir)
    "688": RESIDENTIAL,  # bron, təminat (2 ay, faizlə), dəbbə pulu
    "692": RESIDENTIAL,  # icarəyə verənin ləğv əsasları
    "693": RESIDENTIAL,  # müddətli müqavilənin uzadılması
    "696": RESIDENTIAL,  # kirayəçinin etiraz hüququ
}


@dataclass(frozen=True)
class Article:
    number: str  # "683"
    title: str  # "Kirayəyə götürülmüş əşyanın üçüncü şəxslərə verilməsi"
    lines: tuple[str, ...]  # maddənin mətni, sətir-sətir

    def point(self, ref: str) -> str | None:
        """'683.2' → həmin bəndin mətni (alt bəndləri ilə). Tapılmasa None."""
        if ref == self.number:
            return "\n".join(self.lines)
        start = re.compile(rf"^{re.escape(ref)}\.?\s")
        child = re.compile(rf"^{re.escape(ref)}\.\d")
        for i, line in enumerate(self.lines):
            if start.match(line):
                block = [line]
                block += [l for l in self.lines[i + 1 :] if child.match(l)]
                return "\n".join(block)
        return None


@cache
def load() -> dict[str, Article]:
    articles: dict[str, Article] = {}
    number = title = None
    body: list[str] = []
    for line in LAW_PATH.read_text(encoding="utf-8").splitlines():
        header = re.match(r"Maddə (\d+)\.\s*(.*)", line)
        if header:
            if number:
                articles[number] = Article(number, title, tuple(body))
            number, title, body = header[1], header[2], []
        elif number and not re.match(r"(\d+-(ci|cı|cu|cü) fəsil\.|§ \d)", line):
            body.append(line)
    if number:
        articles[number] = Article(number, title, tuple(body))
    return articles


def full_text() -> str:
    """Modelə verilən tam qanun mətni."""
    return LAW_PATH.read_text(encoding="utf-8")


def lookup(ref: str) -> tuple[Article, str] | None:
    """'Maddə 683.2' / '683.2' / '683' → (maddə, bəndin mətni). Bazada yoxdursa None."""
    ref = re.sub(r"[^\d.]", "", str(ref)).strip(".")
    if not ref:
        return None
    article = load().get(ref.split(".")[0])
    if not article:
        return None
    text = article.point(ref)
    return (article, text) if text else None


def is_imperative(ref: str, property_type: str) -> bool:
    """Bu maddə/bənd bu əmlak növü üçün tərəflərin dəyişə bilmədiyi normadırmı?

    Əmlak növü müəyyən deyilsə, yalnız hamıya aid normalar sayılır (ehtiyatlı yanaşma).
    """
    ref = re.sub(r"[^\d.]", "", str(ref)).strip(".")
    for key, scope in IMPERATIVE.items():
        related = ref == key or ref.startswith(key + ".") or key.startswith(ref + ".")
        if related and (scope == ALL or property_type == RESIDENTIAL):
            return True
    return False


if __name__ == "__main__":
    arts = load()
    print(f"{len(arts)} maddə: {min(arts, key=int)}–{max(arts, key=int)}")
    for ref in ["688.2", "685.2.2", "691.3", "700", "650", "683.9"]:
        hit = lookup(ref)
        print(ref, "→", hit[1][:80] if hit else "YOXDUR")
