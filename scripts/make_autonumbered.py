"""Test üçün: xarab_01.docx-in mətnini Word-un avtomatik nömrələməsi ilə yenidən qurur.

Real müqavilələrin çoxunda "3.3." nömrəsi mətndə yazılmır — Word onu numbering.xml-dən çəkir.
Nəticə: data/contracts/xarab_01_avto.docx
"""

import re
from pathlib import Path

import docx
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data/contracts/xarab_01.docx"
TARGET = ROOT / "data/contracts/xarab_01_avto.docx"
CLAUSE = re.compile(r"^(\d+)(?:\.(\d+))?\.?\s+(.*)$")

ABSTRACT = f"""<w:abstractNum {nsdecls("w")} w:abstractNumId="10">
  <w:multiLevelType w:val="multilevel"/>
  <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
  <w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1.%2."/></w:lvl>
</w:abstractNum>"""
NUM = f'<w:num {nsdecls("w")} w:numId="10"><w:abstractNumId w:val="10"/></w:num>'

src = docx.Document(SOURCE)
out = docx.Document()
numbering = out.part.numbering_part.element
numbering.insert(0, parse_xml(ABSTRACT))  # abstractNum-lar num-lardan əvvəl gəlməlidir
numbering.append(parse_xml(NUM))

for p in src.paragraphs:
    m = CLAUSE.match(p.text.strip())
    para = out.add_paragraph(m[3] if m else p.text)
    if m:
        level = 1 if m[2] else 0
        para._p.get_or_add_pPr().append(
            parse_xml(
                f'<w:numPr {nsdecls("w")}><w:ilvl w:val="{level}"/><w:numId w:val="10"/></w:numPr>'
            )
        )
out.save(TARGET)
print(TARGET.relative_to(ROOT))
