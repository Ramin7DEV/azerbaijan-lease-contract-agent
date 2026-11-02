"""Streamlit interfeysi: müqavilə yüklə → tərəf seç → sənəd görünüşü / risklər → Word.

İşə salmaq: uv run streamlit run app.py
"""

import dataclasses
import os
import time
from pathlib import Path

import streamlit as st

import compare_page
from agent import (
    analyzer,
    checks,
    compare,
    ics,
    memo,
    parser,
    preview,
    qa,
    redliner,
    score,
    verifier,
)

st.set_page_config(page_title="İcarə müqaviləsi yoxlaması", page_icon="⚖️", layout="wide")

RISK_STYLE = {
    "kritik": ("🔴", "error"),
    "orta": ("🟠", "warning"),
    "aşağı": ("🟡", "info"),
}
TIP_LABEL = {
    "qanuna_zidd": "Qanuna zidd",
    "birterefli": "Birtərəfli şərt",
    "catismayan": "Çatışmayan bənd",
}
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

with st.sidebar:
    mode = st.radio(
        "Rejim", ["🔍 Müqavilə yoxlaması", "🔀 Versiya müqayisəsi"], label_visibility="collapsed"
    )
    st.divider()
if mode == "🔀 Versiya müqayisəsi":
    compare_page.render()
    st.stop()

st.title("⚖️ İcarə müqaviləsi yoxlaması")
st.caption(
    "Mülki Məcəllənin 33–34-cü fəsilləri əsasında · Gemma 4 31B · "
    "hər istinad qanun bazası ilə yoxlanılır"
)

with st.sidebar:
    source = st.radio("Müqavilə", ["Fayl yüklə", "Mətni yapışdır"], horizontal=True)
    if source == "Fayl yüklə":
        upload = st.file_uploader("DOCX, PDF və ya TXT", type=["docx", "pdf", "txt"])
        filename, ready = (upload.name if upload else ""), upload is not None
    else:
        text = st.text_area("Müqavilənin mətni", height=300, placeholder="1.1. İcarəyə verən ...")
        filename, ready = "yapışdırılmış mətn", bool(text.strip())
    party = st.radio("Kimin maraqlarını qoruyuruq?", list(analyzer.PARTIES), index=0)
    run = st.button("Yoxla", type="primary", disabled=not ready, use_container_width=True)
    refresh = st.checkbox(
        "Keşi keçmək", help="Eyni müqavilə əvvəl yoxlanılıbsa, nəticə dərhal keşdən gəlir."
    )

if run:
    try:
        if source == "Fayl yüklə":
            data, lines = upload.getvalue(), parser.read_lines(upload.getvalue(), upload.name)
        else:
            data, lines = None, [l.strip() for l in text.splitlines() if l.strip()]
        clauses = parser.split_clauses(lines)
        cached = analyzer.cache_path(clauses, party).exists() and not refresh
        started = time.time()
        label = (
            "Nəticə keşdən oxunur..." if cached else "Model müqaviləni təhlil edir (1–2 dəqiqə)..."
        )
        with st.status(f"{len(clauses)} bənd tapıldı. {label}") as status:
            raw = analyzer.analyze(clauses, party, refresh=refresh)
            status.update(label="Verifier istinadları qanun bazası ilə yoxlayır...")
            result = verifier.verify(raw, clauses)
            result.checks = checks.run(clauses)  # modelsiz texniki yoxlamalar
            took = "keşdən" if cached else f"{time.time() - started:.0f} san"
            status.update(label=f"Hazırdır · {took}", state="complete")
    except Exception as error:  # noqa: BLE001 — istifadəçiyə anlaşılan mesaj, detal aşağıda
        st.error(
            "Təhlil alınmadı. İnternet bağlantısını və `.env`-dəki API açarını yoxlayın, "
            "sonra yenidən **Yoxla** basın."
        )
        if os.getenv("DEBUG"):
            with st.expander("Texniki detal"):
                st.exception(error)
        st.stop()
    st.session_state.update(
        result=result,
        filename=filename,
        party=party,
        source=(data, filename, lines),
        clauses=clauses,
        run_id=int(time.time() * 1000),  # yeni təhlildə kartların seçimləri sıfırlansın
    )

