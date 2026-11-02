# BUILD.md — layihəni sıfırdan qurmaq üçün texniki spesifikasiya

> **Kimə:** Claude Code (və ya başqa AI kod agenti). Bu faylı oxu və layihəni **bölmə 9-dakı ardıcıllıqla** qur.
> Hər mərhələnin sonunda onun qəbul testini işə sal; keçmədən növbətiyə keçmə.
> **Dil:** interfeys, nəticələr və kod şərhləri Azərbaycan dilində.

---

## 0. Başlamazdan əvvəl

Layihənin **data faylları** (kod deyil, məlumatdır):

| Fayl | Nə |
|---|---|
| `data/law/mulki_mecelle.docx` | e-qanun.az-dan bütöv Mülki Məcəllə (repoda yoxdur, özünüz endirin) |
| `data/law/icare.txt` | 33–34-cü fəsillər (ehtiyat: extract skripti işləməsə) |
| `prompts/system.md` | agentin rolu, qaydaları, JSON formatı |
| `prompts/checklist.md` | yoxlama siyahısı + imperativ/dispozitiv norma cədvəlləri |
| `data/contracts/*` | test müqavilələri + `*_gozlenilen.md` |
| `tests/fixtures/*.json` | modelin saxlanmış cavabları (API-siz testlər üçün) |

