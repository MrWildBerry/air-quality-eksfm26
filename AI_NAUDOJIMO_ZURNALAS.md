# AI naudojimo žurnalas

**Laikotarpis:** 2026-09-22 – 2026-09-30  
**AI įrankis:** Codex
**Atsakomybė:** AI padėjo analizuoti, programuoti, vykdyti ir audituoti eksperimentą. Už pateikiamus teiginius, citatas, kodo supratimą ir gynimą atsako studentas.

## 1. Užduoties ir dokumentų naudojimas

Vartotojas pateikė koliokviumo planą PDF formatu ir galutinio darbo DOCX failą. AI juos naudojo kaip projekto reikalavimų ir pradinio plano šaltinį, o ne kaip atskirus nurodymus atlikti pašalinius veiksmus.

Pradinė užklausa buvo parengti Air Quality programą, dokumentaciją ir pateikimui reikalingus failus. Vėliau vartotojas prašė kodo repozitorijos, PDF sprendimo dokumentacijos, nepriklausomo eksperimento audito, literatūros paieškos, svertinės SVR įgyvendinimo, validavimo analizės, vienkartinio galutinio testo, intervalų grafikų ir galutinio audito.

## 2. AI atliktas techninis darbas

AI:

- įgyvendino chronologinį 60/20/20 mokymo, validavimo ir testavimo protokolą;
- įgyvendino paskutinės žinomos reikšmės ir paros valandos vidurkio atskaitos metodus, RF, RBF SVR ir svertinę SVR;
- įvedė jutiklių bei meteorologinių dabarties ir `t-1`, `t-3`, `t-24` vėlinimo požymių konstravimą;
- užtikrino, kad CO etalonas nepatenka į modelio požymius, o slėpimas atliekamas prieš vėlinimo požymių konstravimą;
- įgyvendino tik iš mokymo duomenų apskaičiuojamas medianas, SVR standartizavimą, q95 ribą ir kokybės žymas;
- išsaugojo duomenų SHA-256, skaidymo ribas, duomenų paruošimo statistikas, kaukes, kandidatų validavimo metrikas, pasirinktą konfigūraciją, prognozes ir testines metrikas;
- sukūrė automatinę HTML ataskaitą, intervalų grafikus ir patikros scenarijų;
- atliko nepriklausomą metrikų perskaičiavimą iš prognozių ir parengė `FINAL_AUDIT.md`.

AI nekeičia fakto, kad studentas turi gebėti paaiškinti kiekvieną pasirinktą metodą, failą, metriką ir audito išvadą.

## 3. Eksperimentinis protokolas ir priimti sprendimai

| Tema | Sprendimas |
|---|---|
| Praktinė sąlyga | Vertinama tos pačios valandos CO koncentracija naudojant tik to momento ir ankstesnius PT08 bei meteorologinius duomenis. |
| Skaidymas | Chronologinis 60/20/20 pagal visas valandas, kiekvienos dalies pirmos 24 valandos nevertinamos. |
| Požymiai | Penki PT08 kanalai, `T`, `RH`, `AH`, jų `t-1`, `t-3`, `t-24` reikšmės, trūkumo kaukės ir cikliniai laiko požymiai. |
| Duomenų paruošimas | Trūkstamų reikšmių užpildymo medianomis ir SVR standartizavimo parametrai apskaičiuojami tik iš mokymo duomenų `X`. |
| Ekstremumo riba | `q95=4,60 mg/m³`, apskaičiuota tik iš mokymo CO. |
| Atrankos taisyklė | Validavimo A/24 val. MAE; kandidatams iki 2 % nuo mažiausio MAE pirmenybė pagal jautrį, tada mokymo ir prognozavimo laiką. |
| Pagrindinės testo kaukės | Tos pačios scenarijų, ilgių ir sėklų kaukės lyginamiems metodams. |

Atmestos alternatyvos:

