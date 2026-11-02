"""app.py-ın interfeys testləri — AppTest ilə, brauzer və model sorğusu olmadan."""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from agent import parser, verifier

ROOT = Path(__file__).resolve().parent.parent


def app(name: str = "xarab_01.docx", party: str = "icarəçi") -> AppTest:
    path = ROOT / "data/contracts" / name
    data = path.read_bytes()
    lines = parser.read_lines(data, name)
    clauses = parser.split_clauses(lines)
    raw = json.loads((ROOT / "tests/fixtures" / f"{path.stem}.json").read_text(encoding="utf-8"))
    result = verifier.verify(raw, clauses)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["result"] = result
    at.session_state["clauses"] = clauses
    at.session_state["source"] = (data, name, lines)
    at.session_state["filename"] = name
    at.session_state["party"] = party
    at.session_state["run_id"] = 1
    return at.run()


def test_app_renders():
    at = app()
    assert not at.exception


def test_document_shows_every_clause():
    at = app()
    texts = " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption)
    for clause_no in ("3.1.", "4.6.", "6.1."):
        assert clause_no in texts


def test_counter_and_reject_button():
    at = app()
    all_md = " ".join(m.value for m in at.markdown)
    assert "14/14 düzəliş qəbul edilib" in all_md

    reject_btn = next(b for b in at.button if b.key == "off_1_0")
    reject_btn.click().run()

    all_md_after = " ".join(m.value for m in at.markdown)
    assert "13/14 düzəliş qəbul edilib" in all_md_after
    assert at.session_state["use_1_0"] is False


def test_accept_button_restores():
    at = app()
    next(b for b in at.button if b.key == "off_1_0").click().run()
    assert at.session_state["use_1_0"] is False

    accept_btn = next(b for b in at.button if b.key == "on_1_0")
    accept_btn.click().run()
    assert at.session_state["use_1_0"] is True


def test_select_all_buttons():
    at = app()
    next(b for b in at.button if b.key == "all_off_1").click().run()
    all_md_off = " ".join(m.value for m in at.markdown)
    assert "0/14" in all_md_off

    next(b for b in at.button if b.key == "all_on_1").click().run()
    all_md_on = " ".join(m.value for m in at.markdown)
    assert "14/14" in all_md_on


def test_edit_changes_diff():
    at = app()
    at.text_area(key="text_1_0").input("TAMAMİLƏ YENİ MƏTN").run()
    all_md = " ".join(m.value for m in at.markdown)
    assert "TAMAMİLƏ YENİ MƏTN" in all_md


def test_three_download_buttons():
    at = app()
    downloads = at.get("download_button")
    assert len(downloads) == 4
    for d in downloads:
        assert d.url


def test_no_duplicate_widget_keys():
    at = app()
    assert not at.exception
    text_areas = [ta for ta in at.text_area if ta.key == "text_1_0"]
    assert len(text_areas) == 1
