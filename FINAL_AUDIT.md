# Galutinis nepriklausomas auditas

**Apimtis.** Audituotas pateikimui skirtas vienkartinis paleidimas `results_final_locked/`, jo šaltinio kodas ir ankstesnis tik-validavimo artefaktas `results_weighted_validation_final/`. Vertinami tik išsaugoti kodas ir artefaktai.

| Tikrinamas punktas | Būsena | Trumpa išvada |
|---|---|---|
| Duomenų kilmė ir SHA | **PASS** | Išsaugotas ir iš naujo sutampantis SHA-256; nurodytas oficialus UCI URL. |
| Train / validation / test izoliacija | **PASS** | Chronologinės, nesikertančios 60/20/20 dalys; mokymas ir atranka iki testo. |
| Preprocessing statistikos | **PASS** | Medianų, vidurkių ir skalių šaltinis yra tik mokymo `X`; statistikos išsaugotos. |
| Target ir future leakage | **WARNING** | Pagrindiniuose scenarijuose jo nerasta, bet `extreme` testo kaukė parenkama pagal testo CO etaloną. |
| Maskavimas prieš lag kūrimą | **PASS** | Testui ir validavimui pirma kuriamas `visible`, po to lag požymiai. |
| Modelių atrankos chronologija | **PASS** | Pilna atranka baigta validavime ir `w=5` užfiksuotas prieš galutinį testą. |
| Rezultatų lentelių duomenų šaltinis | **PASS** | `metrics.csv` ir `summary.csv` kuriami iš testinių prognozių; validavimo lentelės atskiros. |
| Testas nebuvo vėliau naudotas derinimui | **WARNING** | Po galutinio testo naujo derinimo artefakto nėra, bet ankstesnis testinis katalogas ir nekintamos istorijos nebuvimas neleidžia įrodyti neigiamo teiginio absoliučiai. |
| Modifikuoto metodo literatūrinis pagrindas | **PASS** | Pridėta patikrinama Zhen ir kt. (2025) citata; q95 ir `w=5` aiškiai nurodyti kaip šio projekto adaptacija. |
| Metrikų perskaičiavimas iš prognozių | **PASS** | Visos 363 `metrics.csv` eilutės perskaičiuotos iš `predictions.csv.gz` be neatitikimų. |

## 1. Duomenų kilmė ir SHA — PASS