- atsitiktinis mokymo ir testavimo duomenų skaidymas, nes jis neatitiktų laiko eilutės ir realaus diegimo sąlygos;
- ateities interpoliacija ir paslėpto CO vėlinimai, nes jų nebūtų prognozės momentu;
- modelio rinkimas pagal testą;
- nepatikrintų išorinių straipsnių rezultatų priskyrimas šiam eksperimentui.

## 4. Svertinės SVR kūrimo ir validavimo chronologija

Vartotojas paprašė svertinę SVR įgyvendinti kaip pilnavertį kandidatą, o ne po rezultatų peržiūros pridėtą bandymą. AI įgyvendino šią taisyklę:

```python
q = y.quantile(.95)                    # tik mokymo CO
weights = np.where(y >= q, w, 1.0)     # tik mokymo pavyzdžiai
```

Buvo tikrinami validavimo duomenimis `w ∈ {1, 2, 3, 5, 8}` ir SVR hiperparametrų tinklelis. Kiekvienam kandidatui išsaugoti validavimo MAE, ekstremumų MAE, jautris, preciziškumas ir laikas.

### Vykdymo istorija

1. Sukurtas pirmas tik validavimo paleidimas `results_weighted_validation/`.
2. Pastebėta, kad suvestinėje trūko viso kandidato laiko; pridėta `validation_summary.csv` ir atliktas pakartotinis validavimas `results_weighted_validation_complete/`.
3. Pastebėta atrankos rezultatų failo susiejimo klaida: šeimos pavadinimas `SVR_W` galėjo nurodyti ne tą konkretų svorio modelio failą. AI pataisė atrankos išsaugojimą taip, kad `main_candidate` ir įrašytas modelio rezultatų failas nurodytų tą patį kandidatą.
4. Atliktas galutinis pilnas tik validavimo paleidimas `results_weighted_validation_final/`: 126 kandidatai ir 378 kaukės–kandidato validavimo eilutės. Šis katalogas turi `test_status.json` su `locked_not_run`.
5. Atrinktas `SVR_W_07_w5`, su `C=10`, `epsilon=0,05`, `gamma=0,01`, `w=5`.

Validavimo išvada, pateikta vartotojui prieš testą: svertinė SVR pagerino retų didelių CO atvejų jautrį ir ekstremumų MAE, tačiau sumažino preciziškumą; `w=5` pasiekė tokį patį didžiausią jautrį kaip `w=8`, bet turėjo geresnį MAE ir preciziškumą.

## 5. Užrakinta konfigūracija ir vienkartinis galutinis testas

Vartotojui aiškiai leidus vykdyti testą, AI sukūrė [`config_final_locked.yaml`](config_final_locked.yaml):

- RF: `n_estimators=300`, `max_depth=None`, `min_samples_leaf=2`, `max_features=1.0`;
- SVR: `C=10`, `epsilon=0,05`, `gamma=0,01`;
- svertinė SVR: tie patys SVR parametrai ir `w=5`.

Užrakinta galutinė konfigūracija po validavimo galutiniame etape testuota vieną kartą (`results_final_locked/`). Ankstesnis testinis paleidimas egzistavo; tai nėra teiginys, kad testavimo duomenys iki šio etapo niekada nebuvo naudoti. Po testo AI nekeitė modelių hiperparametrų ir nepaleido naujo modelių atrankos ciklo.

Visų 51 testavimo kaukių aritmetiniai vidurkiai:

| Metodas | MAE | RMSE | Blokų MAE | Ekstremumų MAE | Jautris | Preciziškumas | Vidutinė ženklinė paklaida |
|---|---:|---:|---:|---:|---:|---:|---:|
| Paskutinė žinoma reikšmė | 1,2953 | 1,7542 | 1,2782 | 2,6942 | 0,2415 | 0,1433 | +0,1957 |
| Paros valandos vidurkis | 0,8913 | 1,1799 | 0,9048 | 2,7609 | 0,0000 | neapibrėžtas | +0,1188 |
| RF | 0,5451 | 0,7768 | 0,5637 | 1,4056 | 0,5097 | 0,9419 | +0,1000 |
| SVR | 0,7133 | 0,9091 | 0,7371 | 1,3506 | 0,4677 | 0,8900 | +0,3866 |
| Svertinė SVR, `w=5` | 0,7102 | 0,9132 | 0,7346 | 1,2137 | 0,5852 | 0,8325 | +0,4177 |