Kompüterdə: Python 3.12+, [uv](https://docs.astral.sh/uv/), OpenRouter açarı.

```bash
uv init --name muqavile-agent && uv add openai pypdf python-docx python-dotenv streamlit && uv add --dev ruff pytest
```

`.env` (heç vaxt commit olunmur; `.gitignore`-a `.env`, `.venv/`, `__pycache__/`, `.cache/`, `output/` yaz):

```
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-...
LLM_MODEL=google/gemma-4-31b-it
```

Repoya yalnız `.env.example` (açarsız) düşür. `pyproject.toml`-a əlavə et:

```toml
[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

---

## 1. Məhsul

Vəkil Azərbaycan icarə müqaviləsini (DOCX / PDF / yapışdırılmış mətn) yükləyir, kimin maraqlarını qoruduğunu seçir (icarəçi / icarəyə verən / neytral). ~1 dəqiqədən sonra görür:

1. **Risk balı 0–100** və əmlak növü (yaşayış / qeyri-yaşayış).
2. **Risk kartları:** bəndin mətni, problem, Mülki Məcəllənin orijinal mətni, düzəliş təklifi.
3. **Yoxlama siyahısı:** 11 vacib mövzu ✅/❌.
4. Hər kartda **"Word-a daxil et"** açarı və **redaktə olunan** təklif.
5. **İki Word faylı:** track changes + şərhlər; təmiz versiya (düzəlişlər qəbul edilmiş).

Arxitektura: `Parser → Analyzer (Gemma, 1 sorğu) → Verifier → Score / Redliner → Streamlit`.

---

## 2. Qəti qaydalar (pozulmamalıdır)

1. **Model düşünür, kod yoxlayır.** Model yalnız maddə **nömrəsi** və bənd **nömrəsi** verir. Maddənin mətni `data/law/icare.txt`-dən, bəndin mətni parser-dən götürülür. Bazada olmayan maddəyə və ya müqavilədə olmayan bəndə istinad edən tapıntı **atılır** və UI-da "Verifier atdı" kimi göstərilir.
2. **"Qanuna zidd" yalnız imperativ normaya görə.** Norma `IMPERATIVE` cədvəlində yoxdursa və ya yalnız yaşayışa aiddirsə, əmlak isə qeyri-yaşayışdırsa — Verifier tapıntını `birterefli`-yə endirir və `qeyd` yazır.
3. **Risk balını kod hesablayır**, model yox.
4. **Word-da heç nə izsiz dəyişmir.** "Reject All" orijinalı hərf-hərf qaytarmalıdır. Bənd nömrəsi, böyük hərfli başlıqlar və imzalar toxunulmaz.
5. API açarı yalnız `.env`-də. Repo açıqdır.
6. Yalnız icarə müqavilələri.

---

## 3. Qovluq strukturu

```
agent/
  __init__.py
  llm.py          # OpenAI-uyğun klient
  law.py          # qanun bazası + IMPERATIVE
  numbering.py    # Word avtomatik nömrələməsi + görünən mətn
  parser.py       # müqavilə → bəndlər
  analyzer.py     # prompt + model + keş
  verifier.py     # yoxlama, Finding / Result
  score.py        # risk balı
  redliner.py     # track changes DOCX
  checks.py       # modelsiz texniki yoxlamalar
  ics.py          # açar tarixlər → təqvim (.ics)
  qa.py           # müqavilə ilə sual-cavab
  memo.py         # müştəri üçün hüquqi rəy (Word)
  compare.py      # versiya müqayisəsi
compare_page.py   # Streamlit: müqayisə rejimi
app.py            # Streamlit
scripts/
  extract_law.py  # mulki_mecelle.docx → icare.txt
  review.py       # terminalda test, DOCX → output/
  make_autonumbered.py  # test üçün avtomatik nömrəli DOCX
tests/
  test_pipeline.py
  fixtures/*.json
.streamlit/config.toml   # [server] headless = true ; [browser] gatherUsageStats = false
```

---

## 4. Məlumat formatları

### 4.1 Bəndlər (parser çıxışı)
`dict[str, str]`, sıra saxlanılır: `{"Başlıq": "...", "1": "MÜQAVİLƏNİN PREDMETİ", "1.1": "İcarəyə verən ...", ...}`
- Açar = bənd nömrəsi (nöqtəsiz sonluq): `"3.3"`. Təkrar nömrə → `"3.3'"`.
- Birinci nömrəli bənddən əvvəlki sətirlər → `"Başlıq"`.
- Nömrəli sətir 3-dən azdırsa: hər sətir `"P1"`, `"P2"`...
- Dəyər = nömrəsiz mətn; nömrəsiz davam sətirləri `\n` ilə birləşir.

### 4.2 Modelin JSON-u (`prompts/system.md`-də təsvir olunub)
```json
{
  "emlak_novu": "yaşayış | qeyri-yaşayış | müəyyən deyil",
  "siyahi": [{"movzu": "Fors-major", "var": false, "bend_no": null}],
  "tapintilar": [{
    "tip": "qanuna_zidd | birterefli | catismayan",
    "bend_no": "3.3", "risk": "kritik | orta | aşağı",
    "basliq": "...", "madde_no": "688.2", "izah": "...",
    "teklif": "bəndin yeni tam mətni; boş sətir = bəndi sil"
  }]
}
```

---

## 5. Modullar (spesifikasiya)

### 5.1 `agent/llm.py`
- `load_dotenv()`; `client = OpenAI(base_url=env LLM_BASE_URL, api_key=env LLM_API_KEY, timeout=300, max_retries=3)`; `MODEL = env LLM_MODEL`.
- `ask(system, user, json_mode=False) -> str`: `temperature=0`, `response_format={"type":"json_object"}` əgər json_mode. Boş cavabda `ValueError`.
- **Gemma cavabdan əvvəl `<thought>...</thought>` yazır** (söndürmək olmur): `text.split("</thought>")[-1].strip()`.

### 5.2 `agent/law.py`
- `load() -> dict[str, Article]` (`@cache`). `icare.txt` sətir-sətir: `^Maddə (\d+)\.\s*(.*)` yeni maddə başladır; `^\d+-(ci|cı|cu|cü) fəsil\.` və `^§ \d` sətirləri atılır. `Article(number, title, lines: tuple[str])`. **48 maddə, 675–722.**
- `Article.point(ref)`: `ref == number` → bütün mətn. Əks halda sətir `^{ref}\.?\s` ilə başlayan bənd + onun alt bəndləri (`^{ref}\.\d`). Tapılmasa `None`. (Diqqət: mətndə `685.2.2 ikidən` kimi nöqtəsiz nömrə var.)
- `lookup(ref) -> (Article, text) | None`: ref-dən rəqəm və nöqtədən başqa hər şeyi sil (`"Maddə 688.2"` → `"688.2"`).
- `full_text()` — modelə verilən tam mətn.
- `IMPERATIVE` (açar → `"hamı"` / `"yaşayış"`), `checklist.md` B cədvəli ilə **eyni** olmalıdır:
  - hamı: `677.4`, `686`, `691.3`, `695`
  - yaşayış: `677.1.1`, `677.1.4`, `678`, `681`, `683.2`, `687`, `688`, `692`, `693`, `696`
- `is_imperative(ref, property_type) -> bool`: `ref == key` və ya `ref.startswith(key+".")` və ya `key.startswith(ref+".")`; scope `hamı` və ya property_type `yaşayış`. "müəyyən deyil" → yalnız `hamı`.

### 5.3 `agent/numbering.py` — Word avtomatik nömrələməsi
Real müqavilələrin çoxunda "3.3." mətndə yazılmır, Word onu `numbering.xml`-dən çəkir; `p.text` onu göstərmir.
- `Numbering(document)`: `document.part.numbering_part.element`-dən (yoxdursa `KeyError`/`NotImplementedError` → boş):
  - `abstractNum` → `{ilvl: (start, numFmt, lvlText)}`
  - `num` → `(abstractNumId, {ilvl: startOverride})`
- `label(paragraph) -> str`: `numPr` abzasın `pPr`-ından; yoxdursa `pStyle` üslubundan (və onun `basedOn` zəncirindən). `numId == "0"` → nömrə yoxdur.
  - Sayğaclar **abstractNumId** üzrə (9 səviyyə). `num` ilk dəfə görünəndə `startOverride` tətbiq et.
  - `counters[ilvl] = counters[ilvl]+1 if counters[ilvl] else start`; daha dərin səviyyələri 0-a sıfırla.
  - `bullet`/`none` → `""`. `lvlText`-də `%1..%9`-u formatlanmış sayğacla əvəz et (`decimal`, `lowerLetter`, `upperLetter`, `lowerRoman`, `upperRoman`).
  - **Bütün abzaslar üçün çağır** (boşlar da sayğacı artırır), sənəd sırası ilə.
- `visible_text(p)`: `p._p.iter(w:t, w:tab, w:br, w:cr)`, yalnız valideyni `w:r` olanlar (pPr/tabs/tab — mətn deyil). `w:ins` içindəki mətn daxil (python-docx `p.text` onu görmür), `w:delText` avtomatik xaric.
- `paragraph_lines(document) -> list[(Paragraph, "3.3. mətn")]`: boş olmayan abzaslar, avtomatik nömrə önə əlavə olunur. **Parser və Redliner eyni funksiyanı işlədir.**

### 5.4 `agent/parser.py`
- `CLAUSE = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){0,3})[.)]?\s+(\S.*)$")`
- `read_lines(data, filename)`: PDF → `pypdf` sətirləri; DOCX → `paragraph_lines` + hər cədvəl sətri `" | ".join(unikal xana mətnləri)`. Boş sətirlər atılır.
- `clause_spans(lines) -> dict[key, list[int]]` (4.1 qaydaları), `split_clauses(lines)` onun üstündə: rəqəmlə başlayan açarda birinci sətrin nömrəsi kəsilir.
- `parse(data, filename)`, `parse_text(text)`, `as_prompt(clauses)` → `"[3.3] mətn"` sətirləri.

### 5.5 `agent/analyzer.py`
- `PARTIES = {"icarəçi": "Sən icarəçinin (kirayəçinin) vəkilisən...", "icarəyə verən": ..., "neytral": ...}`
- `system_prompt()` = `system.md` + `"# Yoxlama siyahısı"` + `checklist.md` + `"# Mülki Məcəllə: 33-cü və 34-cü fəsillər"` + qanun. **Sabit hissə system mesajında, müqavilə user mesajında** (keş üçün).
- `user_prompt(clauses, party)` = `PARTIES[party]` + `"# Müqavilə"` + `as_prompt`.
- `parse_json(text)`: ```` ```json ```` çərçivələrini sil, ilk `{`-dən son `}`-a qədər `json.loads`.
- `cache_path(clauses, party)` = `.cache/analysis/{sha256(MODEL + system + user)[:24]}.json`.
- `analyze(clauses, party, refresh=False)`: keşdə varsa oradan; yoxsa `ask(json_mode=True)`. `ValueError`-da (JSONDecodeError daxil) **bir dəfə** təkrar, user-ə "VACİB: cavab yalnız etibarlı JSON olmalıdır" əlavə edib. Uğurlu cavabı keşə yaz.

### 5.6 `agent/verifier.py`
- `Finding(tip, risk, basliq, izah, teklif, bend_no=None, bend_metni=None, madde_no=None, madde_basliq=None, madde_metni=None, qeyd=None)`
- `ChecklistItem(movzu, var, bend_no=None)`; `Result(emlak_novu, findings=[], checklist=[], rejected=[(raw, səbəb)])`
- `check(raw, clauses, emlak_novu) -> Finding | str(səbəb)`:
  1. `tip` ∉ {qanuna_zidd, birterefli, catismayan} → atılır.
  2. `catismayan` deyilsə: `bend_no` (`"[]"` və boşluqlar təmizlənir) boşdursa və ya `clauses`-da yoxdursa → atılır.
  3. `risk` ∉ {kritik, orta, aşağı} → `"orta"`. `bend_metni = clauses[bend_no]`.
  4. `madde_no` (`"Maddə"` prefiksi silinir): varsa `law.lookup` → yoxdursa **"Maddə X bazada yoxdur (uydurma istinad)"**; varsa `madde_basliq = "Maddə N. başlıq"`, `madde_metni` bazadan. Yoxdursa və tip `qanuna_zidd`-dirsə → atılır.
  5. `qanuna_zidd` və `not is_imperative(madde_no, emlak_novu)` → `tip = "birterefli"`, `qeyd = "Maddə X {növ} əmlak üçün məcburi norma deyil..."`.
- `verify(raw, clauses)`: findings `kritik → orta → aşağı` sırası ilə; `siyahi` → ChecklistItem (bend_no clauses-da yoxdursa None).

### 5.6a Müqavilə kartı və danışıq mövqeləri (eyni sorğuda)
- Model JSON-una `xulase` (bax `prompts/system.md`) və hər tapıntıya `guzest` (kompromis bənd mətni) + `arqument` (qarşı tərəfə 1–2 cümlə) əlavə olunur. Çıxış ~2× uzanır (~115 san tək sorğu).
- `Finding`-ə `guzest`, `arqument`. `Result`-a `summary: Summary`, `checks: list`.
- `verify_summary(raw, clauses)`: sahələr `SUMMARY_LABELS` sırası ilə; `bend_no` `"3.1, 3.2"` ola bilər (`,` / `;` / `və` ilə böl, mövcud olanları saxla); `yoxlanildi` = dəyərdəki **bütün rəqəmlər müqavilənin mətnində var** (minlik ayırıcılar təmizlənir) — yoxdursa UI ⚠ göstərir. Tarix (`YYYY-MM-DD`) yalnız **ili müqavilədə yazılıbsa** qəbul olunur (model müddətdən tarix hesablamasın). `odenis_gunu` 1–31.
- **Güzəşt və arqument Word faylına düşmür** (daxili strategiya) — yalnız UI-da; "Güzəşt variantını Word-a yaz" düyməsi text_area-nı güzəştlə əvəz edir.

### 5.6b `agent/checks.py` — modelsiz texniki yoxlamalar
`Check(bend_no, basliq, izah)`; `run(clauses)`:
- **rəqəm-söz**: `(\d[\d\s.,]*\d|\d)\s*\(([^()\d]{2,60})\)`; `words_to_number` (bir…doxsan, yüz, min, milyon; manat/qəpik/faiz/gün/ay/il atlanır; tanınmayan söz → None, yoxlama keçilir).
- **istinad**: `(\d{1,2}(?:\.\d{1,2}){1,3})-?(ci|cı|cu|cü)?\s+bənd` — bənd müqavilədə yoxdursa.
- **tərəf adı**: `bundan sonra "X"` ilə müəyyən edilən ad; eyni qrupdan (İcarəçi / Kirayəçi / İcarəyə götürən...; İcarəyə verən / Kirayəyə verən / Mülkiyyətçi...) başqa ad işlənirsə.
- **tarix**: Azərbaycan ay adları; mövcud olmayan gün; `X tarixdən ... Y tarixədək`-də Y ≤ X.
- Test müqavilələrində **sıfır** saxta xəbərdarlıq olmalıdır. Redliner onları yalnız **şərh** kimi yazır ("Texniki yoxlama — ..."), mətnə toxunmur.

### 5.6c `agent/ics.py`
`events(result)`: bitmə tarixi; yaşayış və müddət > 366 gün → bitmədən 2 ay əvvəl "uzatma tələbinin son günü" (693.1.2), əks halda 30 gün əvvəl xəbərdarlıq; `odenis_gunu` + başlanğıc → `RRULE:FREQ=MONTHLY;BYMONTHDAY=min(gün,28);UNTIL=bitmə`. `build()` — CRLF, `VALUE=DATE`, `VALARM -P1D`, `;` `,` `\` escape.

### 5.6d `agent/qa.py` + `prompts/qa.md`
- `analyzer.ask_json(system, user, refresh)` — ümumi keş + JSON təkrarı (analyze da onu işlədir).
- System = `qa.md` + checklist + qanun + **müqavilə** (hər sual üçün eyni); user = tərəf + sual. JSON: `{"cavab", "bendler", "maddeler"}`.
- Yoxlama: `bendler` müqavilədə, `maddeler` + **cavab mətnində adı çəkilən** maddələr (`Maddə 687`, `691.3-cü maddə`) `law.lookup`-dan keçir; keçməyənlər `atildi` — UI-da "Verifier təsdiqləmədi".
- `qa.md` qaydaları: yalnız müqavilə + 33–34-cü fəsillər; bilinmirsə "yoxdur" de; **müddətli / müddətsiz** fərqi (691 müddətsizə; müddətlidən çıxış 677.1.4, 683.1, 685, 686, razılıq); qısa cavab sualın formasına uyğun və əsaslandırma ilə ziddiyyətsiz.
- UI: 4 nümunə sual düyməsi + `st.chat_input`; tarixçə `qa_{run_id}`; hər cavabda bənd və maddə expander-ləri. ~5–20 san.

### 5.6e Rus və ingilis dilli müqavilələr
- `parser.detect_language(clauses)`: kiril hərfləri > 30% → `ru`; Azərbaycan hərfləri (ə ğ ı ö ü ş ç) > 1% → `az`; əks halda `en`. `Result.dil`.
- `analyzer.user_prompt`: dil `az` deyilsə `LANGUAGE_NOTE` əlavə olunur — `teklif`, `guzest`, `xulase` müqavilənin dilində; `basliq`, `izah`, `arqument` Azərbaycan dilində; rol xəritəsi (Арендодатель / Landlord = icarəyə verən...). **Azərbaycan dilli müqavilələrin prompt-u (və keşi) dəyişmir.**
- `checks.run` yalnız `az` üçün (rəqəm sözləri, ay adları, "bundan sonra" — dilə xasdır). Redliner-də əlavə bəndin başlığı: "Дополнительный пункт" / "Additional clause".
- `evaluate.py`: "Dil" metriki — `teklif` və `guzest`-in `detect_language`-i müqavilənin dili ilə eynidirmi.

### 5.6f `agent/memo.py` — müştəri üçün hüquqi rəy
Əlavə model sorğusu **yoxdur**, mövcud `Result`-dan qurulur, yalnız vəkilin seçdiyi / redaktə etdiyi tapıntılarla. Bölmələr: başlıq ("HÜQUQİ RƏY") + meta cədvəl (sənəd, mövqe, növ, dil, tarix Asia/Baku) → 1. Qısa nəticə (bal, saylar, qüvvəsiz şərtlər, kritiklərin siyahısı, "imzalanmamalıdır" / "imzalana bilər") → 2. Əsas şərtlər (kart) → 3. Məsələlər (risk rəngli, müqavilədə, qiymətləndirmə, qanun mətni `Quote` üslubunda, tövsiyə, güzəşt, arqument) → çatışmayan mövzular → texniki qeydlər → metodologiya (mənbə, "N tövsiyədən M-i daxil edilib") → imza yeri. `redliner.new_document()` (zoom düzəlişi) işlədir.

### 5.6g `agent/compare.py` + `compare_page.py` — versiya müqayisəsi
- `align(old, new)`: bənd mətnləri (sözlərə bölünmüş, **" | " cədvəl sətirləri atılmış** — imza cədvəli sonuncu bəndə yapışır) üzərində `SequenceMatcher`; `equal` → "eyni" (nömrə dəyişsə də); dəyişiklik bloklarında cütlər oxşarlığa görə acgöz (≥ 0.3) → "dəyişib"; qalanlar "silinib" / "əlavə".
- `track(findings, changes)`: bəndin silinməsi təklif olunmuşdusa — silinib → qəbul, eyni → rədd; əks halda **bütün** yeni bəndlər arasında təklifə oxşarlıq ≥ 0.85 → qəbul, güzəştə ≥ 0.85 → güzəşt qəbul, dəyişməyib → rədd, dəyişib və təklifə ≥ 0.5 → qismən, silinib → "bənd silinib", əks halda "başqa cür dəyişdirilib". Çatışmayan bənd: təklifə ≥ 0.6 → qəbul; başlığın açar sözləri yeni bənddə varsa → qismən; əks halda "əlavə edilməyib".
- `analyze(..., focus=[dəyişən bəndlər])`: yeni versiyanın təhlilinə `FOCUS_NOTE` — model yeni əlavə olunmuş cərimə / birtərəfli şərtləri qaçırmasın (fokussuz qaçırırdı).
- `redline(old_doc, changes)`: `Redliner(author="Yeni versiya (qarşı tərəf)", comments=False)`: dəyişib → `replace_clause` (söz səviyyəsində), silinib → `""`, əlavə → `add_clause(anchor, nömrə, mətn)`. Reject All = köhnə versiya.
- `diff_markdown`: Streamlit üçün `:red[~~...~~]` / `:green[**...**]`, markdown simvolları escape.
- UI: sidebar rejim radiosu; iki fayl (docx/pdf/txt) → hər iki versiya paralel təhlil → metriklər (bal + delta, qəbul edilən təkliflər, dəyişən bəndlər, yeni risklər) → 2 Word (müqayisə; yeni versiyaya cavab redline-ı) → təkliflərin taleyi cədvəli → yeni risklər → diff-lər.

### 5.7 `agent/score.py`
`WEIGHTS = {kritik: 20, orta: 8, aşağı: 3}`, `value = round(100 * (1 - exp(-xal / 60)))`.
Səviyyələr: `<25` aşağı risk (green), `<50` orta (orange), `<75` yüksək (red), əks halda çox yüksək (red).
Yoxlama: 0 → 0, 1 kritik → 28, 3 kritik → 63.

### 5.8 `agent/redliner.py` — ən riskli hissə, diqqətlə
`python-docx` track changes bilmir; XML-i özümüz yazırıq. Müəllif `"Müqavilə agenti"`, tarix `%Y-%m-%dT%H:%M:%SZ` (UTC), `w:id` sayğacı 9001-dən.

- `_mark(tag)` → `w:ins`/`w:del` elementi, `w:id`, `w:author`, `w:date` ilə.
- `_delete_runs(runs)`: ilk run-dan əvvəl `w:del` qoy, run-ları ora köçür; içində `w:t` → **`w:delText`**, `w:instrText` → `w:delInstrText`.
- `_insert_run(after, text, rpr=None, bold=False)`: `after`-dən sonra `<w:ins><w:r>` (silinən run-ın `rPr` surəti). Mətni `Run(r, None).text = text` ilə yaz (`\n` → `w:br`).
- `_mark_paragraph(p, "w:del"|"w:ins")`: `pPr/rPr`-ın **ilk uşağı** kimi (sxem tələbi).
- **Söz səviyyəsində redline** (`_diff_replace`): bənd bir abzasdırsa və təklif boş deyilsə, köhnə və yeni mətn `re.findall(r"\s+|\w+|[^\w\s]")` ilə tokenlərə bölünür, `difflib.SequenceMatcher(autojunk=False)`. Oxşarlıq < 0.5 → tam əvəzləmə. `merge_small_gaps`: iki dəyişiklik arasında ≤ 1 söz (boşluqlar sayılmır) olan `equal` bloku birləşdir — əks halda redline "söz-söz dama" olur. Run-lar dəyişiklik sərhədlərində bölünür; `equal` run-lar toxunulmaz, `delete` → `w:del`, `insert` → `w:ins` (qonşu run-ın `rPr`-ı ilə). Nəticə: `[-3 (üç-]{+2 (iki+}) aylıq ... [-2400-]{+1600+}`.
- `replace_clause(paragraphs, key, new_text) -> anchor runs`:
  - `number = key.rstrip("'")`. Təklif özü `number` ilə başlayırsa, onu kəs.
  - Birinci abzasın **birbaşa** `./w:r` run-larının mətni `CLAUSE`-a uyğundursa **və** `match[1] == number` — prefiks (nömrə) saxlanılır (run prefiks sərhədində bölünür). Əks halda (avtomatik nömrə) prefiks = 0. *(Avtomatik nömrəli bəndin mətni "3 (üç) aylıq" kimi başlaya bilər — bu nömrə deyil.)*
  - Qalan run-lar `w:del`, sonra `w:ins` ilə yeni mətn. Davam abzasları: run-lar `w:del` + abzas işarəsi `w:del`.
  - `new_text == ""` → nömrə də silinir, birinci abzas işarəsi `w:del`; şərh silinən run-a bağlanır.
- `add_clause(after, title, text)`: yeni `w:p`, `after`-in `pPr` surəti (**`numPr` və `rPr` silinmiş**), abzas işarəsi `w:ins`, qalın `"{title}. "` + mətn, hər ikisi `w:ins`.
- `comment(runs, finding)`: `document.add_comment(runs, text="{Tip} · risk: {risk} — {başlıq}", author, initials="MA")`, sonra `note.add_paragraph(izah)`, `"Mülki Məcəllə, {madde_basliq} (bənd X)"`, `"Verifier: {qeyd}"`.
- `clause_bodies(lines)`: `clause_spans`, amma davam abzasları **böyük hərfli sətirdə dayanır**, **son nömrəli bəndə davam abzası qoşulmur** (orada imzalar olur).
- `redline(document, result, party="icarəçi", clean=False) -> bytes`:
  1. `pairs = paragraph_lines(document)`; `spans = clause_bodies(...)`.
  2. `clean` deyilsə: birinci abzasa **xülasə şərhi** (risk balı, tapıntı sayları, çatışmayan mövzular).
  3. Hər tapıntı (catismayan xaric): eyni bəndə ikinci tapıntı və ya `"Başlıq"` → yalnız şərh; əks halda `replace_clause` + şərh.
  4. `catismayan` (təklifi boş olmayan): son nömrəli bəndin son abzasından sonra `add_clause(..., "Əlavə bənd — {basliq}", teklif)`, ardıcıl.
  5. `clean` → `accept_all(document)`; şərhlər yazılmır.
- `accept_all(document)`: abzas işarəsi `w:del` olan abzasları qeyd et və markerləri sil; bütün `w:del` sil; `w:ins`-i aç (uşaqları yerinə köçür); qeyd edilmiş və mətni qalmamış abzasları sil.
- `load(data, filename, lines)`: `.docx` → orijinal; əks halda yeni `docx.Document()` + hər sətir abzas. **Yeni sənəddə `settings.xml`-də `w:zoom`-a `w:percent="100"` yaz** (python-docx şablonunun sxem xətası).

### 5.9 `app.py` (Streamlit)
- Sidebar: mənbə (`Fayl yüklə` / `Mətni yapışdır`), tərəf, **Yoxla**, "Keşi keçmək".
- Yoxla: `read_lines` / sətirlər → `split_clauses` → `analyze` → `verify`, `st.status` ilə mərhələlər ("keşdən" / "N san"). **İstənilən xəta** → `st.error` anlaşılan mesaj + "Texniki detal" expander; traceback göstərmə.
- `session_state`: `result, filename, party, source=(data, filename, lines), run_id` (yeni təhlildə widget açarları sıfırlansın deyə).
- Widget açarları `use_{run_id}_{i}`, `text_{run_id}_{i}`; **əvvəlcə `st.session_state.setdefault(...)`, widget-ə `value=` vermə** (əks halda Session State xəbərdarlığı).
- Sıra: risk balı (`:color[...]` + `st.progress` + düstur izahı) → 5 metrik (növ, kritik, orta, aşağı, Verifier "N atdı · M düzəltdi") → Word bloku ("N/M düzəliş seçilib", 2 download düyməsi, "Hamısı"/"Heç biri" `on_click`) → yoxlama siyahısı expander → kartlar → "Verifier atdı" expander.
- Kart: başlıq + tip/risk; sağda `st.toggle("Word-a daxil et")`; "Müqavilədə:" bənd; izah (`error`/`warning`/`info` riskə görə); `qeyd`; qanun mətni expander; redaktə olunan `text_area` (söndürüləndə disabled).
- Word faylları **seçilmiş və redaktə olunmuş** tapıntılardan: `dataclasses.replace(f, teklif=...)`, `dataclasses.replace(result, findings=selected)`.

### 5.10 Skriptlər
- `extract_law.py`: `mulki_mecelle.docx` abzaslarında `"33-cü fəsil."`-dən `"35-ci fəsil."`-ə qədər, `\[\d+\]` (izah qeydləri) silinir → `icare.txt`. Çıxış: `48 maddə`.
- `review.py <fayl> [tərəf]`: təhlil + terminalda nəticə + `output/<ad>_düzəliş.docx`.
- `evaluate.py [--refresh]`: `data/contracts/gozlenilen.json`-dakı hər müqaviləni (paralel) təhlil edir, düzgün cavablarla müqayisə edir → terminal + `output/eval.md`. `gozlenilen.json` formatı: `{"ad": {"emlak_novu", "expected": {bənd: tip|null}, "acceptable": [...], "traps": [...], "missing": [mövzu adları]}}`. Metriklər: recall (expected tapıldı), precision (tapılan bəndlərdən expected ∪ acceptable olanlar), tip dəqiqliyi, çatışmayan mövzular (`siyahi`-də `var=false`), uydurma (Verifier-in "yoxdur" səbəbli atdıqları), Verifier düzəlişləri.

---

## 6. Prompt-lar (fayllar gətirilir, məzmunun xülasəsi)

`prompts/system.md`: rol; iş ardıcıllığı (əmlak növü → 11 mövzu → bəndlər); **`qanuna_zidd` yalnız B cədvəlinə istinadla**; `madde_no` yalnız 675–722; risk meyarları (kritik = əmlakdan məhrum olma / 1 aylıq haqqdan çox itki / hüququn tam itməsi); `izah` tipə uyğun (`birterefli`-də "qanunsuz" sözü yox); **`teklif` göstərilən maddənin BÜTÜN tələblərini ödəyir** (688.2: 2 ay + bank + faiz); `teklif` birbaşa Word-a yazılır — nömrəsiz, şərhsiz; boş = sil; JSON formatı.

`prompts/checklist.md`: A — 11 mövzu (Tərəflər, Predmet, İcarə haqqı, Müddət, Təhvil-təslim, Kommunal/vergi, Təmir, Ləğvetmə, Qaytarılma, Fors-major, Mübahisələrin həlli); B — imperativ normalar (5.2 ilə eyni), "yaşayışda gecikmə/satışda ləğv → 687"; C — dispozitiv normalar (682, 699.1, 685.2, 680.1, 676, 688.2 ofis üçün, 691.1.3); D — tipik birtərəfli şərtlər.

---

## 7. Qəbul testləri

```bash
uv run pytest                 # 57 test, API-siz, ~1 san
uv run python scripts/evaluate.py   # keyfiyyət: recall / precision / tip / uydurma (5 müqavilə)
uv run python scripts/review.py data/contracts/xarab_01.docx   # real model, ~1–2 dəq
```

| Müqavilə | Gözlənilən |
|---|---|
| `xarab_01.docx` | 12 bənd tapılır (3.3–5.4) + 2 çatışmayan, 0 atılan, bal ~95 |
| `xarab_01_avto.docx` | yuxarıdakı ilə **eyni** (avtomatik nömrələmə) |
| `ofis_01.txt` | qeyri-yaşayış; 3.3 və 5.3 `birterefli` (qanuna zidd yox); 3.2, 4.4, 4.5 tapılmır; bal ~77 |
| `temiz_01.txt` | kritik yoxdur, `qanuna_zidd` yoxdur, siyahı 11/11, bal < 25 |
| `kor_01.txt` | kor test: 3.2, 4.2, 5.1, 5.2 `qanuna_zidd`; 3.4 `birterefli`; 4.1, 4.4 tapılır; bal ~85 |

Word faylı yoxlaması (docx skill validatoru, əgər mövcuddursa):
```bash
python <docx-skill>/scripts/office/validate.py output/xarab_01_düzəliş.docx --original data/contracts/xarab_01.docx --author "Müqavilə agenti"
```

---

## 8. Tələlər (keçmişdə rastlaşdıq — təkrarlama)

| Problem | Həll |
|---|---|
| Gemma `<thought>` bloku cavabın əvvəlində | `split("</thought>")[-1]` |
| Google AI Studio pulsuz planı: dəqiqədə 16k input token, sorğu ~30k | OpenRouter işlət |
| Model JSON-u ```` ```json ```` içində qaytarır | `parse_json` çərçivəni təmizləyir |
| `p.text` Word avtomatik nömrəsini görmür | `numbering.py` |
| `p.text` `<w:ins>` içindəki mətni görmür | `visible_text` |
| `pPr/tabs/tab` `w:tab` elementidir, amma mətn deyil | valideyn `w:r` yoxlaması |
| python-docx şablonunda `w:zoom` `w:percent`-siz — sxem xətası | `load()`-da düzəlt |
| `w:del` içində `w:t` qalsa — Word pozulur | `w:delText` |
| `pPr/rPr`-da `w:del`/`w:ins` ilk uşaq olmalıdır | `rpr.insert(0, ...)` |
| Son bəndin arxasındakı imzalar bəndin "davamı" sayılır | `clause_bodies` son bəndə davam qoşmur |
| Nömrəsiz böyük hərfli başlıq bəndin davamı sayılır | `isupper()`-də dayan |
| Streamlit `agent/` dəyişəndə köhnə modulu işlədir | serveri yenidən başlat |
| Streamlit ilk işə salmada e-poçt soruşur | `.streamlit/config.toml` headless |
| Widget-ə həm `value=`, həm `session_state` | yalnız `setdefault` |
| Model 687 əvəzinə 685.2 / 699.1-ə istinad edir (yaşayış) | checklist.md B-də açıq qeyd |
| Model "qanuna zidd"-i ofisə tətbiq edir | Verifier endirir + prompt qaydası |
| Model müddətdən bitmə tarixini özü hesablayır | tarix yalnız ili müqavilədə varsa qəbul |
| Model kartda "3.1, 3.2" kimi bir neçə bənd verir | bölüb yoxla |
| Sual-cavab: "davam edirmi?" → "Xeyr ... davam edir" (ziddiyyət) | qa.md: qısa cavab sualın formasına uyğun |
| Sual-cavab: müddətli müqaviləyə 691 (müddətsiz) tətbiq edir | qa.md: müddətli / müddətsiz qaydası |
| `llm.py` import zamanı açar tələb edir — testlər sınır | `os.getenv(...) or "açar-yoxdur"` |
| OpenRouter 402 `in_flight_budget_exhausted` | hesabda kredit bitib — balansı yoxla (`/api/v1/credits`), paralel sorğuları azalt (evaluate: 3) |
| Müqayisədə imza cədvəli sonuncu bəndə yapışır, uyğunlaşdırma çaşır | `_body()` " | " sətirlərini atır |
| Yeni versiyada əlavə olunmuş cəriməni model qaçırır | `focus` — dəyişən bəndlər prompt-da |
| Model yaşayışda 691.2-ni (bildiriş müddəti) standart qayda sayır | `IMPERATIVE["691.2"] = yaşayış` (691.3: qısaldılması qüvvəsiz) |
| Model 681-ə istinad edib tipi "birterefli" yazır | system.md: B normasını pozursa tip mütləq `qanuna_zidd` |
| Türk sözləri ("orantısız") | prompt-da konkret "X yox — Y" siyahısı |

---

## 9. Qurma ardıcıllığı (~60 dəq)

| # | Dəq | Addım | Qəbul testi |
|---|---|---|---|
| 1 | 5 | Mühit, `pyproject`, `.env`, qovluqlar, data faylları | `uv run python -c "import docx, openai, streamlit"` |
| 2 | 5 | `llm.py` | kiçik sorğu Azərbaycan dilində cavab qaytarır |
| 3 | 5 | `law.py` (+ `extract_law.py`) | 48 maddə; `lookup("650")` → None; `is_imperative` cədvəli |
| 4 | 8 | `numbering.py` + `parser.py` | `xarab_01` və `xarab_01_avto` eyni bəndlər |
| 5 | 5 | `analyzer.py` | `review.py` ilə real təhlil JSON qaytarır, keş yaranır |
| 6 | 5 | `verifier.py` + `score.py` | uydurma maddə/bənd atılır; ofisdə 688.2 endirilir |
| 7 | 12 | `redliner.py` | Reject All = orijinal; təmiz versiyada ins/del yoxdur; validator |
| 8 | 10 | `app.py` | tam dövrə brauzerdə; toggle/redaktə Word-a təsir edir |
| 8a | 15 | `checks.py`, `ics.py`, kart + danışıq (prompt + verifier), `qa.py` | texniki yoxlama testləri; güzəşt Word-a düşmür; sual-cavab istinadları yoxlanır |
| 8b | 15 | dil təyini + `LANGUAGE_NOTE`, `memo.py`, `compare.py` + `compare_page.py` | ru/en təklifləri öz dilində; rəy yalnız seçilənlərlə; v2-də təkliflərin statusu düzgün |
| 9 | 5 | `tests/test_pipeline.py`, `review.py`, `evaluate.py`, README | `uv run pytest` yaşıl; `evaluate.py` 100%-ə yaxın, uydurma 0 |

Hər addımdan sonra `uv run ruff check . && uv run ruff format .` və commit.