result: verifier.Result | None = st.session_state.get("result")
if not result:
    st.info("Soldan müqaviləni yükləyin, tərəfi seçin və **Yoxla** düyməsini basın.")
    st.stop()

run_id = st.session_state.run_id


def use_key(i: int) -> str:
    return f"use_{run_id}_{i}"


def text_key(i: int) -> str:
    return f"text_{run_id}_{i}"


def set_use(i: int, value: bool) -> None:
    st.session_state[use_key(i)] = value


def reset_text(i: int, text: str) -> None:
    st.session_state[text_key(i)] = text


def use_compromise(i: int, text: str) -> None:
    st.session_state[text_key(i)] = text
    st.session_state[use_key(i)] = True


def select_all(value: bool) -> None:
    for i in range(len(result.findings)):
        st.session_state[use_key(i)] = value


# Kartların başlanğıc vəziyyəti: hamısı seçilib, mətn modelin təklifidir
for i, f in enumerate(result.findings):
    st.session_state.setdefault(use_key(i), True)
    st.session_state.setdefault(text_key(i), f.teklif)

# Vəkilin seçdiyi və redaktə etdiyi düzəlişlər — Word faylı yalnız bunlardan qurulur
selected = [
    dataclasses.replace(f, teklif=st.session_state[text_key(i)])
    for i, f in enumerate(result.findings)
    if st.session_state[use_key(i)]
]
chosen = dataclasses.replace(result, findings=selected)

# --- xülasə ---
risk = score.score(result.findings)
left, right = st.columns([1, 2])
left.markdown(f"### Risk balı: :{risk.color}[{risk.value}/100]")
left.markdown(f"**:{risk.color}[{risk.level}]** · tərəf: {st.session_state.party}")
right.progress(risk.value / 100)
right.caption(
    "Bal kodla hesablanır, model rəqəm vermir: hər kritik tapıntı 20, orta 8, aşağı 3 xal. "
    "Xal artdıqca bal 100-ə yaxınlaşır. 0–24 aşağı, 25–49 orta, 50–74 yüksək, 75+ çox yüksək risk."
)

counts = {r: sum(f.risk == r for f in result.findings) for r in verifier.RISKS}
cols = st.columns(5)
cols[0].metric("Əmlak növü", result.emlak_novu)
cols[1].metric("🔴 Kritik", counts["kritik"])
cols[2].metric("🟠 Orta", counts["orta"])
cols[3].metric("🟡 Aşağı", counts["aşağı"])
cols[4].metric(
    "🛡️ Verifier",
    f"{len(result.rejected)} atdı · {sum(bool(f.qeyd) for f in result.findings)} düzəltdi",
)
st.caption(st.session_state.filename)

# --- müqavilə kartı ---
summary = result.summary
if summary.fields:
    with st.container(border=True):
        st.markdown("**🗂️ Müqavilə kartı**")
        halves = st.columns(2)
        for i, item in enumerate(summary.fields):
            source = f" · bənd {item.bend_no}" if item.bend_no else ""
            mark = "" if item.yoxlanildi else " ⚠️"
            halves[i % 2].markdown(
                f"**{item.label}:** {item.deyer}{mark}  \n:gray[{source.strip(' ·')}]"
            )
        if any(not item.yoxlanildi for item in summary.fields):
            st.caption("⚠️ — rəqəm mənbə bənddə tapılmadı, əllə yoxlayın.")
        calendar = ics.build(result, Path(st.session_state.filename).stem)
        if calendar:
            names = [e[1] for e in ics.events(result)]
            st.download_button(
                "📅 Açar tarixləri təqvimə əlavə et (.ics)",
                data=calendar,
                file_name=f"{Path(st.session_state.filename).stem}_tarixlər.ics",
                mime="text/calendar",
                help="Telefon, Outlook və Google Calendar açır: " + "; ".join(names),
            )

if result.checks:
    with st.expander(
        f"🔎 Texniki yoxlama: {len(result.checks)} qeyd (kodla, modelsiz)", expanded=True
    ):
        for c in result.checks:
            st.markdown(f"- **Bənd {c.bend_no} — {c.basliq}.** {c.izah}")