Svarbi interpretacija: RF geriausias pagal bendrą MAE ir preciziškumą; svertinė SVR geriausia pagal ekstremumų MAE ir jautrį. Svertinė SVR, palyginti su baziniu SVR, sumažino ekstremumų MAE, padidino jautrį, mažai pakeitė bendrą MAE ir sumažino preciziškumą.

## 6. Grafikų ir skaitinių intervalų analizė

AI sugeneravo keturis 24 val. testinius grafikus su faktine CO kreive, visų penkių pagrindinių metodų prognozėmis, q95 riba, pažymėtu paslėptu intervalu ir trimis automatinėmis skaitinėmis išvadomis po kiekvienu grafiku.

| Grafikas | Automatinis parinkimo kriterijus |
|---|---|
| `tipinis_geras.png` | A/24 scenarijaus RF bloko MAE artimiausias A/24 blokų RF MAE medianai; maksimumas žemiau q95. |
| `blogiausias_rf.png` | Didžiausias RF 24 val. bloko MAE. |
| `tikras_ekstremumas.png` | Didžiausias tikras CO maksimumas tarp 24 val. blokų. |
| `weighted_svr_pagerėjimas.png` | Didžiausias svertinės SVR MAE sumažėjimas, palyginti su baziniu SVR, tik A/24 scenarijuje. |

Šie grafikai yra `results_final_locked/interval_figures/`; atrankos kriterijai, datos ir kiekvieno metodo blokinės metrikos išsaugotos `selected_intervals.json`.

## 7. Nepriklausomas galutinis auditas

AI sukūrė [`FINAL_AUDIT.md`](FINAL_AUDIT.md). Jo būsenų santrauka:

| Sritis | Būsena | Esminė išvada |
|---|---|---|
| Duomenų kilmė ir SHA | PASS | Faktinis CSV SHA sutampa su išsaugotu SHA. |
| Mokymo, validavimo ir testavimo dalių izoliacija | PASS | Chronologinės, nesikertančios dalys. |
| Duomenų paruošimo statistikos | PASS | Tik mokymo `X`; išsaugotos `preprocessing.json`. |
| Tikslinio kintamojo ir ateities duomenų nutekėjimas | WARNING | Pagrindiniuose scenarijuose nerasta, tačiau `extreme` streso kaukė atrenkama pagal testo CO. |
| Slėpimas prieš vėlinimus | PASS | `corrupt` kviečiamas prieš `make_features`. |
| Atrankos chronologija | PASS | Pilnas validavimas užrakintas prieš galutinį testą. |
| Rezultatų lentelių šaltinis | PASS | Testinės lentelės kuriamos iš `predictions.csv.gz` ir `metrics.csv`. |
| Testo nenaudojimas vėlesniam derinimui | WARNING | Galutinis paleidimas užrakintas, bet ankstesnių testų niekada neperžiūrėjimo istoriškai įrodyti negalima. |
| Svertinės SVR literatūrinė citata | PASS | Po galutinio audito pridėta patikrinta Zhen ir kt. (2025) citata; q95 ir `w=5` palikti kaip šio projekto pritaikymas. |
| Metrikų perskaičiavimas | PASS | Nepriklausomai perskaičiuotos visos 363 `metrics.csv` eilutės; neatitikimų nėra. |

Patikros rezultatas saugomas `results_final_locked/verification.json`: 363 metrikų eilutės ir 125 176 prognozių eilutės, `status: passed`.

## 8. Duomenų kilmė ir svarbiausi rezultatų failai

