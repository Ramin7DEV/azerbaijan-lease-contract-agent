"""API-siz testlər: saxlanmış model cavabları (tests/fixtures) ilə bütün boru xətti.

İşə salmaq: uv run pytest
"""

import dataclasses
import io
import json
from datetime import date
from pathlib import Path

import docx
import pytest
from docx.oxml.ns import qn

from agent import checks, compare, ics, law, memo, parser, qa, redliner, score, verifier
from agent.numbering import paragraph_lines

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "data/contracts"
FIXTURES = Path(__file__).parent / "fixtures"


def load_contract(name: str) -> tuple[bytes | None, list[str]]:
    path = CONTRACTS / name
    if path.suffix == ".txt":
        return None, [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return path.read_bytes(), parser.read_lines(path.read_bytes(), name)


def result_for(name: str) -> tuple[verifier.Result, bytes | None, list[str]]:
    data, lines = load_contract(name)
    raw = json.loads((FIXTURES / f"{Path(name).stem}.json").read_text(encoding="utf-8"))
    return verifier.verify(raw, parser.split_clauses(lines)), data, lines


def body_texts(document, reject: bool) -> list[str]:
    """Gövdə abzaslarının mətni: reject=True — "Reject All" görünüşü (əlavələr yox, silinənlər var)."""
    out = []
    for p in document.element.body.findall(qn("w:p")):
        ppr_rpr = f"{qn('w:pPr')}/{qn('w:rPr')}/"
        if reject and p.find(ppr_rpr + qn("w:ins")) is not None:
            continue
        text = ""
        for el in p.iter(qn("w:t"), qn("w:delText")):
            inside = {a.tag for a in el.iterancestors()}
            if (reject and qn("w:ins") in inside) or (not reject and qn("w:del") in inside):
                continue
            text += el.text or ""
        if text.strip():
            out.append(text)
    return out


# --- qanun bazası ---


def test_law_has_all_articles():
    articles = law.load()
    assert len(articles) == 48
    assert min(articles, key=int) == "675" and max(articles, key=int) == "722"


@pytest.mark.parametrize(
    "ref, found",
    [("688.2", True), ("685.2.2", True), ("700", True), ("650", False), ("683.9", False)],
)
def test_law_lookup(ref, found):
    assert (law.lookup(ref) is not None) == found


@pytest.mark.parametrize(
    "ref, kind, expected",
    [
        ("688.2", "yaşayış", True),
        ("688.2", "qeyri-yaşayış", False),  # 688.3: qadağa yalnız yaşayışa aiddir
        ("691.3", "qeyri-yaşayış", True),
        ("691.2", "yaşayış", True),
        ("691.2", "qeyri-yaşayış", False),
        ("699.1", "yaşayış", False),  # dispozitiv norma
        ("677.4", "müəyyən deyil", True),
        ("677.1.1", "müəyyən deyil", False),  # növ bilinmirsə, yalnız hamıya aid normalar
    ],
)
def test_imperative_norms(ref, kind, expected):
    assert law.is_imperative(ref, kind) == expected


# --- parser ---


def test_parser_numbered_clauses():
    _, lines = load_contract("xarab_01.docx")
    clauses = parser.split_clauses(lines)
    assert (
        clauses["3.4"] == "İcarəçi müqavilə bağlanarkən İcarəyə verənə 500 manat dəbbə pulu ödəyir."
    )
    assert "Başlıq" in clauses and "6.1" in clauses


def test_parser_reads_word_autonumbering():
    """Word-un avtomatik nömrələri mətndə yoxdur — parser onları numbering.xml-dən bərpa etməlidir."""
    _, manual = load_contract("xarab_01.docx")
    _, auto = load_contract("xarab_01_avto.docx")
    a, b = parser.split_clauses(manual), parser.split_clauses(auto)
    assert list(a) == list(b)
    assert all(a[k] == b[k] for k in a if k != "6.1")  # avto versiyada imza cədvəli yoxdur


def test_parser_unnumbered_text():
    assert list(parser.parse_text("Birinci abzas\nİkinci abzas")) == ["P1", "P2"]


# --- verifier ---


def test_verifier_rejects_fabrications():
    clauses = {"1.1": "mətn"}
    raw = {
        "tapintilar": [
            {"tip": "qanuna_zidd", "bend_no": "1.1", "risk": "kritik", "madde_no": "650"},
            {"tip": "birterefli", "bend_no": "9.9", "risk": "orta", "madde_no": None},
            {"tip": "qanuna_zidd", "bend_no": "1.1", "risk": "kritik", "madde_no": None},
        ]
    }
    result = verifier.verify(raw, clauses)
    assert result.findings == []
    reasons = " ".join(reason for _, reason in result.rejected)
    assert "650" in reasons and "9.9" in reasons and "maddə göstərilməyib" in reasons


def test_verifier_takes_text_from_sources_not_model():
    raw = {"tapintilar": [{"tip": "qanuna_zidd", "bend_no": "3.3", "madde_no": "688.2",
                           "risk": "kritik", "bend_metni": "UYDURMA", "madde_metni": "UYDURMA"}]}  # fmt: skip
    finding = verifier.verify({"emlak_novu": "yaşayış", **raw}, {"3.3": "orijinal"}).findings[0]
    assert finding.bend_metni == "orijinal"
    assert finding.madde_metni.startswith("688.2.")


def test_verifier_downgrades_non_imperative():
    raw = {"emlak_novu": "qeyri-yaşayış", "tapintilar": [
        {"tip": "qanuna_zidd", "bend_no": "3.3", "risk": "orta", "madde_no": "688.2"}]}  # fmt: skip
    finding = verifier.verify(raw, {"3.3": "4 aylıq təminat"}).findings[0]
    assert finding.tip == "birterefli" and finding.qeyd


# --- saxlanmış model cavabları ilə keyfiyyət ---

EXPECTED = {
    "xarab_01.docx": {
        "3.3",
        "3.4",
        "3.5",
        "4.1",
        "4.2",
        "4.3",
        "4.4",
        "4.5",
        "5.1",
        "5.2",
        "5.3",
        "5.4",
    },
    "ofis_01.txt": {"3.3", "3.4", "4.3", "5.1", "5.2", "5.3"},
    "ru_01.txt": {"3.2", "3.3", "4.1", "4.2", "5.1", "5.2"},
    "en_01.txt": {"3.2", "3.3", "4.2", "5.1", "5.2", "5.3"},
}
TRAPS = {"ofis_01.txt": {"3.2", "4.4", "4.5"}, "en_01.txt": {"3.1", "4.1", "4.3", "6.1"}}


@pytest.mark.parametrize("name", EXPECTED)
def test_fixture_finds_expected_clauses(name):
    result, _, _ = result_for(name)
    found = {f.bend_no for f in result.findings if f.bend_no}
    assert EXPECTED[name] <= found
    assert not (TRAPS.get(name, set()) & found)
    assert result.rejected == []


def test_clean_contract_has_no_serious_findings():
    result, _, _ = result_for("temiz_01.txt")
    assert not [f for f in result.findings if f.risk == "kritik" or f.tip == "qanuna_zidd"]
    assert all(item.var for item in result.checklist)
    assert score.score(result.findings).value < 25


def test_office_is_not_treated_as_residential():
    result, _, _ = result_for("ofis_01.txt")
    assert result.emlak_novu == "qeyri-yaşayış"
    assert not any(law.is_imperative(f.madde_no or "", "qeyri-yaşayış") is False
                   and f.tip == "qanuna_zidd" for f in result.findings)  # fmt: skip


# --- risk balı ---


def test_score_curve():
    make = lambda risk: verifier.Finding("birterefli", risk, "", "", "")
    assert score.score([]).value == 0
    assert score.score([make("kritik")]).value == 28
    assert score.score([make("kritik")] * 3).value == 63
    assert score.score([make("kritik")] * 20).value <= 100


# --- redliner ---


@pytest.mark.parametrize("name", ["xarab_01.docx", "ofis_01.txt"])
def test_redline_reject_all_restores_original(name):
    result, data, lines = result_for(name)
    original = redliner.load(data, name, lines)
    expected = [p.text for p in original.paragraphs if p.text.strip()]
    out = redliner.redline(redliner.load(data, name, lines), result)
    assert body_texts(docx.Document(io.BytesIO(out)), reject=True) == expected


def test_redline_writes_suggestions_and_comments():
    result, data, lines = result_for("xarab_01.docx")
    out = docx.Document(io.BytesIO(redliner.redline(redliner.load(data, "x.docx", lines), result)))
    accepted = "\n".join(body_texts(out, reject=False))
    assert "dəbbə pulu" not in accepted  # 3.4 silinməli idi
    assert "Əlavə bənd" in accepted
    assert len(out.comments) == len(result.findings) + 1  # + xülasə şərhi


def test_redline_respects_lawyer_selection_and_edits():
    result, data, lines = result_for("xarab_01.docx")
    first, *rest = result.findings
    edited = dataclasses.replace(first, teklif="VƏKİLİN MƏTNİ")
    skipped = rest[0]
    chosen = dataclasses.replace(result, findings=[edited, *rest[1:]])
    out = docx.Document(io.BytesIO(redliner.redline(redliner.load(data, "x.docx", lines), chosen)))
    accepted = "\n".join(body_texts(out, reject=False))
    assert "VƏKİLİN MƏTNİ" in accepted
    assert skipped.bend_metni.splitlines()[0] in accepted  # söndürülmüş bənd dəyişməyib


def test_clean_version_has_no_tracking():
    result, data, lines = result_for("xarab_01.docx")
    out = redliner.redline(redliner.load(data, "x.docx", lines), result, clean=True)
    xml = docx.Document(io.BytesIO(out)).element.xml
    assert "<w:ins " not in xml and "<w:del " not in xml and "commentReference" not in xml


def test_redline_autonumbered_document():
    """Avtomatik nömrəli sənəddə düzəlişlər düzgün bəndlərə düşməlidir."""
    result, _, _ = result_for("xarab_01.docx")  # eyni mətn, eyni bənd nömrələri
    data, lines = load_contract("xarab_01_avto.docx")
    out = docx.Document(io.BytesIO(redliner.redline(redliner.load(data, "a.docx", lines), result)))
    by_label = {line.split(" ", 1)[0]: line for _, line in paragraph_lines(out)}
    assert "2 (iki) aylıq" in by_label["3.3."]


def test_redline_marks_only_changed_words():
    """Söz səviyyəsində redline: 3.3-də yalnız rəqəmlər və son cümlə dəyişir, qalan mətn toxunulmaz."""
    result, data, lines = result_for("xarab_01.docx")
    out = docx.Document(io.BytesIO(redliner.redline(redliner.load(data, "x.docx", lines), result)))
    clause = next(
        p for p in out.element.body.findall(qn("w:p"))
        if "".join(t.text or "" for t in p.iter(qn("w:t"))).startswith("3.3.")
    )  # fmt: skip
    kept = "".join(t.text or "" for r in clause.findall(qn("w:r")) for t in r.iter(qn("w:t")))
    deleted = "".join(t.text or "" for t in clause.iter(qn("w:delText")))
    assert "aylıq icarə haqqı məbləğində, yəni" in kept  # dəyişməyən hissə adi mətn olaraq qalır
    assert "3 (üç" in deleted and "2400" in deleted
    assert "İcarəçi müqavilə imzalanarkən" not in deleted


def test_merge_small_gaps_joins_word_by_word_changes():
    old = ["a", " ", "b", " ", "c"]
    ops = [
        ("replace", 0, 1, 0, 1),
        ("equal", 1, 2, 1, 2),
        ("replace", 2, 3, 2, 3),
        ("equal", 3, 5, 3, 5),
    ]
    assert redliner.merge_small_gaps(ops, old)[0] == ("replace", 0, 3, 0, 3)


# --- texniki yoxlamalar (modelsiz) ---


def test_checks_find_mechanical_errors():
    clauses = {
        "Başlıq": 'A (bundan sonra "İcarəyə verən") və B (bundan sonra "İcarəçi")',
        "3.1": "Aylıq icarə haqqı 800 (yeddi yüz) manat təşkil edir.",
        "3.2": "Təminat 1600 (min altı yüz) manatdır.",
        "4.1": "Kirayəçi 7.2-ci bəndə uyğun olaraq mənzili qaytarır.",
        "2.1": "Müqavilə 31 iyun 2026-cı il tarixdən başlayır.",
        "2.2": "Müqavilə 1 may 2027-ci il tarixdən 1 may 2026-cı il tarixədək bağlanır.",
    }
    found = {(c.bend_no, c.basliq) for c in checks.run(clauses)}
    assert found == {
        ("3.1", "Rəqəm sözlə uyğun gəlmir"),
        ("4.1", "Mövcud olmayan bəndə istinad"),
        ("4.1", "Tərəf fərqli adlandırılıb"),
        ("2.1", "Mövcud olmayan tarix"),
        ("2.2", "Bitmə tarixi başlanğıcdan əvvəldir"),
    }


@pytest.mark.parametrize("name", ["xarab_01.docx", "ofis_01.txt", "temiz_01.txt", "kor_01.txt"])
def test_checks_no_false_alarms_on_clean_mechanics(name):
    _, lines = load_contract(name)
    assert checks.run(parser.split_clauses(lines)) == []


def test_words_to_number():
    assert checks.words_to_number("iki min dörd yüz manat") == 2400
    assert checks.words_to_number("səkkiz yüz alma") is None


# --- müqavilə kartı və təqvim ---


def test_summary_flags_fabricated_numbers_and_computed_dates():
    clauses = {
        "3.1": "Aylıq icarə haqqı 800 manat.",
        "2.1": "Müqavilə 1 oktyabr 2026-cı ildən 3 il.",
    }
    raw = {
        "icare_haqqi": {"deyer": "950 manat", "bend_no": "3.1"},
        "muddet": {"deyer": "3 il", "bend_no": "2.1"},
        "baslangic_tarixi": "2026-10-01",
        "bitme_tarixi": "2029-09-30",  # model hesablayıb — müqavilədə yazılmayıb
        "odenis_gunu": 45,
    }
    summary = verifier.verify_summary(raw, clauses)
    assert [f.yoxlanildi for f in summary.fields] == [False, True]
    assert summary.baslangic == date(2026, 10, 1) and summary.bitme is None
    assert summary.odenis_gunu is None


def test_summary_from_fixture():
    result, _, _ = result_for("xarab_01.docx")
    labels = {f.label for f in result.summary.fields}
    assert {"İcarəyə verən", "İcarəçi", "İcarə haqqı", "Təminat", "Müddət"} <= labels
    assert all(f.yoxlanildi for f in result.summary.fields)
    assert result.summary.bitme == date(2027, 8, 31)


def test_calendar_events():
    result = verifier.Result(
        "yaşayış",
        summary=verifier.Summary(
            baslangic=date(2026, 10, 1), bitme=date(2028, 9, 30), odenis_gunu=5
        ),
    )
    days = {title: day for day, title, _, _ in ics.events(result)}
    assert days["Son gün: müqavilənin uzadılmasını yazılı tələb etmək"] == date(2028, 7, 30)
    assert days["İcarə haqqının ödənilməsi"] == date(2026, 10, 5)
    assert ics.build(result, "x").decode().count("BEGIN:VEVENT") == 3


# --- danışıq mövqeləri ---


def test_negotiation_stays_out_of_word():
    """Güzəşt variantı və arqument daxili strategiyadır — qarşı tərəfə gedən Word faylına düşməməlidir."""
    result, data, lines = result_for("xarab_01.docx")
    assert any(f.guzest for f in result.findings) and all(f.arqument for f in result.findings)
    out = redliner.redline(redliner.load(data, "x.docx", lines), result)
    comments = docx.Document(io.BytesIO(out)).part.package
    xml = b"".join(p.blob for p in comments.parts if p.partname.endswith("comments.xml"))
    text = xml.decode("utf-8")
    assert not any(f.guzest and f.guzest[:40] in text for f in result.findings)
    assert not any(f.arqument[:40] in text for f in result.findings)


def test_checks_become_comments_without_changing_text():
    result, data, lines = result_for("temiz_01.txt")
    result.checks = [checks.Check("3.1", "Rəqəm sözlə uyğun gəlmir", "test izahı")]
    result.findings = []
    out = docx.Document(io.BytesIO(redliner.redline(redliner.load(data, "t.txt", lines), result)))
    assert body_texts(out, reject=False) == [l for l in lines]
    assert any("Texniki yoxlama" in c.text for c in out.comments)


# --- sual-cavab ---


def test_qa_verifies_citations(monkeypatch):
    fake = {"cavab": "Bəli. Maddə 650-yə görə...", "bendler": ["5.4", "9.9"], "maddeler": ["699.1"]}
    monkeypatch.setattr(qa.analyzer, "ask_json", lambda system, user, refresh=False: fake)
    _, lines = load_contract("xarab_01.docx")
    answer = qa.ask("Satılsa?", parser.split_clauses(lines), "icarəçi")
    assert [no for no, _ in answer.bendler] == ["5.4"]
    assert [no for no, _, _ in answer.maddeler] == ["699.1"]
    assert "bənd 9.9 (müqavilədə yoxdur)" in answer.atildi
    assert "Maddə 650 (bazada yoxdur)" in answer.atildi  # mətndə adı çəkilən uydurma maddə


# --- rus / ingilis dilli müqavilələr ---


@pytest.mark.parametrize(
    "name, lang", [("xarab_01.docx", "az"), ("ru_01.txt", "ru"), ("en_01.txt", "en")]
)
def test_language_detection(name, lang):
    _, lines = load_contract(name)
    assert parser.detect_language(parser.split_clauses(lines)) == lang


@pytest.mark.parametrize("name, lang", [("ru_01.txt", "ru"), ("en_01.txt", "en")])
def test_foreign_contract_suggestions_in_contract_language(name, lang):
    result, data, lines = result_for(name)
    assert result.dil == lang
    texts = [t for f in result.findings for t in (f.teklif, f.guzest) if t]
    assert texts and all(parser.detect_language({"t": t}) == lang for t in texts)
    assert all(parser.detect_language({"t": f.izah}) == "az" for f in result.findings)  # vəkil üçün
    out = docx.Document(io.BytesIO(redliner.redline(redliner.load(data, name, lines), result)))
    added = [
        t for t in body_texts(out, reject=False) if t.startswith(("Дополнительный", "Additional"))
    ]
    assert added  # "Əlavə bənd" başlığı müqavilənin dilində
    assert checks.run(parser.split_clauses(lines)) == []  # AZ-yə xas yoxlamalar işə düşmür


# --- versiya müqayisəsi ---


def v2_changes():
    old_result, data, old_lines = result_for("xarab_01.docx")
    new_lines = parser.read_lines((CONTRACTS / "xarab_01_v2.txt").read_bytes(), "v2.txt")
    old, new = parser.split_clauses(old_lines), parser.split_clauses(new_lines)
    return old_result, data, old_lines, new_lines, compare.align(old, new)


def test_compare_aligns_by_text_despite_renumbering():
    _, _, _, _, changes = v2_changes()
    moved = {(c.status, c.old_key, c.new_key) for c in changes if c.status != "eyni"}
    assert moved == {
        ("dəyişib", "3.3", "3.3"), ("silinib", "3.4", None), ("silinib", "3.5", None),
        ("əlavə", None, "3.4"), ("dəyişib", "5.1", "5.1"), ("silinib", "5.4", None),
        ("əlavə", None, "5.4"), ("əlavə", None, "6.2"),
    }  # fmt: skip
    assert ("eyni", "6.1", "6.1") in {(c.status, c.old_key, c.new_key) for c in changes}


def test_compare_tracks_our_proposals():
    old_result, _, _, _, changes = v2_changes()
    status = {(p.finding.bend_no or p.finding.basliq): p.status
              for p in compare.track(old_result.findings, changes)}  # fmt: skip
    assert status["3.3"] == "qəbul edilib"
    assert status["3.4"] == "qəbul edilib"  # silinməsini təklif etmişdik
    assert status["3.5"] == "güzəşt variantı qəbul edilib"  # indi 3.4 nömrəsi ilə
    assert status["5.4"] == "qəbul edilib"
    assert status["5.1"] == "başqa cür dəyişdirilib"
    assert status["4.1"] == "rədd edilib"
    fors = next(v for k, v in status.items() if "Fors-major" in k)
    assert fors == "qismən qəbul edilib"


def test_compare_redline_reject_is_old_accept_contains_new():
    _, data, _, _, changes = v2_changes()
    original = [p.text for p in redliner.load(data, "x.docx", []).paragraphs if p.text.strip()]
    out = docx.Document(io.BytesIO(compare.redline(redliner.load(data, "x.docx", []), changes)))
    assert body_texts(out, reject=True) == original
    accepted = "\n".join(body_texts(out, reject=False))
    assert "ev heyvanı" in accepted and "fors-major" in accepted and "dəbbə" not in accepted


def test_diff_markdown_marks_changes():
    md = compare.diff_markdown("haqqı 800 manat", "haqqı 900 manat")
    assert "~~800~~" in md and "**900**" in md


# --- hüquqi rəy ---


def test_memo_contains_selected_findings_and_strategy():
    result, _, _ = result_for("xarab_01.docx")
    chosen = dataclasses.replace(result, findings=result.findings[:3])
    doc = docx.Document(io.BytesIO(memo.build(chosen, "icarəçi", "x.docx", total_findings=14)))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "HÜQUQİ RƏY" in text and "1. Qısa nəticə" in text
    assert all(f.basliq in text for f in chosen.findings)
    assert result.findings[5].basliq not in text  # vəkilin seçmədiyi rəyə düşmür
    assert any(f.guzest and f.guzest[:30] in text for f in chosen.findings)  # daxili strategiya var
    assert "14 tövsiyəsindən 3-ni" in text
