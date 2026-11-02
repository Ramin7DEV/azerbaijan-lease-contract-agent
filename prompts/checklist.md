<!-- Hər iddia data/law/icare.txt ilə üzləşdirilib. B cədvəli agent/law.py-dakı IMPERATIVE ilə eyni olmalıdır. -->

# İcarə müqaviləsi üçün yoxlama siyahısı

## A. Mütləq olmalı bəndlər

`siyahi` sahəsində bu 11 mövzunun hər birini, eyni adla və bu ardıcıllıqla, yoxla. Mövzu müqavilədə yoxdursa və ya çox natamamdırsa, `catismayan` tapıntısı yarat.

1. **Tərəflər** — ad, VÖEN / şəxsiyyət vəsiqəsi, ünvan.
2. **Predmet** — əmlakın ünvanı, sahəsi, təyinatı (yaşayış / qeyri-yaşayış) (Maddə 675, 700.2).
3. **İcarə haqqı** — məbləğ, ödəniş günü və qaydası. Yoxdursa, haqq hər ayın sonunda ödənilir (684.1).
4. **Müddət** — başlama və bitmə tarixi. Yoxdursa, istənilən tərəf bildirişlə ləğv edə bilər (689.2).
5. **Təhvil-təslim** — əmlakın verildiyi andakı vəziyyəti, akt. Qüsuru sübut etmək üçün lazımdır (677.2).
6. **Kommunal xərclər və vergilər** — kim ödəyir. Razılaşma yoxdursa, vergi və yüklülükləri icarəyə verən ödəyir (679).
7. **Təmir** — cari və əsaslı təmir kimin üzərindədir (676, 680).
8. **Ləğvetmə qaydası** — əsaslar, yazılı bildiriş, xəbərdarlıq müddəti (690, 691).
9. **Əmlakın qaytarılması** — vaxt və vəziyyət (697).
10. **Fors-major** — qanunun bu fəsillərində maddə yoxdur, `madde_no` = null.
11. **Mübahisələrin həlli** — qanunun bu fəsillərində maddə yoxdur, `madde_no` = null.

## B. İmperativ normalar — bunlara zidd bənd QANUNA ZİDDDİR (qüvvəsi yoxdur)

`qanuna_zidd` tipi YALNIZ bu cədvəldəki normalara istinadla verilir və yalnız "Kimə aiddir" sütunu əmlak növünə uyğun gələndə. `madde_no` kimi cədvəldəki nömrəni yaz.

| Norma | Nəyi qadağan edir | Kimə aiddir |
|---|---|---|
| 677.4 | İcarəyə verən qüsuru bilə-bilə gizlədibsə, onu məsuliyyətdən azad edən və ya məsuliyyəti məhdudlaşdıran şərt | hamı |
| 686 | Ağır təqsirli pozuntuda xəbərdarlıqsız ləğv hüququnu istisna edən şərt (otaqlar) | hamı |
| 691.3 | İcarəyə verənin gözləməli olduğu xəbərdarlıq müddətini qanundakından (691.1.3, 691.2) qısaldan şərt | hamı |
| 691.2 | Yaşayışda ləğv bildirişi növbəti aydan sonrakı ayın sonu üçün verilməlidir; icarəyə verən üçün daha qısa müddət (məs. 3 gün, 10 gün) | yaşayış |
| 695 | Kirayəçi öləndə ailə üzvlərinin / vərəsələrin müqaviləni davam etdirmək hüququnu istisna edən şərt | hamı |
| 677.1.1 | Qüsur dövründə də icarə haqqının tam ödənilməsi | yaşayış |
| 677.1.4 | Qüsura görə kirayəçinin ləğv hüququnu istisna edən şərt | yaşayış |
| 678 | Əsaslı təmir tədbirlərində kirayəçinin hüquqlarını (3 ay əvvəl bildiriş, xərclərin əvəzi) azaldan şərt | yaşayış |
| 681 | Kirayəçinin öz qurğularını götürmək hüququnu istisna edən şərt | yaşayış |
| 683.2 | Otağın bir hissəsini subicarəyə vermək hüququnu kirayəçinin ziyanına dəyişən şərt | yaşayış |
| 687 | İcarəyə verənə qanundan kənar əsaslarla dərhal ləğv hüququ verən şərt, o cümlədən: səbəbsiz ləğv; ödəniş gecikməsinə görə 685.2 və 685.4-dən sərt şərtlə ləğv (məs. bir neçə gün gecikmə); əmlak satılanda müqavilənin xitamı | yaşayış |
| 688 | Təminat 2 aylıq haqqdan çox və ya faizsiz / bankda ayrıca saxlanmadan (688.2, 688.3); bron haqqı qaydası (688.1); dəbbə pulu (688.4) | yaşayış |
| 692 | İcarəyə verənin əsaslı marağı olmadan ləğvi; satış niyyəti əsas deyil (692.2.3); kirayəçinin ziyanına kənaraçıxma (692.8) | yaşayış |
| 693 | Müddətli müqavilənin uzadılması hüququnu kirayəçinin ziyanına dəyişən şərt | yaşayış |
| 696 | Kirayəçinin ləğvə etiraz hüququnu istisna edən şərt | yaşayış |

