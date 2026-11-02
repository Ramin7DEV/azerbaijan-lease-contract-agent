# Araşdırma: dünyada AI ilə müqavilə yoxlaması (28.09.2026)

Məqsəd: oxşar məhsulları tapmaq, necə işlədiklərini öyrənmək, bizə nəyin inteqrasiya oluna biləcəyini müəyyən etmək.

## Qısa nəticə

1. **Bazar var və böyükdür.** Spellbook, LegalOn, Screens (Agiloft), BlackBoiler — hamısı eyni sxemlə işləyir: *playbook* (yoxlama standartları) + risk dərəcəsi + **Word-da track changes**. Bizim arxitektura sənaye standartına uyğundur.
2. **Hamısının zəif yeri — uydurma.** Stanford tədqiqatı: Lexis+ AI və Westlaw AI kimi aparıcı hüquqi AI alətləri **17–33%** hallarda uydurur. Bizim Verifier məhz bu problemi həll edir.
3. **Azərbaycan dilində müqavilə yoxlayan alət tapmadıq.** Dövlətin [E-Qanun.ai](https://www.e-qanun.ai/) platforması **qanunlarda axtarış** edir, müqavilə yoxlamır və düzəltmir. Biz onun rəqibi deyil, tamamlayıcısıyıq.
4. **İnteqrasiya üçün ən dəyərli ideyalar:** söz səviyyəsində redline, keyfiyyətin rəqəmlə ölçülməsi, qarşı tərəfin baxışı, müştəri üçün hüquqi rəy.

---

## 1. Kommersiya məhsulları

| Məhsul | Nə edir | Bizdə var? |
|---|---|---|
| [Spellbook](https://www.spellbook.legal/features/benchmarks) | Word add-in. Qeyri-standart şərtləri tapır, redline-ları vəkilin adından track changes kimi yazır. 2026-dan "Compare to Market": şərti 2300+ bazar standartı ilə müqayisə edir, çatışmayan şərtləri göstərir. | Track changes ✅, çatışmayan bəndlər ✅, bazar müqayisəsi ❌ |
| [LegalOn](https://www.legalontech.com/contract-playbooks) | Vəkillərin yazdığı 135+ playbook (müqavilə növü + danışıq mövqeyinə görə), riskləri Low/Medium/High dərəcələyir, bir kliklə redline. "My Playbooks": firmanın öz standartları. | Playbook (checklist.md) ✅, tərəf seçimi ✅, öz playbook-unu yazmaq ❌ |
| [Screens / Agiloft](https://www.agiloft.com/blog/screens-accuracy-evaluation-report) | "Standart" = ikili **keçdi/keçmədi** qaydası. İcma playbook-ları. Dəqiqliyi açıq metodologiya ilə ölçüb dərc edir: **97.5%** (720 qərar, 51 müqavilə). | Yoxlama siyahısı ✅/❌ ✅, dəqiqliyin ölçülməsi qismən |
| [BlackBoiler](https://blackboiler.com/) | Word-da redline. Qaydalarla deyil, müştərinin keçmiş redline-larından öyrənir. | ❌ (bizdə tarixçə yoxdur) |

**Ümumi nümunə:** *"AI təklif edir, vəkil qərar verir"*. Hər düzəliş ayrıca qəbul və ya rədd edilir. Bizdə bu var: kartlarda seçim + Word-da Accept/Reject.

**Screens-dən öyrəniləcək dərs:** prompt-a açıq **təlimat** (edge case-lər, üstünlüklər) əlavə etmək onların dəqiqliyini **8%** artırıb (89.3% → 97.5%). Bizim `checklist.md`-dəki B/C cədvəlləri və "687-yə istinad et" qeydi məhz belə təlimatdır, testlərimizdə də eyni effekti gördük (12/14 → 14/14).

## 2. Açıq mənbəli layihələr (GitHub)

| Layihə | Nə edir | Bizim üçün nə götürmək olar |
|---|---|---|
| [legal-redline-tools](https://github.com/evolsb/legal-redline-tools) (MIT, 60★) | AI-nın JSON düzəlişlərindən track changes DOCX, redline PDF və **daxili danışıq memosu** yaradır. | **Xarici / daxili** sənəd ayrımı: qarşı tərəfə strategiyasız redline, komandaya isə əsaslandırma, "geri çəkilmə mövqeyi" və prioritetlərlə memo. Mətn uyğunlaşdırmada dırnaq/tire/boşluq normallaşdırması. |
| [REDLINE agent](https://github.com/AaryanSehgal/redline-agent) | Eyni bəndi **iki agent** oxuyur: biri müştəri, biri təchizatçı kimi. Risk = onların fikir ayrılığı. CUAD ilə qiymətləndirilir. | **Qarşı tərəfin baxışı:** hər düzəlişə "qarşı tərəf nə etiraz edəcək" qeydi. Bizim tərəf seçimimizin təbii davamıdır. |
| [contract-review-pipeline](https://github.com/marvelousorimoloye-hub/contract-review-pipeline) | LangGraph ilə 4 agent: çıxarış → playbook üzrə risk → presedent axtarışı → redline. İnsan yoxlaması və **eval harness** (precision/recall). | Keyfiyyət ölçümü: test müqavilələrində precision / recall rəqəmləri. Hər etiket konkret qaydaya bağlanır — bizdə də `*_gozlenilen.md` belədir. |
| [Redline Buddy](https://github.com/dhruv1220/redline-buddy) | Lokal, açarsız: YAML playbook + Python evristikaları. | Konfidensiallıq arqumenti — bizdə open-weight Gemma ilə eyni. |
| [Ally (Azure Samples)](https://github.com/Azure-Samples/ally-legal-assistant) | Word add-in (Office.js): təhlil, sual-cavab, siyasətə görə avtomatik redline. | Gələcək: bizim agenti Word-un içinə add-in kimi qoymaq. |
| [redline-llm](https://github.com/MarcusElwin/redline-llm) | Açıq modeli redline üçün fine-tune edir. | Gələcək: Gemma-nı Azərbaycan müqavilələri üzrə fine-tune. |

## 3. Redline (track changes) kitabxanaları

| Kitabxana | Xüsusiyyət | Lisenziya |
|---|---|---|
| [docx-redline](https://github.com/gh-aswanth/docx_walking) | Ən tam: **söz səviyyəsində diff**, formatlaşdırma dəyişiklikləri, köçürmə, avtomatik yenidən nömrələmə, 386 test | MPL-2.0 |
| [Adeu](https://github.com/dealfluence/adeu) | DOCX → Markdown (LLM üçün) → düzəlişlər geri track changes kimi; mətnlə lövbərləmə, qeyri-müəyyən uyğunluqları bloklayır. 163★ | MIT |
| [Python-Redlines](https://github.com/JSv4/Python-Redlines) | İki DOCX-i müqayisə edib redline yaradır | MIT |
| [docx-revisions](https://github.com/balalofernandez/docx-revisions), [docx-editor](https://github.com/pablospe/docx-editor) | python-docx-ə `w:ins`/`w:del` dəstəyi | — |

**Qərar: öz Redliner-imizi saxlayırıq.** Səbəblər:
- bizimki bəndləri **nömrə** ilə tapır, bu isə mətnlə axtarışdan daha etibarlıdır (təkrarlanan ifadələr problem yaratmır);
- Word-un avtomatik nömrələməsini bilir, imzaları və başlıqları qoruyur;
- validator və 29 testdən keçib, xarici asılılıq yoxdur.

**Götürülən ideya:** docx-redline kimi **yalnız dəyişən sözləri** işarələmək (bütün bəndi silib yenisini yazmaq əvəzinə). Vəkillər minimal redline gözləyir: "3 (üç) aylıq" → "2 (iki) aylıq" dəyişikliyi bütün abzasın qırmızı olmasından qat-qat aydın oxunur.

## 4. Tədqiqatlar və rəqəmlər

- **Stanford (JELS, 2025):** Lexis+ AI **17%**, Westlaw AI-Assisted Research **33%** hallarda uydurur. Düzgün cavab payı 65% və 42%. → [PDF](https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf)
- **Uydurma istinadlar artır:** 2025-ci ildə elmi və hüquqi mətnlərdə ən azı **146 932** uydurma istinad aşkarlanıb, 2024-ün ortasından kəskin artım var. → [arXiv 2605.07723](https://arxiv.org/pdf/2605.07723)
- **LawGeex (2018):** NDA yoxlamasında AI **94%**, 20 təcrübəli vəkil **85%** dəqiqlik göstərib. Vəkillər orta hesabla **92 dəqiqə**, AI isə **26 saniyə** sərf edib. → [Artificial Lawyer](https://www.artificiallawyer.com/2018/02/26/lawgeex-hits-94-accuracy-in-nda-review-vs-85-for-human-lawyers/)
- **Screens:** playbook-a əsaslanan yoxlamada **97.5%** dəqiqlik; açıq təlimatlar dəqiqliyi +8% artırır. → [Agiloft](https://www.agiloft.com/blog/screens-accuracy-evaluation-report)
- **CUAD:** 510 müqavilə, 41 bənd kateqoriyası, 13 000+ vəkil etiketi — sahənin əsas açıq dataseti. → [Atticus Project](https://www.atticusprojectai.org/cuad/)

## 4a. Qlobal bazarın digər oyunçuları

| Məhsul | Seqment | Qeyd |
|---|---|---|
| Harvey | Böyük hüquq firmaları, həm tədqiqat, həm müqavilə | ~$1 200–2 000 / nəfər / ay, 20 nəfərlik minimum |
| Luminance | M&A due diligence, avtomatik danışıq | Böyük həcmdə müqavilə oxuma |
| Robin AI | Kiçik və orta firmalar (NDA, MSA, əmək) | Playbook əsaslı redline, əlçatan qiymət |
| Kira | Minlərlə sənəddən bənd çıxarışı | Tranzaksiyalarda |
| Ironclad | CLM: təsdiq axını, saxlama, öhdəliklər | Yoxlamadan çox iş prosesi |

Mənbə: [müqayisəli icmallar](https://guptadeepak.com/tools/top-5-ai-legal-contract-tools-2026/), [LegalOn icmalı](https://www.legalontech.com/post/best-ai-contract-review-tools). **Nəticə:** bu məhsullar ingilis dilli, ümumi hüquq (common law) bazarı üçündür və bahadır. Azərbaycan dili və Mülki Məcəllə üçün heç biri uyğun deyil.

## 4b. Açıq infrastruktur və benchmark-lar

- **[OpenContracts](https://github.com/Open-Source-Legal/OpenContracts)** (MIT) — sənəd analitikası platforması: annotasiya, strukturlaşdırılmış çıxarış, AI agentlər, MCP server. **[LexNLP](https://github.com/LexPredict/lexpredict-lexnlp)** — hüquqi mətn üçün NLP kitabxanası (ingilis dili).
- **Benchmark-lar:** [LegalBench](https://proceedings.neurips.cc/paper_files/paper/2023/file/89e44582fd28ddfea1ea4dcb0ebbf4b0-Paper-Datasets_and_Benchmarks.pdf) (162 tapşırıq), ContractNLI (bənd var / zidd / qeyd olunmayıb), MAUD (birləşmə müqavilələri), [ACORD](https://arxiv.org/pdf/2501.06582) (presedent bənd axtarışı).
- **[ContractEval](https://arxiv.org/html/2508.03080)** — məhz bizim tapşırıq: LLM-lər müqavilədə bənd səviyyəsində riski tapırmı (CUAD, 41 kateqoriya, 19 model). Nəticələr:
  - bağlı modellər öndədir: GPT-4.1 F1 0.64, ən yaxşı açıq model 0.54;
  - açıq modellərin əsas xətası **"tənbəllik"**: bənd olduğu halda "yoxdur" deyir (bəzi modellərdə ~30%);
  - kvantlaşdırma keyfiyyəti azaldır; nadir risk kateqoriyalarında bütün modellər zəifdir;
  - tövsiyə: AI-ı gənc köməkçi kimi yerləşdirmək, son qərarı vəkilə vermək.

  **Bizim üçün dərs:** 11 mövzunu bir-bir cavablandırmağa məcbur edən yoxlama siyahısı "tənbəlliyə" qarşı qorunmadır; imperativ/dispozitiv cədvəli nadir halları açıq təlimata çevirir; UI-da hər düzəliş vəkilin seçimidir.

## 4c. İcarə müqavilələri üzrə açıq layihələr

| Layihə | Yanaşma | Götürüləcək ideya |
|---|---|---|
| [Lease-Review-Assistant](https://github.com/san-thiya5/Lease-Review-Assistant) | Bəndlər regex ilə (LLM-siz) bölünür; standartlar rəqəmlə: depozit 1–2 ay, bildiriş 30–60 gün; "Match / Deviate / Forbidden" | **"Susqunluq da tapıntıdır"** (bizdə: çatışmayan bəndlər). **Deterministik qayda qatı**: məsələn, yaşayışda depozit 2 aydan çoxdursa, model qaçırsa belə kod tutsun |
| [LeaseLens](https://github.com/AdityaTummuri/LeaseLens) | Şərtləri regionun bazar statistikası ilə müqayisə edir; "hüquqi məsləhət" ifadələrini süzən qoruyucu agent | Bazar orta göstəriciləri (məs. Bakıda adi depozit); nəticələrdə məsuliyyət xəbərdarlığı |
| [Lease Plain](https://github.com/tomd0627/lease-plain) | Kirayəçi üçün sadə dildə izah, gizli ödənişləri tapmaq | Vətəndaş rejimi (vəkil olmayan istifadəçi üçün) |

## 5. Azərbaycan konteksti

- **[E-Qanun.ai](https://www.e-qanun.ai/)** — Ədliyyə Nazirliyi və Rəqəmsal İnkişaf Nazirliyinin layihəsi, AZCON-un Milli Süni İntellekt Mərkəzi hazırlayıb. "Süni İntellekt Strategiyası 2025–2028" çərçivəsindədir. **Qanunvericilikdə axtarış** platformasıdır. → [Mincom](https://mincom.gov.az/en/media-en/news/e-qanunai-platform-officially-presented)
  *Mövqeyimiz:* "E-Qanun.ai qanunu tapır, bizim agent isə müqaviləni o qanunla yoxlayır və düzəldir." Rəqib deyil, növbəti addımıq. Dövlət strategiyası ilə üst-üstə düşür, bu da təqdimat üçün yaxşı arqumentdir.
- **[YOXLA](https://github.com/LocalDoc-Azerbaijan/yoxla)** (LocalDoc) — Gemma-nı seçməyimizin əsası.
- **[allmalab/eqanun](https://huggingface.co/datasets/allmalab/eqanun)** — e-qanun.az-dan toplanmış qanunlar (Apache-2.0, ~150 MB). Gələcəkdə Mənzil Məcəlləsi və başqa qanunları bazaya əlavə etmək üçün mənbədir. (Qeyd: 2024-cü il vəziyyətidir; bizim Məcəllə mətni daha təzədir.)
- **LocalDoc** — Azərbaycan dili üçün RAG və embedding benchmark-ları. RAG-a qayıtsaq, lazım olacaq.

---

## 5a. Funksiya xəritəsi: qlobal məhsullarda nə var, bizdə nə var

| # | Funksiya | Kimdə var | Bizdə | Azərbaycan vəkili üçün dəyəri |
|---|---|---|---|---|
| 1 | Risk tapma + track changes redline | Spellbook, LegalOn, Luminance, Robin, BlackBoiler | ✅ | əsas iş |
| 2 | Playbook (yoxlama standartları) | LegalOn, Screens, Robin | ✅ (Mülki Məcəllə əsasında) | əsas iş |
| 3 | Vəkil hər düzəlişi qəbul / rədd edir | hamısı | ✅ | etibar |
| 4 | Orijinal mənbəyə klikli istinad | Spellbook Ask, Robin Reports | ✅ (qanun mətni bazadan) | etibar |
| 5 | **Müqavilə kartı**: əsas şərtlərin xülasəsi (tərəflər, məbləğ, depozit, müddət, bildiriş müddətləri) | LegalOn Summary, Robin Tables | ❌ | vəkil müqaviləni 10 saniyəyə anlayır |
| 6 | **Müqavilə ilə sual-cavab** (istinadla) | Spellbook Ask, LegalOn Assistant, Ask Lumi, Robin | ❌ | "Müştərim nə vaxt çıxa bilər?" — cavab bənd + qanun maddəsi ilə |
| 7 | **Danışıq mövqeləri**: ideal mövqe, güzəşt variantı, arqument | Luminance ("middle ground"), Robin (talking points), legal-redline-tools (walkaway) | ❌ | danışığa hazır gəlir |
| 8 | **Deterministik yoxlamalar**: tərif / istinad / rəqəm uyğunsuzluğu | Definely | ❌ | "800 (yeddi yüz)", olmayan bəndə istinad — kod tapır, uydurma riski sıfır |
| 9 | Açar tarixlər və xəbərdarlıqlar (bitmə, bildiriş son günü, ödəniş) | Luminance, LegalOn Vault | ❌ | təqvimə (.ics) ixrac |
| 10 | Versiya müqayisəsi: qarşı tərəf nəyi dəyişdi, risk necə dəyişdi | Luminance | ❌ | danışığın 2-ci raundu |
| 11 | Hüquqi rəy / hesabat (müştəri üçün) | Robin Reports | ❌ | vəkilin ikinci gündəlik işi |
| 12 | Tərcümə: rus / ingilis dilli müqaviləni yoxlamaq, redline orijinal dildə | LegalOn Translate | ❌ | Bakıda çox müqavilə rus / ingilis dilindədir |
| 13 | Bənd yazmaq (şablon / kitabxanadan) | Spellbook Draft, Library | qismən (çatışmayan bəndlər) | — |
| 14 | Bazar standartı ilə müqayisə | Spellbook Benchmarks | ❌ | data yoxdur — sonra |
| 15 | Portfel / çox sənəd, repozitoriya | LegalOn Vault, Spellbook Associate | ❌ | verilənlər bazası lazımdır — sonra |
| 16 | Word add-in | Spellbook, Robin, Ally | ❌ | sonra |

Mənbələr: [Spellbook](https://lawyerist.com/reviews/artificial-intelligence-in-law-firms/spellbook-review-artificial-intelligence-for-lawyers/), [LegalOn Assistant](https://www.legalontech.com/post/introducing-legalon-assistant), [LegalOn Translate / Vault](https://www.businesswire.com/news/home/20260407968823/en/LegalOn-Expands-Global-Contracting-Capabilities-for-In-House-Legal-Teams), [Luminance Negotiate](https://www.luminance.com/negotiate/), [Ask Lumi](https://www.luminance.com/resources/blog/product-feature-spotlight-answer-any-contract-query-with-lumi-pro-%C2%96-the-%C2%91google%C2%92-of-contracts/), [Robin AI](https://www.layer3labs.io/guides/robin-ai-explained), [Definely](https://www.definely.com/blogs/how-ai-improves-contract-review).

## 6. Bizə inteqrasiya: təkliflər (prioritet sırası ilə)

| # | Təklif | Mənbə | Dəyər | İş |
|---|---|---|---|---|
| 1 | **Söz səviyyəsində redline** — yalnız dəyişən sözlər qırmızı/yaşıl | docx-redline | Word faylı peşəkar görünür, vəkil dəyişikliyi bir baxışda görür | Az (`difflib`) |
| 2 | **Keyfiyyət ölçümü** — test müqavilələrində precision / recall / uydurma sayı, bir əmrlə | Screens, contract-review-pipeline | Konkret rəqəm: "X% dəqiqlik, 0 uydurma" | Az |
| 3 | **Qarşı tərəfin baxışı** — hər düzəlişə "qarşı tərəf nə deyə bilər və necə cavab vermək olar" | REDLINE agent | Danışıq üçün real fayda; tərəf seçimimizi gücləndirir | Orta (prompt + UI) |
| 4 | **Hüquqi rəy (memo)** — müştəri üçün Word: xülasə, risklər, tövsiyələr; redline-dan ayrı, daxili sənəd | legal-redline-tools | Vəkilin ikinci gündəlik işi | Orta |
| 5 | Öz playbook-unu yazmaq (UI-da checklist redaktəsi) | LegalOn, Screens | Hər firma öz standartını qoyur | Orta |
| 5a | Deterministik qayda qatı (depozit > 2 ay və s. kodla) | Lease-Review-Assistant | Model qaçırsa belə kod tutur | Orta |
| 6 | Word add-in (Office.js) | Spellbook, Ally | Vəkil Word-dan çıxmır | Böyük — sonrakı mərhələ |
| 7 | Qanun bazasının genişləndirilməsi (Mənzil Məcəlləsi və s.) | allmalab/eqanun | Daha çox norma | Böyük — sonrakı mərhələ |

## Mənbələr

- Kommersiya: [Spellbook Benchmarks](https://www.spellbook.legal/features/benchmarks), [LegalOn playbooks](https://www.legalontech.com/contract-playbooks), [Screens accuracy report](https://www.agiloft.com/blog/screens-accuracy-evaluation-report), [Agiloft acquires Screens](https://www.lawnext.com/2025/01/agiloft-acquires-screens-ai-contract-review-technology-based-on-expert-built-playbooks.html), [BlackBoiler](https://blackboiler.com/)
- Açıq mənbə: [legal-redline-tools](https://github.com/evolsb/legal-redline-tools), [REDLINE agent](https://github.com/AaryanSehgal/redline-agent), [contract-review-pipeline](https://github.com/marvelousorimoloye-hub/contract-review-pipeline), [redline-buddy](https://github.com/dhruv1220/redline-buddy), [Ally](https://github.com/Azure-Samples/ally-legal-assistant), [redline-llm](https://github.com/MarcusElwin/redline-llm), [contract-review-agent](https://github.com/kogunlowo123/contract-review-agent)
- Kitabxanalar: [docx-redline](https://github.com/gh-aswanth/docx_walking), [Adeu](https://github.com/dealfluence/adeu), [Python-Redlines](https://github.com/JSv4/Python-Redlines), [docx-revisions](https://github.com/balalofernandez/docx-revisions), [docx-editor](https://github.com/pablospe/docx-editor)
- Tədqiqat: [Stanford — Hallucination-Free?](https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf), [LawNext — Stanford redo](https://www.lawnext.com/2024/06/in-redo-of-its-study-stanford-finds-westlaws-ai-hallucinates-at-double-the-rate-of-lexisnexis.html), [Hallucinated citations in the wild](https://arxiv.org/pdf/2605.07723), [LawGeex](https://www.artificiallawyer.com/2018/02/26/lawgeex-hits-94-accuracy-in-nda-review-vs-85-for-human-lawyers/), [CUAD](https://www.atticusprojectai.org/cuad/)
- Azərbaycan: [E-Qanun.ai](https://www.e-qanun.ai/), [Ədliyyə Nazirliyi](https://justice.gov.az/en/digital-justice/e-qanunai), [Mincom](https://mincom.gov.az/en/media-en/news/e-qanunai-platform-officially-presented), [YOXLA](https://github.com/LocalDoc-Azerbaijan/yoxla), [allmalab/eqanun](https://huggingface.co/datasets/allmalab/eqanun), [LocalDoc](https://github.com/LocalDoc-Azerbaijan)
