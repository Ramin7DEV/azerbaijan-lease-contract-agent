"""Streamlit: versiya müqayisəsi rejimi — köhnə və yeni versiya, təkliflərin taleyi, risk dəyişikliyi."""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st

from agent import analyzer, checks, compare, parser, redliner, score, verifier

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
STATUS_ICON = {
    "qəbul edilib": "✅",
    "güzəşt variantı qəbul edilib": "🟢",
    "qismən qəbul edilib": "🟡",
    "başqa cür dəyişdirilib": "🔄",
    "rədd edilib": "❌",
    "bənd silinib": "➖",
    "əlavə edilməyib": "❌",
}
CHANGE_LABEL = {"dəyişib": "🔄 Dəyişib", "silinib": "➖ Silinib", "əlavə": "➕ Əlavə olunub"}


def _analyze(
    clauses: dict[str, str], party: str, refresh: bool, focus: list[str] | None = None
) -> verifier.Result:
    raw = analyzer.analyze(clauses, party, refresh=refresh, focus=focus)
    result = verifier.verify(raw, clauses)
    result.checks = checks.run(clauses)
    return result


def render() -> None:
    with st.sidebar:
        old_file = st.file_uploader(
            "Köhnə versiya (bizim yoxladığımız)", type=["docx", "pdf", "txt"]
        )
        new_file = st.file_uploader(
            "Yeni versiya (qarşı tərəfin cavabı)", type=["docx", "pdf", "txt"]
        )
        party = st.radio("Kimin maraqlarını qoruyuruq?", list(analyzer.PARTIES), index=0)
        run = st.button(
            "Müqayisə et", type="primary", disabled=not (old_file and new_file),
            use_container_width=True,
        )  # fmt: skip
        refresh = st.checkbox("Keşi keçmək", key="cmp_refresh")

    st.title("🔀 Versiya müqayisəsi")
    st.caption(
        "Qarşı tərəf müqavilənin yeni versiyasını göndərəndə: nə dəyişdi, təkliflərimizdən "
        "hansılar qəbul edildi, risk necə dəyişdi."
    )

    if run:
        try:
            old_lines = parser.read_lines(old_file.getvalue(), old_file.name)
            new_lines = parser.read_lines(new_file.getvalue(), new_file.name)
            old, new = parser.split_clauses(old_lines), parser.split_clauses(new_lines)
            changes = compare.align(old, new)  # modelsiz — yeni versiyanın təhlilinə fokus verir
            focus = [c.new_key for c in changes if c.status in ("dəyişib", "əlavə")]
            with st.status("Hər iki versiya paralel təhlil olunur (1–3 dəqiqə)...") as status:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    old_job = pool.submit(_analyze, old, party, refresh)
                    new_job = pool.submit(_analyze, new, party, refresh, focus)
                    old_result, new_result = old_job.result(), new_job.result()
                status.update(label="Hazırdır", state="complete")
        except Exception as error:  # noqa: BLE001
            st.error("Müqayisə alınmadı. İnternet bağlantısını və API açarını yoxlayın.")
            if os.getenv("DEBUG"):
                with st.expander("Texniki detal"):
                    st.exception(error)
            st.stop()
        st.session_state.cmp = {
            "party": party,
            "old": (old_file.getvalue(), old_file.name, old_lines, old_result),
            "new": (new_file.getvalue(), new_file.name, new_lines, new_result),
            "changes": changes,
            "proposals": compare.track(old_result.findings, changes),
        }

    state = st.session_state.get("cmp")
    if not state:
        st.info("Soldan köhnə və yeni versiyanı yükləyin və **Müqayisə et** basın.")
        return

    old_data, old_name, old_lines, old_result = state["old"]
    new_data, new_name, new_lines, new_result = state["new"]
    changes, proposals = state["changes"], state["proposals"]
    changed_keys = {c.new_key for c in changes if c.status in ("dəyişib", "əlavə")}
    fresh_risks = [f for f in new_result.findings if f.bend_no in changed_keys]
    before, after = score.score(old_result.findings), score.score(new_result.findings)
    accepted = sum(p.status in ("qəbul edilib", "güzəşt variantı qəbul edilib") for p in proposals)

    cols = st.columns(4)
    cols[0].metric(
        "Risk balı", f"{after.value}/100", delta=after.value - before.value, delta_color="inverse",
        help=f"Köhnə versiya: {before.value}/100",
    )  # fmt: skip
    cols[1].metric("Təkliflərimiz qəbul edilib", f"{accepted}/{len(proposals)}")
    cols[2].metric("Dəyişən bəndlər", sum(c.status != "eyni" for c in changes))
    cols[3].metric("🆕 Yeni risklər", len(fresh_risks))

    b1, b2 = st.columns(2)
    b1.download_button(
        "📥 Müqayisə (Word, track changes)",
        data=compare.redline(redliner.load(old_data, old_name, old_lines), changes),
        file_name=f"{Path(old_name).stem}_müqayisə.docx",
        mime=DOCX_MIME,
        use_container_width=True,
        help="Köhnə versiya üzərində qarşı tərəfin etdiyi bütün dəyişikliklər.",
    )
    b2.download_button(
        "📥 Yeni versiyaya cavab redline-ı",
        data=redliner.redline(
            redliner.load(new_data, new_name, new_lines), new_result, state["party"]
        ),
        file_name=f"{Path(new_name).stem}_düzəliş.docx",
        mime=DOCX_MIME,
        type="primary",
        use_container_width=True,
        help="Danışığın növbəti raundu: yeni versiyadakı risklərə düzəlişlər.",
    )

    st.markdown("### Təkliflərimizin taleyi")
    rows = []
    for p in proposals:
        where = f"Bənd {p.finding.bend_no}" if p.finding.bend_no else "Çatışmayan bənd"
        now = f" → indi {p.new_key}" if p.new_key and p.new_key != p.finding.bend_no else ""
        rows.append(
            f"| {STATUS_ICON.get(p.status, '')} {p.status} | {where}{now} | {p.finding.basliq} |"
        )
    st.markdown("| Status | Bənd | Təklif |\n|---|---|---|\n" + "\n".join(rows))

    if fresh_risks:
        st.markdown("### 🆕 Yeni və ya dəyişmiş bəndlərdə risklər")
        for f in fresh_risks:
            with st.container(border=True):
                st.markdown(f"**Bənd {f.bend_no} — {f.basliq}** · risk: {f.risk}")
                st.markdown(f"_{f.bend_metni}_")
                st.warning(f.izah)
                if f.madde_metni:
                    with st.expander(f"📖 {f.madde_basliq}"):
                        st.text(f.madde_metni)

    st.markdown("### Dəyişikliklər")
    for c in changes:
        if c.status == "eyni":
            continue
        keys = f"{c.old_key} → {c.new_key}" if c.old_key and c.new_key else (c.old_key or c.new_key)
        with st.container(border=True):
            st.markdown(f"**{CHANGE_LABEL[c.status]}** · bənd {keys}")
            if c.status == "dəyişib":
                st.markdown(compare.diff_markdown(c.old_text, c.new_text))
            elif c.status == "silinib":
                st.markdown(f":red[~~{c.old_text}~~]")
            else:
                st.markdown(f":green[{c.new_text}]")