if result.checklist:
    present = sum(item.var for item in result.checklist)
    with st.expander(f"📋 Yoxlama siyahısı: {present}/{len(result.checklist)} mövzu var"):
        halves = st.columns(2)
        for i, item in enumerate(result.checklist):
            where = f" — bənd {item.bend_no}" if item.var and item.bend_no else ""
            halves[i % 2].markdown(f"{'✅' if item.var else '❌'} {item.movzu}{where}")

# --- Tablar ---
tab_sened, tab_riskler, tab_sual = st.tabs(
    [
        "📄 Müqavilə və düzəlişlər",
        "⚠️ Risklərin təfərrüatı",
        "💬 Sual-cavab",
    ]
)

# --- Tab 1: Sənəd görünüşü ---
with tab_sened:
    accepted = sum(st.session_state[use_key(i)] for i in range(len(result.findings)))
    with st.container(border=True):
        col_info, col_btn1, col_btn2 = st.columns([5, 1.5, 1.5])
        col_info.markdown(
            f"**✅ {accepted}/{len(result.findings)} düzəliş qəbul edilib**  \n"
            "Hər düzəlişin yanındaki düymələrlə qəbul edin, ləğv edin və ya mətnini dəyişin. "
            "Word faylına yalnız qəbul edilənlər düşür."
        )
        col_btn1.button(
            "Hamısını qəbul et",
            on_click=select_all,
            args=(True,),
            key=f"all_on_{run_id}",
            use_container_width=True,
        )
        col_btn2.button(
            "Hamısını ləğv et",
            on_click=select_all,
            args=(False,),
            key=f"all_off_{run_id}",
            use_container_width=True,
        )

    document = preview.rows(st.session_state.clauses, result.findings)
    for row in document:
        if row.kind == "metn":
            st.markdown(row.text)
        elif row.kind == "basliq":
            st.markdown(f"##### {row.key}. {row.text}")
        elif row.kind == "bend" and row.finding is None:
            st.caption(f"**{row.key}.** {row.text}")
        elif row.kind == "bend" and row.finding is not None:
            i = row.finding
            f = result.findings[i]
            use = st.session_state[use_key(i)]
            current = st.session_state[text_key(i)]
            icon = RISK_STYLE[f.risk][0]
            madde_part = f" · Maddə {f.madde_no}" if f.madde_no else ""

            with st.container(border=True):
                # a) Başlıq sətri
                c_head, c_action = st.columns([5, 2])
                c_head.markdown(f"**{row.key}.** {icon} {f.basliq}")
                c_head.caption(f"{TIP_LABEL[f.tip]} · risk: {f.risk}{madde_part}")
                if use:
                    c_action.markdown(":green[**✅ Qəbul edilib**]")
                    c_action.button(
                        "↩︎ Ləğv et",
                        key=f"off_{run_id}_{i}",
                        on_click=set_use,
                        args=(i, False),
                        use_container_width=True,
                    )
                else:
                    c_action.markdown(":gray[**↩︎ Ləğv edilib**]")
                    c_action.button(
                        "✅ Qəbul et",
                        key=f"on_{run_id}_{i}",
                        on_click=set_use,
                        args=(i, True),
                        use_container_width=True,
                    )

                # b) Mətn
                if use and current:
                    st.markdown(compare.diff_markdown(row.text, current))
                elif use and not current:
                    st.markdown(compare.diff_markdown(row.text, ""))
                    st.caption("Bənd müqavilədən tamamilə çıxarılır.")
                else:
                    st.markdown(row.text)
                    st.caption("Düzəliş ləğv edildi — bənd olduğu kimi qalır.")

                # c) Niyə
                st.caption(f.izah)

                # d) Redaktə
                with st.expander("✏️ Mətni özüm yazım"):
                    st.text_area(
                        "Bəndin yeni mətni",
                        key=text_key(i),
                        height=120,
                        disabled=not use,
                        placeholder="Boş saxlasanız, bənd müqavilədən silinəcək.",
                    )
                    if current != f.teklif:
                        st.button(
                            "İlkin təklifə qaytar",
                            key=f"rst_{run_id}_{i}",
                            on_click=reset_text,
                            args=(i, f.teklif),
                        )

                # e) Digər qeydlər
                if row.notes:
                    for j in row.notes:
                        note_f = result.findings[j]
                        st.caption(f"ℹ️ Bu bəndə aid digər qeyd: {note_f.basliq} — {note_f.izah}")

                # f) Texniki qeydlər
                if result.checks:
                    for c in result.checks:
                        if c.bend_no == row.key:
                            st.caption(f"🔎 {c.basliq}: {c.izah}")

        elif row.kind == "elave":
            i = row.finding
            f = result.findings[i]
            use = st.session_state[use_key(i)]
            current = st.session_state[text_key(i)]
            madde_part = f" · Maddə {f.madde_no}" if f.madde_no else ""

            with st.container(border=True):
                # Başlıq sətri
                c_head, c_action = st.columns([5, 2])
                c_head.markdown(f"**➕ Əlavə ediləcək bənd** — {f.basliq}")
                c_head.caption(f"{TIP_LABEL[f.tip]} · risk: {f.risk}{madde_part}")
                if use:
                    c_action.markdown(":green[**✅ Qəbul edilib**]")
                    c_action.button(
                        "↩︎ Ləğv et",
                        key=f"off_{run_id}_{i}",
                        on_click=set_use,
                        args=(i, False),
                        use_container_width=True,
                    )
                else:
                    c_action.markdown(":gray[**↩︎ Ləğv edilib**]")
                    c_action.button(
                        "✅ Qəbul et",
                        key=f"on_{run_id}_{i}",
                        on_click=set_use,
                        args=(i, True),
                        use_container_width=True,
                    )

                # Mətn
                if use:
                    st.markdown(compare.diff_markdown("", current))
                else:
                    st.caption("Bu bənd əlavə edilməyəcək.")

                # Niyə
                st.caption(f.izah)

                # Redaktə
                with st.expander("✏️ Mətni özüm yazım"):
                    st.text_area(
                        "Bəndin yeni mətni",
                        key=text_key(i),
                        height=120,
                        disabled=not use,
                    )
                    if current != f.teklif:
                        st.button(
                            "İlkin təklifə qaytar",
                            key=f"rst_{run_id}_{i}",
                            on_click=reset_text,
                            args=(i, f.teklif),
                        )

    # 4.3. Sonda — təsdiq və ixrac
    st.divider()
    st.markdown("### ✅ Təsdiq və ixrac")
    st.caption(f"Word faylına {accepted} düzəliş düşəcək.")
    data, filename, lines = st.session_state.source
    stem = Path(filename).stem
    b1, b2, b3 = st.columns(3)
    b1.download_button(
        "📥 Track changes + şərhlər",
        data=redliner.redline(redliner.load(data, filename, lines), chosen, st.session_state.party),
        file_name=f"{stem}_düzəliş.docx",
        mime=DOCX_MIME,
        type="primary",
        use_container_width=True,
        help="Word-da Review → Track Changes: hər düzəlişi qəbul və ya rədd edin.",
    )
    b2.download_button(
        "📄 Təmiz versiya",
        data=redliner.redline(
            redliner.load(data, filename, lines), chosen, st.session_state.party, clean=True
        ),
        file_name=f"{stem}_təmiz.docx",
        mime=DOCX_MIME,
        use_container_width=True,
        help="Bütün seçilmiş düzəlişlər qəbul edilmiş, şərhsiz mətn — göndərməyə hazır.",
    )
    b3.download_button(
        "📝 Müştəri üçün hüquqi rəy",
        data=memo.build(
            chosen, st.session_state.party, filename, total_findings=len(result.findings)
        ),
        file_name=f"{stem}_hüquqi_rəy.docx",
        mime=DOCX_MIME,
        use_container_width=True,
        help="Müştəriyə: nəticə, əsas şərtlər, risklər, qanun mətni, tövsiyə və danışıq strategiyası.",
    )