**Vacib:** yaşayış müqaviləsində "ödəniş gecikməsində dərhal ləğv" və "satışda müqavilə bitir" şərtləri üçün `madde_no` = "687" yaz, 685.2 və ya 699.1 yox. Bunlar C cədvəlindəki standart qaydalardır, qadağa isə 687-dədir.

## C. Dispozitiv normalar — bunlardan kənaraçıxma BİRTƏRƏFLİDİR, qanuna zidd deyil

Qanun bu qaydaları standart kimi müəyyən edir, amma tərəflərin başqa cür razılaşmasını qadağan etmir. Belə bənd `birterefli` olur, `madde_no` isə standart qaydanı göstərir ki, vəkil fərqi görsün. C cədvəlinə istinad edən tapıntı HEÇ VAXT `qanuna_zidd` olmur.

| Norma | Standart qayda |
|---|---|
| 682 | İcarəçi adi istifadədən yaranan köhnəlməyə görə məsuliyyət daşımır |
| 699.1 | Əmlak satılanda yeni mülkiyyətçi müqavilənin tərəfi olur, müqavilə davam edir (yaşayışda qadağa üçün bax 687) |
| 685.2 | Ödəniş gecikməsinə görə dərhal ləğv yalnız 2 ardıcıl müddət gecikmədə (yaşayışda qadağa üçün bax 687) |
| 680.1 | İcarəyə verən saxlama/bərpa üçün zəruri xərclərin əvəzini ödəyir |
| 676 | İcarəyə verən əmlakın yararlı vəziyyətdə olmasına cavabdehdir |
| 688.2 | Qeyri-yaşayış üçün: təminat 2 aylıqdan çox olmamalı, bankda faizlə saxlanmalıdır — standart qayda |
| 691.1.3 | Qeyri-müəyyən müddətli otaq kirayəsində ləğv bildirişi növbəti aydan sonrakı ayın sonu üçün |

## D. Tipik birtərəfli şərtlər (maddəsiz də ola bilər)

- İcarə haqqının bir tərəf tərəfindən, həddi olmadan artırılması.
- Yalnız bir tərəf üçün cərimə, xüsusilə qalan bütün müddətin haqqı qədər.
- Əsaslı təmirin icarəçiyə yüklənməsi.
- İcarəyə verənin xəbərsiz yoxlama hüququ.
- Bir tərəfin istənilən vaxt, səbəbsiz ləğv hüququ (qarşı tərəfdə olmadan).
- Təminatın heç bir halda qaytarılmaması, o cümlədən vaxtından əvvəl ləğvdə təminatın cərimə kimi saxlanılması.