**Įrodymai.** Oficialus šaltinis užkoduotas [`airquality/load.py:13`](airquality/load.py#L13), atsisiunčiamas tik iš šio URL [`airquality/load.py:15-25`](airquality/load.py#L15-L25), o įvesties CSV SHA-256 apskaičiuojamas iš faktinių baitų [`airquality/load.py:56-60`](airquality/load.py#L56-L60).

Galutinio paleidimo [`results_final_locked/data_audit.json`](results_final_locked/data_audit.json) reikšmė yra:

```text
SHA-256 = 13277ae5d8581e80b7be09d47c7d3d06fe9b8e957078f2cf6e859f955e62f996
URL     = https://archive.ics.uci.edu/static/public/360/air%2Bquality.zip
```

Audito metu perskaičiuotas lokalaus `data/AirQualityUCI.csv` SHA-256 yra toks pats. [`results_final_locked/verification.json`](results_final_locked/verification.json) taip pat fiksuoja `sha256_match: true`.

## 2. Train / validation / test izoliacija — PASS

**Įrodymai.** Skaidymas atliekamas pagal visas chronologines eilutes, prieš filtruojant žinomus CO taikinius: [`airquality/split.py:4-12`](airquality/split.py#L4-L12). Galutiniame paleidime išsaugotos nesikertančios ribos:

| Dalis | Laikotarpis | Valandos | Žinomi CO po 24 val. warm-up |
|---|---|---:|---:|
| train | 2004-03-10 18:00 – 2004-10-30 15:00 | 5 614 | 4 153 |
| validation | 2004-10-30 16:00 – 2005-01-16 14:00 | 1 871 | 1 694 |
| test | 2005-01-16 15:00 – 2005-04-04 14:00 | 1 872 | 1 757 |

Šaltinis: [`results_final_locked/split.json`](results_final_locked/split.json). Mokymo `X` ir `y` imami tik iš `train` [`run_experiment.py:61-66`](run_experiment.py#L61-L66). Validavimas naudoja tik `validation` [`run_experiment.py:73-78`](run_experiment.py#L73-L78), o testas pradedamas tik po atrankos ir modelių išsaugojimo [`run_experiment.py:145-176`](run_experiment.py#L145-L176).

## 3. Visos preprocessing statistikos — PASS

**Įrodymai.** `Prepare.fit` medianas, vidurkius ir standartinius nuokrypius apskaičiuoja iš perduoto mokymo `X` [`airquality/features.py:29-37`](airquality/features.py#L29-L37); `transform` tik naudoja jau išmoktas reikšmes [`airquality/features.py:39-44`](airquality/features.py#L39-L44). Pipeline `Prepare` įdeda prieš modelį [`airquality/models.py:8-14`](airquality/models.py#L8-L14), todėl validavimo ir testo metu jis nefitinamas iš naujo.

[`results_final_locked/preprocessing.json`](results_final_locked/preprocessing.json) turi po 32 medianas, 32 vidurkius ir 32 skales kiekvienam iš `RF`, `SVR` ir `SVR_W`; nėra tuščių matavimo stulpelių. Iš viso modeliai turi 68 požymius: 32 dabarties ir lag matavimus, 32 trūkumo kaukes ir 4 kalendorinius požymius. Mokymo q95, baseline būsena, jutiklių min/max ir S1 standartinis nuokrypis taip pat skaičiuojami tik iš `train` [`run_experiment.py:66-70`](run_experiment.py#L66-L70).

## 4. Target ir future leakage — WARNING

**Pagrindiniai scenarijai: PASS.** Į modelio požymius patenka tik penki PT08 jutikliai ir meteorologija, ne `CO(GT)` [`airquality/load.py:10-12`](airquality/load.py#L10-L12) ir [`airquality/features.py:7-22`](airquality/features.py#L7-L22). Lagai yra tik `t-1`, `t-3` ir `t-24` [`airquality/features.py:10-14`](airquality/features.py#L10-L14), todėl požymių konstravime nėra `t+k`. Tikras `CO(GT)` į `frame_for` patenka tik po prognozės, metrikoms apskaičiuoti [`run_experiment.py:79-83`](run_experiment.py#L79-L83).

**Išimtis: WARNING.** `extreme` scenarijaus blokų pradžios atrenkamos pagal testo `CO(GT) >= q95` [`airquality/masks.py:11-12`](airquality/masks.py#L11-L12). Tai nėra įvesties ar mokymo leakage ir nedalyvauja atrankoje, tačiau tai yra retrospektyvus, target-conditioned streso testas. Jo metrikų negalima pateikti kaip nešališko realaus laiko spragų pasiskirstymo įverčio. Ataskaita tai vadina „retrospektyviu streso testu“ [`airquality/report.py:140`](airquality/report.py#L140), bet jo eilutės vis tiek yra bendrame `metrics.csv`.

## 5. Maskavimas prieš lag kūrimą — PASS

**Įrodymai.** `corrupt` pirmiausia paslepia CO ir, priklausomai nuo scenarijaus, jutiklius [`airquality/masks.py:24-34`](airquality/masks.py#L24-L34). Tada validavimui kviečiamas `make_features(visible)` [`run_experiment.py:75-78`](run_experiment.py#L75-L78), o testui — taip pat po `corrupt` [`run_experiment.py:183-185`](run_experiment.py#L183-L185). Todėl paslėpto jutiklio `t` reikšmė negali patekti į `t+1`, `t+3` ar `t+24` lag požymį.

## 6. Modelių atrankos chronologija — PASS

**Įrodymai.** Pilnas kandidatų tinklelis, įskaitant `w ∈ {1,2,3,5,8}`, validuojamas [`run_experiment.py:95-130`](run_experiment.py#L95-L130). Atrankos taisyklė — MAE iki 2 % nuo geriausio, tada recall ir laikas — realizuota [`airquality/evaluate.py:28-37`](airquality/evaluate.py#L28-L37). Atranka įrašoma prieš testinį ciklą [`run_experiment.py:135-146`](run_experiment.py#L135-L146).

Pilnas, testą užrakinęs validavimo artefaktas [`results_weighted_validation_final/selection.json`](results_weighted_validation_final/selection.json) pasirinko `SVR_W_07_w5`, `C=10`, `epsilon=0.05`, `gamma=0.01`, `w=5`. To paleidimo [`test_status.json`](results_weighted_validation_final/test_status.json) fiksuoja `locked_not_run`. Galutinis [`config_final_locked.yaml`](config_final_locked.yaml) turi būtent šias vieninteles RF, SVR ir `w=5` reikšmes; galutinio testo [`results_final_locked/selection.json`](results_final_locked/selection.json) pasirinkimas atitinka jas.

## 7. Ar rezultatų lentelėse naudojamas tik testas — PASS

**Įrodymai.** Testinės prognozės rašomos į `predictions.csv.gz`, o testinės metrikos į `metrics.csv` [`run_experiment.py:201-212`](run_experiment.py#L201-L212). Ataskaitos generatorius `metrics.csv` ir `predictions.csv.gz` perskaito tiesiogiai [`airquality/report.py:21-31`](airquality/report.py#L21-L31), o `summary.csv` generuoja tik grupuodamas `metrics.csv` [`airquality/report.py:29-31`](airquality/report.py#L29-L31).

Validavimo metrikos saugomos atskirai kaip [`results_final_locked/validation_metrics.csv`](results_final_locked/validation_metrics.csv) ir nenaudojamos rezultatų lentelėms. Išimtis tik semantinė: `selection.json` ir ataskaitos tekstas nurodo validavimo atrankos rezultatą; tai nėra testinė metrika.

## 8. Ar testas nebuvo naudotas vėlesniam parametrų derinimui — WARNING

**Teigiami įrodymai.** Galutinis testas buvo paleistas su jau užrakinta [`config_final_locked.yaml`](config_final_locked.yaml); po jo kataloge nėra naujo kandidato, naujos validavimo suvestinės ar nebaigtų bandymų ([`results_final_locked/incomplete.json`](results_final_locked/incomplete.json) yra `[]`). Galutinio modelio parametrai sutampa su testą užrakinusio validavimo sprendimu, kaip nurodyta 6 skyriuje.

**Kodėl ne PASS.** Neigiamo istorinio teiginio „testas niekada nebuvo naudotas“ negalima įrodyti vien darbo katalogu. Jame yra ankstesnis pilnas [`results/`](results/) testinis paleidimas su `predictions.csv.gz`, `metrics.csv` ir `ataskaita.html`, bet nėra pasirašyto Git commit, nekintamo žurnalo ar nuotolinio CI įrodymo, kuris neleistų jo peržiūrėti prieš vėlesnį dizaino sprendimą. Galutinės konfigūracijos testas yra tvarkingai užfiksuotas, tačiau griežtam pateikimui studentas neturėtų teigti, kad ankstesni testai buvo nepasiekiami.

## 9. Modifikuoto metodo literatūrinė citata — PASS

**Įrodymai.** Weighted SVR įgyvendinimas techniškai aiškus: q95 skaičiuojamas tik iš mokymo `y`, o svoriai taikomi tik mokymo pavyzdžiams [`run_experiment.py:61-66`](run_experiment.py#L61-L66) ir [`run_experiment.py:95-107`](run_experiment.py#L95-L107); `sample_weight` perduodamas SVR pipeline [`airquality/train.py:12-18`](airquality/train.py#L12-L18).

Atnaujintoje koliokviumo ir galutinio sprendimo dokumentacijoje pateikta patikrinama pirminė citata: Zhen, L., Chen, B., Wang, L., Yang, L., Xu, W., Huang, R.-J. (2025). *Data imbalance causes underestimation of high ozone pollution in machine learning models: A weighted support vector regression solution*. *Atmospheric Environment*, 343, 120952. DOI: [`10.1016/j.atmosenv.2024.120952`](https://doi.org/10.1016/j.atmosenv.2024.120952).

Straipsnis pagrindžia oro teršalų aukštų reikšmių nuvertinimo ir sample-weighting pagrįstos SVR-W idėją. Jis **nepagrindžia tiesiogiai** šio projekto konkretaus `q95` slenksčio ar `w=5`; tai yra projekto adaptacija, kurios parametrai pasirinkti tik validavimo duomenimis. Šis skirtumas aiškiai nurodytas abiejuose atnaujintuose PDF dokumentuose.

## 10. Ar metrikos perskaičiuojamos iš `predictions` — PASS

**Įrodymai.** Metrikų formulės apibrėžtos [`airquality/evaluate.py:6-20`](airquality/evaluate.py#L6-L20). Audito metu iš [`results_final_locked/predictions.csv.gz`](results_final_locked/predictions.csv.gz) nepriklausomai perskaičiuotos `n`, `blocks`, MAE, blokų MAE, RMSE, TP, FN, FP, recall, precision, extreme MAE, extreme bias, `warning_fraction` ir `clipped_fraction` visoms 363 `metrics.csv` eilutėms. Neatitikimų: **0**.

Papildomai [`verify_results.py:12-55`](verify_results.py#L12-L55) atskirai patikrina SHA, testo laikotarpį, neigiamas/NaN prognozes, MAE, blokų MAE ir A scenarijaus kaukių atkūrimą. Jo galutinis rezultatas [`results_final_locked/verification.json`](results_final_locked/verification.json) fiksuoja `status: passed`, 363 patikrintas metrikų eilutes ir 125 176 prognozių eilutes. Visų penkių pagrindinių metodų testinės laiko žymos kiekvienai kaukei taip pat sutampa.

## Išvada pateikimui

Galutinio paleidimo skaičiai yra atkartojami iš išsaugotų prognozių, o preprocessing ir pagrindinių scenarijų laiko protokolas neturi nustatyto target ar future leakage. Pateikimo teiginius būtina apriboti dviem WARNING: `extreme` scenarijus yra retrospektyvus target-conditioned streso testas, o visiško testų neperžiūrėjimo istoriškai įrodyti negalima. Svertinės SVR idėja turi patikrinamą literatūrinį pagrindą, tačiau `q95` ir `w=5` turi būti vadinami šio projekto validuota adaptacija.