# --- Tab 2: Risklərin təfərrüatı ---
with tab_riskler:
    for i, f in enumerate(result.findings):
        icon, box = RISK_STYLE[f.risk]
        where = f"Bənd {f.bend_no}" if f.bend_no else "Müqavilədə yoxdur"
        with st.container(border=True):
            head, toggle = st.columns([5, 1])
            head.markdown(f"#### {icon} {where} — {f.basliq}")
            head.caption(f"{TIP_LABEL[f.tip]} · risk: {f.risk}")
            toggle.toggle("Word-a daxil et", key=use_key(i))
            if f.bend_metni:
                st.markdown(f"**Müqavilədə:** {f.bend_metni}")
            getattr(st, box)(f.izah)
            if f.qeyd:
                st.caption(f"🛡️ Verifier düzəltdi: {f.qeyd}")
            if f.madde_metni:
                ref = f" — {f.madde_no}" if "." in (f.madde_no or "") else ""
                with st.expander(f"📖 {f.madde_basliq}{ref}"):
                    st.text(f.madde_metni)
            else:
                st.caption("Qanunda birbaşa maddə yoxdur — praktik tövsiyə.")

            current = st.session_state[text_key(i)]
            if current:
                st.markdown("**Təklif olunan mətn:**")
                st.success(current)
            elif f.bend_no:
                st.markdown("**Təklif:** bənd müqavilədən tamamilə çıxarılmalıdır.")
            st.caption("Mətni redaktə etmək üçün «📄 Müqavilə və düzəlişlər» tabına keçin.")

            if f.arqument or f.guzest:
                with st.expander(
                    "🤝 Danışıq: arqument və güzəşt variantı (yalnız sizin üçün, Word-a düşmür)"
                ):
                    if f.arqument:
                        st.markdown(f"**Qarşı tərəfə arqument:** {f.arqument}")
                    if f.guzest:
                        st.markdown(
                            f"**Güzəşt variantı** (ideal təklif qəbul olunmasa):\n\n> {f.guzest}"
                        )
                        st.button(
                            "Güzəşt variantını Word-a yaz",
                            key=f"compromise_{run_id}_{i}",
                            on_click=use_compromise,
                            args=(i, f.guzest),
                        )

    if result.rejected:
        with st.expander(
            f"🛡️ Verifier {len(result.rejected)} tapıntını atdı "
            "(uydurma və ya yoxlanıla bilməyən istinad)"
        ):
            for item, reason in result.rejected:
                title = item.get("basliq", "?") if isinstance(item, dict) else item
                st.markdown(f"- **{title}** — {reason}")

