"""Müştəri üçün hüquqi rəy (Word) — mövcud təhlildən qurulur, əlavə model sorğusu yoxdur.

Redline qarşı tərəfə gedir, rəy isə müştəriyə: burada qanunun mətni, danışıq strategiyası
(güzəşt variantı, arqument) və tövsiyə var. Yalnız vəkilin seçdiyi / redaktə etdiyi
düzəlişlərdən qurulur.
"""

import io
from datetime import datetime
from zoneinfo import ZoneInfo

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from agent import parser
from agent.redliner import new_document
from agent.score import score
from agent.verifier import Result

TIP_LABEL = {
    "qanuna_zidd": "qanuna zidd (qüvvəsiz) şərt",
    "birterefli": "birtərəfli şərt",
    "catismayan": "çatışmayan bənd",
}
RISK_COLOR = {"kritik": RGBColor(0xB4, 0x23, 0x18), "orta": RGBColor(0xB2, 0x6B, 0x00),
              "aşağı": RGBColor(0x6B, 0x6B, 0x6B)}  # fmt: skip
LAW_SOURCE = "Mülki Məcəllə, 33–34-cü fəsillər (e-qanun.az, 27.09.2026 tarixli redaksiya)"


def _label(paragraph, label: str, text: str, italic: bool = False) -> None:
    paragraph.add_run(f"{label} ").bold = True
    paragraph.add_run(text).italic = italic


def build(result: Result, party: str, filename: str, total_findings: int | None = None) -> bytes:
    """Hüquqi rəyin DOCX baytları. total_findings — agentin ilkin tapıntı sayı (vəkil seçməmişdən əvvəl)."""
    doc = new_document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    risk = score(result.findings)
    counts = {r: sum(f.risk == r for f in result.findings) for r in ("kritik", "orta", "aşağı")}
    void = [f for f in result.findings if f.tip == "qanuna_zidd"]

    title = doc.add_heading("HÜQUQİ RƏY", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = doc.add_paragraph(
        "İcarə müqaviləsinin Azərbaycan Respublikası Mülki Məcəlləsinə uyğunluğu barədə"
    )
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    meta = doc.add_table(rows=0, cols=2)
    meta.style = "Table Grid"
    for key, value in [
        ("Sənəd", filename),
        ("Müştərinin mövqeyi", party),
        ("Əmlak növü", result.emlak_novu),
        ("Müqavilənin dili", parser.LANGUAGES.get(result.dil, result.dil)),
        ("Tarix", f"{datetime.now(ZoneInfo('Asia/Baku')):%d.%m.%Y}"),
    ]:
        row = meta.add_row().cells
        row[0].text, row[1].text = key, value
        row[0].paragraphs[0].runs[0].bold = True

    # 1. Qısa nəticə
    doc.add_heading("1. Qısa nəticə", level=1)
    doc.add_paragraph(
        f"Müqavilə müştərinin ({party}) maraqları baxımından {risk.level} daşıyır — risk balı "
        f"{risk.value}/100. Cəmi {len(result.findings)} məsələ aşkar edilib: {counts['kritik']} "
        f"kritik, {counts['orta']} orta, {counts['aşağı']} aşağı risk; onlardan {len(void)}-i "
        "qanunun imperativ normasına zidd olduğu üçün qüvvəsizdir."
    )
    critical = [f for f in result.findings if f.risk == "kritik"]
    for f in critical:
        where = f"Bənd {f.bend_no}" if f.bend_no else "Çatışmayan bənd"
        doc.add_paragraph(f"{where}: {f.basliq}", style="List Bullet")
    doc.add_paragraph().add_run(
        "Tövsiyə: müqavilə aşağıdakı kritik düzəlişlər qəbul edilmədən imzalanmamalıdır."
        if critical
        else "Tövsiyə: müqavilə aşağıdakı düzəlişlər nəzərə alınmaqla imzalana bilər."
    ).bold = True

    # 2. Əsas şərtlər
    if result.summary.fields:
        doc.add_heading("2. Müqavilənin əsas şərtləri", level=1)
        table = doc.add_table(rows=0, cols=3)
        table.style = "Table Grid"
        for item in result.summary.fields:
            row = table.add_row().cells
            row[0].text, row[1].text = item.label, item.deyer
            row[2].text = f"bənd {item.bend_no}" if item.bend_no else ""
            row[0].paragraphs[0].runs[0].bold = True

    # 3. Məsələlər
    doc.add_heading("3. Aşkar edilmiş məsələlər və tövsiyələr", level=1)
    for n, f in enumerate(result.findings, 1):
        where = f"Bənd {f.bend_no}" if f.bend_no else "Müqavilədə yoxdur"
        doc.add_heading(f"3.{n}. {where} — {f.basliq}", level=2)
        line = doc.add_paragraph()
        mark = line.add_run(f"Risk: {f.risk}")
        mark.bold, mark.font.color.rgb = True, RISK_COLOR[f.risk]
        line.add_run(f" · {TIP_LABEL[f.tip]}")
        if f.bend_metni:
            _label(doc.add_paragraph(), "Müqavilədə:", f.bend_metni, italic=True)
        _label(doc.add_paragraph(), "Hüquqi qiymətləndirmə:", f.izah)
        if f.qeyd:
            _label(doc.add_paragraph(), "Qeyd:", f.qeyd)
        if f.madde_metni:
            _label(doc.add_paragraph(), "Qanun:", f.madde_basliq or "")
            doc.add_paragraph(f.madde_metni, style="Quote")
        if f.teklif:
            _label(doc.add_paragraph(), "Tövsiyə olunan redaksiya:", f.teklif)
        elif f.bend_no:
            _label(doc.add_paragraph(), "Tövsiyə:", "bəndin müqavilədən tamamilə çıxarılması.")
        if f.guzest:
            _label(doc.add_paragraph(), "Güzəşt variantı (danışıq üçün):", f.guzest)
        if f.arqument:
            _label(doc.add_paragraph(), "Qarşı tərəfə arqument:", f.arqument)

    section = 4
    missing = [i.movzu for i in result.checklist if not i.var]
    if missing:
        doc.add_heading(f"{section}. Müqavilədə olmayan vacib mövzular", level=1)
        for topic in missing:
            doc.add_paragraph(topic, style="List Bullet")
        section += 1
    if result.checks:
        doc.add_heading(f"{section}. Texniki qeydlər", level=1)
        for c in result.checks:
            doc.add_paragraph(f"Bənd {c.bend_no} — {c.basliq}. {c.izah}", style="List Bullet")
        section += 1

    doc.add_heading(f"{section}. Metodologiya və məhdudiyyətlər", level=1)
    selected = (
        f" Vəkil agentin {total_findings} tövsiyəsindən {len(result.findings)}-ni bu rəyə daxil edib."
        if total_findings and total_findings != len(result.findings)
        else ""
    )
    doc.add_paragraph(
        f"Təhlil {LAW_SOURCE} əsasında aparılıb. Rəy açıq çəkili Gemma 4 modeli üzərində qurulmuş "
        "süni intellekt köməkçisi ilə hazırlanıb; hər qanun istinadı və müqavilə bəndi qanunun və "
        f"müqavilənin mətni ilə avtomatik yoxlanılıb.{selected} Rəy vəkilin peşəkar qiymətləndirməsini "
        "əvəz etmir və yalnız göstərilən fəsillərin normalarını əhatə edir."
    )
    doc.add_paragraph()
    doc.add_paragraph("Vəkil: ______________________        İmza: ____________")

    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()
