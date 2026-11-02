"""Word-un avtomatik nömrələməsini bərpa edir: abzasın ekranda görünən nömrəsi ("3.3.").

Real müqavilələrin çoxunda nömrə mətnin içində yazılmır — Word onu numbering.xml-dən
hesablayır, python-docx isə göstərmir. Bu modul Word-un məntiqini təkrarlayır:
hər siyahının (abstractNum) səviyyə sayğacları, üst səviyyə artanda alt səviyyələrin
sıfırlanması, lvlText şablonu ("%1.%2.") və start / startOverride dəyərləri.
"""

from docx.document import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

ROMAN = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
         (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]  # fmt: skip


def _roman(n: int) -> str:
    out = ""
    for value, letters in ROMAN:
        while n >= value:
            out, n = out + letters, n - value
    return out


def _format(n: int, fmt: str) -> str:
    if fmt == "lowerLetter":
        return chr(ord("a") + (n - 1) % 26)
    if fmt == "upperLetter":
        return chr(ord("A") + (n - 1) % 26)
    if fmt == "lowerRoman":
        return _roman(n)
    if fmt == "upperRoman":
        return _roman(n).upper()
    return str(n)  # decimal və tanınmayan formatlar


def _val(element, tag: str, default=None):
    child = element.find(qn(tag)) if element is not None else None
    return child.get(qn("w:val")) if child is not None else default


class Numbering:
    def __init__(self, document: Document):
        self.levels: dict[
            str, dict[int, tuple[int, str, str]]
        ] = {}  # abstractId → ilvl → (start, fmt, text)
        self.nums: dict[str, tuple[str, dict[int, int]]] = {}  # numId → (abstractId, startOverride)
        self.counters: dict[str, list[int]] = {}
        self.started: set[str] = set()
        self.styles = document.styles.element

        try:
            root = document.part.numbering_part.element
        except (KeyError, NotImplementedError):
            return
        for abstract in root.findall(qn("w:abstractNum")):
            levels = {}
            for lvl in abstract.findall(qn("w:lvl")):
                levels[int(lvl.get(qn("w:ilvl")))] = (
                    int(_val(lvl, "w:start", "1")),
                    _val(lvl, "w:numFmt", "decimal"),
                    _val(lvl, "w:lvlText", ""),
                )
            self.levels[abstract.get(qn("w:abstractNumId"))] = levels
        for num in root.findall(qn("w:num")):
            overrides = {
                int(o.get(qn("w:ilvl"))): int(_val(o, "w:startOverride"))
                for o in num.findall(qn("w:lvlOverride"))
                if _val(o, "w:startOverride") is not None
            }
            self.nums[num.get(qn("w:numId"))] = (_val(num, "w:abstractNumId"), overrides)

    def _num_pr(self, paragraph: Paragraph) -> tuple[str, int] | None:
        """(numId, ilvl) — abzasın öz xassələrindən və ya üslubundan (basedOn zənciri ilə)."""
        ppr = paragraph._p.pPr
        num_pr = ppr.find(qn("w:numPr")) if ppr is not None else None
        style_id = _val(ppr, "w:pStyle")
        while num_pr is None and style_id:
            style = next(
                (
                    s
                    for s in self.styles.findall(qn("w:style"))
                    if s.get(qn("w:styleId")) == style_id
                ),
                None,
            )
            if style is None:
                break
            num_pr = style.find(f"{qn('w:pPr')}/{qn('w:numPr')}")
            style_id = _val(style, "w:basedOn")
        if num_pr is None:
            return None
        num_id = _val(num_pr, "w:numId")
        if not num_id or num_id == "0":  # numId=0 — nömrələmə söndürülüb
            return None
        return num_id, int(_val(num_pr, "w:ilvl", "0"))

    def label(self, paragraph: Paragraph) -> str:
        """Abzasın nömrəsi ("3.3.") və ya nömrəsi yoxdursa "". Abzaslar sənəd sırası ilə verilməlidir."""
        found = self._num_pr(paragraph)
        if not found or found[0] not in self.nums:
            return ""
        num_id, ilvl = found
        abstract_id, overrides = self.nums[num_id]
        levels = self.levels.get(abstract_id, {})
        if ilvl not in levels:
            return ""

        counters = self.counters.setdefault(abstract_id, [0] * 9)
        if num_id not in self.started:  # startOverride yeni siyahı instansını sıfırlayır
            self.started.add(num_id)
            for level, start in overrides.items():
                counters[level] = start - 1
        start, fmt, text = levels[ilvl]
        counters[ilvl] = counters[ilvl] + 1 if counters[ilvl] else start
        for deeper in range(ilvl + 1, 9):
            counters[deeper] = 0

        if fmt in ("bullet", "none"):
            return ""
        for level in range(ilvl, -1, -1):
            if f"%{level + 1}" in text:
                lvl_start, lvl_fmt, _ = levels.get(level, (1, "decimal", ""))
                value = counters[level] or lvl_start
                text = text.replace(f"%{level + 1}", _format(value, lvl_fmt))
        return text.strip()


def visible_text(paragraph: Paragraph) -> str:
    """Abzasın Word-da görünən mətni: əlavələr (w:ins) daxil, silinənlər (w:delText) xaric.

    python-docx-in p.text-i <w:ins> içindəki mətni görmür — qarşı tərəfin track changes ilə
    göndərdiyi müqavilədə bu, mətnin itməsi deməkdir.
    """
    parts = []
    for el in paragraph._p.iter(qn("w:t"), qn("w:tab"), qn("w:br"), qn("w:cr")):
        if el.getparent().tag != qn("w:r"):  # pPr/tabs/tab — tab dayanacağının təsviri, mətn deyil
            continue
        if el.tag == qn("w:t"):
            parts.append(el.text or "")
        else:
            parts.append("\t" if el.tag == qn("w:tab") else "\n")
    return "".join(parts)


def paragraph_lines(document: Document) -> list[tuple[Paragraph, str]]:
    """Boş olmayan abzaslar və onların ekranda görünən mətni (avtomatik nömrə daxil).

    Parser və Redliner eyni funksiyanı işlədir ki, bəndlərin bölgüsü üst-üstə düşsün.
    """
    numbering = Numbering(document)
    out = []
    for p in document.paragraphs:
        label = numbering.label(p)  # boş abzaslar da sayğacı dəyişə bilər — hamısından keçirik
        text = visible_text(p).strip()
        if text:
            out.append((p, f"{label} {text}" if label else text))
    return out
