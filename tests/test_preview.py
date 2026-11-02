"""agent/preview.py üçün avtomatik testlər."""

import json
from pathlib import Path

from agent import parser, preview, verifier

ROOT = Path(__file__).resolve().parent.parent


def load(name: str):
    """data/contracts/<name> + tests/fixtures/<stem>.json → (clauses, result)"""
    path = ROOT / "data/contracts" / name
    lines = parser.read_lines(path.read_bytes(), name)
    clauses = parser.split_clauses(lines)
    raw = json.loads((ROOT / "tests/fixtures" / f"{path.stem}.json").read_text(encoding="utf-8"))
    return clauses, verifier.verify(raw, clauses)


def test_rows_cover_every_clause_in_order():
    """xarab_01.docx üçün: bend, basliq və metn sətirlərinin açarları clauses ilə eynidir."""
    clauses, result = load("xarab_01.docx")
    r = preview.rows(clauses, result.findings)
    doc_keys = [row.key for row in r if row.kind in ("bend", "basliq", "metn")]
    assert doc_keys == list(clauses.keys())


def test_row_kinds():
    """xarab_01.docx üçün: Başlıq -> metn, 1 -> basliq, 1.1 -> bend."""
    clauses, result = load("xarab_01.docx")
    r = preview.rows(clauses, result.findings)
    by_key = {row.key: row for row in r if row.key is not None}

    assert by_key["Başlıq"].kind == "metn"
    assert by_key["1"].kind == "basliq"
    assert by_key["1"].text == "MÜQAVİLƏNİN PREDMETİ"
    assert by_key["1.1"].kind == "bend"


def test_findings_attached_to_right_clause():
    """3.3 bəndinə aid tapıntı var, 3.1 bəndinə aid tapıntı isə yoxdur."""
    clauses, result = load("xarab_01.docx")
    r = preview.rows(clauses, result.findings)
    by_key = {row.key: row for row in r if row.key is not None}

    row_33 = by_key["3.3"]
    assert row_33.finding is not None
    assert result.findings[row_33.finding].bend_no == "3.3"

    row_31 = by_key["3.1"]
    assert row_31.finding is None


def test_added_clauses_at_the_end():
    """Çatışmayan bəndlər ("elave") sonda gəlir və sayı teklif-i olan tapıntılara bərabərdir."""
    clauses, result = load("xarab_01.docx")
    r = preview.rows(clauses, result.findings)
    added = [row for row in r if row.kind == "elave"]
    missing_with_proposal = [
        (i, f) for i, f in enumerate(result.findings) if f.tip == "catismayan" and f.teklif
    ]

    assert len(added) == 2
    assert len(added) == len(missing_with_proposal)
    assert r[-len(added) :] == added

    for row, (idx, expected_f) in zip(added, missing_with_proposal, strict=True):
        assert row.key is None
        assert row.text == ""
        assert row.finding == idx
        assert row.notes == ()
        assert result.findings[row.finding] == expected_f


def test_second_finding_on_same_clause_goes_to_notes():
    """Eyni bəndə ikinci tapıntı notes-a düşür, birinci mətni dəyişir (finding)."""
    clauses = {"1.1": "İcarə haqqı hər ayın 1-dək ödənilir."}
    f1 = verifier.Finding(
        tip="qanuna_zidd",
        risk="kritik",
        basliq="Gecikmə faizi",
        izah="Faiz çox yüksəkdir",
        teklif="0.1% azaldılsın",
        bend_no="1.1",
        bend_metni=clauses["1.1"],
    )
    f2 = verifier.Finding(
        tip="birterefli",
        risk="orta",
        basliq="Ödəniş qaydası",
        izah="Birtərəfli şərt",
        teklif="Təklif 2",
        bend_no="1.1",
        bend_metni=clauses["1.1"],
    )
    r = preview.rows(clauses, [f1, f2])
    assert len(r) == 1
    row = r[0]
    assert row.key == "1.1"
    assert row.kind == "bend"
    assert row.finding == 0
    assert row.notes == (1,)


def test_unknown_and_header_findings():
    """Müqavilədə olmayan bənd buraxılır; Başlıq tapıntısı yalnız notes-a düşür."""
    clauses = {
        "Başlıq": "İCARƏ MÜQAVİLƏSİ",
        "1.1": "Bənd 1.1 mətni",
    }
    f_unknown = verifier.Finding(
        tip="qanuna_zidd",
        risk="kritik",
        basliq="Uydurma bənd",
        izah="Müqavilədə yoxdur",
        teklif="Düzəliş",
        bend_no="9.9",
    )
    f_header = verifier.Finding(
        tip="birterefli",
        risk="aşağı",
        basliq="Başlıq qeydi",
        izah="Müqavilənin preambula qeydi",
        teklif="Düzəliş",
        bend_no="Başlıq",
        bend_metni=clauses["Başlıq"],
    )
    r = preview.rows(clauses, [f_unknown, f_header])
    assert len(r) == 2
    by_key = {row.key: row for row in r}

    # 9.9 heç bir sətirdə olmamalıdır
    for row in r:
        assert row.finding != 0
        assert 0 not in row.notes

    # Başlıq sətri
    row_header = by_key["Başlıq"]
    assert row_header.kind == "metn"
    assert row_header.finding is None
    assert row_header.notes == (1,)


def test_empty_inputs():
    """Boş girişlərin idarə edilməsi."""
    assert preview.rows({}, []) == []

    clauses = {"1": "BÖLMƏ", "1.1": "Mətn"}
    r = preview.rows(clauses, [])
    assert len(r) == 2
    assert r[0].finding is None
    assert r[0].notes == ()
    assert r[1].finding is None
    assert r[1].notes == ()


def test_missing_clause_empty_teklif_skipped():
    """Təklifi boş olan çatışmayan bənd üçün sətir yaradılmır."""
    clauses = {"1.1": "Mətn"}
    f_empty = verifier.Finding(
        tip="catismayan",
        risk="orta",
        basliq="Çatışmayan amma təklifsiz",
        izah="İzah",
        teklif="",
        bend_no=None,
    )
    r = preview.rows(clauses, [f_empty])
    assert len(r) == 1
    assert r[0].kind == "bend"


def test_deletion_proposal_assigned():
    """Mövcud bənd üçün təklif boş olduqda da (silmə təklifi) finding təyin olunur."""
    clauses = {"1.1": "Zərərli bənd mətni"}
    f_delete = verifier.Finding(
        tip="qanuna_zidd",
        risk="kritik",
        basliq="Bənd silinməlidir",
        izah="Bu bənd tamamilə qanunsuzdur",
        teklif="",
        bend_no="1.1",
        bend_metni=clauses["1.1"],
    )
    r = preview.rows(clauses, [f_delete])
    assert len(r) == 1
    assert r[0].finding == 0
    assert r[0].notes == ()