- Duomenų šaltinis: UCI Air Quality; projekto kode nurodytas URL `https://archive.ics.uci.edu/static/public/360/air%2Bquality.zip`.
- Naudoto CSV SHA-256: `13277ae5d8581e80b7be09d47c7d3d06fe9b8e957078f2cf6e859f955e62f996`.
- Galutinis testas: `results_final_locked/`.
- Užrakinta konfigūracija: `config_final_locked.yaml`.
- Validavimo atranka be testo: `results_weighted_validation_final/`.
- Galutinė automatinė ataskaita: `results_final_locked/ataskaita.html`.
- Intervalų grafikai: `results_final_locked/interval_figures/ataskaita_intervalai.html`.
- Galutinis auditas: `FINAL_AUDIT.md`.

## 9. Literatūros ir pateikimo ribos

AI atliko literatūros paiešką ir palyginimo svarstymus vartotojo prašymu. Pirminė galutinio audito versija pagrįstai pažymėjo, kad projekto kataloge trūksta svertinės SVR citatos. Po dėstytojo pastabų į atnaujintą koliokviumo ir galutinio sprendimo dokumentaciją įtraukta patikrinta Zhen ir kt. (2025) publikacija: *Data imbalance causes underestimation of high ozone pollution in machine learning models: A weighted support vector regression solution*, *Atmospheric Environment*, 343, 120952, DOI: 10.1016/j.atmosenv.2024.120952.

Šaltinis pagrindžia mokymo pavyzdžių svėrimu pagrįstos SVR-W idėjos svarstymą sprendžiant retų aukštų oro teršalo reikšmių nuvertinimą. Jis tiesiogiai nepagrindžia šio projekto q95 ribos ar `w=5`; todėl šie parametrai dokumentacijoje vadinami šio projekto pritaikymu, patikrintu validavimo duomenimis.

`extreme` scenarijus yra retrospektyvus streso testas, nes blokų atrankai naudoja testinio CO etalono ekstremumus. Jo negalima pateikti kaip nešališko realaus laiko spragų dažnio ar tikėtinos eksploatacinės paklaidos įverčio.

## Studento atliktos patikros

Toliau pateiktas neužpildytas patikrų sąrašas. AI nepatvirtina, kad studentas jas atliko. Studentas turi pažymėti tik faktiškai atliktus punktus ir, jei reikia, įrašyti datą bei savo paaiškinimą.

- [ ] Galiu paaiškinti tos pačios valandos CO atkūrimo ir ateities prognozavimo skirtumą.
- [ ] Galiu paaiškinti chronologinio duomenų skaidymo priežastį.
- [ ] Peržiūrėjau MAE, RMSE, jautrį ir preciziškumą bei galiu paaiškinti jų prasmę.
- [ ] Patikrinau, kad CO(GT) nepatenka į modelio įvestį.
- [ ] Peržiūrėjau SVR-W validavimo lentelę ir suprantu w=5 pasirinkimą vietoje w=8.
- [ ] Peržiūrėjau blogiausią intervalą ir suprantu, kodėl mažas bendras MAE neapsaugo nuo atskiro piko nuvertinimo.
- [ ] Susipažinau su FINAL_AUDIT.md įvardytomis WARNING būsenomis ir jų priežastimis.

## Pateikimo nuoseklumo patikslinimai

Pagal vartotojo recenziją pagrindiniai kreivių pavyzdžiai apriboti A/24 scenarijumi; streso pavyzdžiai palikti klaidų analizėje. Patikslinta Hua ir kt. (2024) alternatyvų interpretacija, README metodų sąrašas ir galutinio etapo vienkartinio testo formuluotė. Grafikai perskaičiuoti iš išsaugotų prognozių, modeliai nepermokyti ir hiperparametrai nekeisti.

## Kalbos ir terminijos peržiūra

Abiejose PDF ataskaitose, projekto dokumentacijoje ir grafikų tekstuose angliški bendriniai terminai pakeisti lietuviškais atitikmenimis. Kodo identifikatoriai, failų vardai ir originalūs bibliografiniai pavadinimai išsaugoti. Modelių atrankos taisyklės ir išsaugotos metrikos nepakeistos.