# --- Tab 3: Sual-cavab ---
with tab_sual:
    st.caption(
        "Cavab yalnız bu müqaviləyə və Mülki Məcəllənin 33–34-cü fəsillərinə əsaslanır; "
        "bənd və maddə istinadları Verifier-dən keçir."
    )
    history_key = f"qa_{run_id}"
    history: list[qa.Answer] = st.session_state.setdefault(history_key, [])
    question = None
    examples = st.columns(len(qa.EXAMPLES))
    for col, example in zip(examples, qa.EXAMPLES, strict=True):
        if col.button(example, use_container_width=True):
            question = example
    question = st.chat_input("Müqavilə barədə sual verin...") or question

    if question:
        with st.spinner("Cavab hazırlanır..."):
            try:
                history.append(qa.ask(question, st.session_state.clauses, st.session_state.party))
            except Exception as error:  # noqa: BLE001
                st.error("Cavab alınmadı. Bir az sonra yenidən cəhd edin.")
                if os.getenv("DEBUG"):
                    st.exception(error)

    for answer in reversed(history):
        with st.chat_message("user"):
            st.markdown(answer.sual)
        with st.chat_message("assistant", avatar="⚖️"):
            st.markdown(answer.cavab)
            for no, txt in answer.bendler:
                with st.expander(f"📄 Müqavilə, bənd {no}"):
                    st.text(txt)
            for no, title, txt in answer.maddeler:
                ref = f" — {no}" if "." in no else ""
                with st.expander(f"📖 {title}{ref}"):
                    st.text(txt)
            if answer.atildi:
                st.caption("🛡️ Verifier təsdiqləmədi: " + ", ".join(answer.atildi))
