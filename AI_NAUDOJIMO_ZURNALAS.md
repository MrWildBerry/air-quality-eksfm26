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

## 10. Užklausos ir AI atsakymai

Peržiūrėk visą šią repozitoriją kaip nepriklausomas ML eksperimento recenzentas. Kol kas NIEKO kode nekeisk.  
Praktinė problema: valandos t pabaigoje įvertinti tos pačios valandos CO koncentraciją, kai CO etalonas trūksta, naudojant tik tuo metu arba anksčiau prieinamus PT08 jutiklių ir meteorologinius duomenis. Ateities informacija negali būti naudojama.  
Patikrink:
1. ar techninis uždavinys kode atitinka šią problemą;
2. ar train/validation/test atskyrimas korektiškas;
3. ar nėra target leakage, future leakage ar preprocessing leakage;
4. ar hiperparametrams niekur nenaudojamas testas;
5. ar visų metodų testavimo sąlygos tikrai vienodos;
6. ar ataskaitoje pateiktos metrikos apskaičiuotos iš testavimo duomenų;
7. ar abliacijos ir papildomi bandymai nepanaudoti modelio atrankai po testo.
Kiekvienam teiginiui nurodyk konkretų failą ir kodo eilutes arba testą, kuris tai įrodo. Jei kažko įrodyti negali, aiškiai parašyk „neįrodyta“. Pabaigoje pateik tik trūkumų ir rizikų sąrašą pagal svarbą.

22:19, trečiadienis

Dirbo 6m 39s

RF ir SVR skaičiavimo grandinėje tiesioginio target, future ar preprocessing leakage neradau. Tačiau visų metodų informacinės sąlygos neatitinka tavo apibrėžto apribojimo: last naudoja ankstesnį CO etaloną.
Peržiūrėjau GitHub versiją a4a584e. Jos kodas ir PDF sutampa su tikrintomis vietinėmis kopijomis. Kodo ir rezultatų nekeičiau.
Pakartotinai praėjo 12 testų. Nepermokydamas modelių atkūriau visas 125 176 išsaugotas prognozes ir 51 scenarijaus kaukes; didžiausias prognozių skirtumas buvo 2,22 × 10⁻¹⁵. Atskirai perskaičiavau 363 metrikų eilutes.
1. Techninio uždavinio atitiktis — RF ir SVR atitinka, visas palyginimas tik iš dalies.
   Mokymo tikslas yra tos pačios eilutės CO(GT), o požymiai — dabartiniai PT08, meteorologija, jų t−1, t−3, t−24 reikšmės ir tuo metu žinomas kalendorius. Tikslas nepaslenkamas į kitą valandą. Įrodymai: run_experiment.py, 61–64 eil., features.py, 7–22 eil..
   last gauna nepaslėptus ankstesnius testo CO etalonus: run_experiment.py, 173–175 eil., baselines.py, 10–13 eil.. Tai nėra ateities nutekėjimas, bet pagal tavo dabartinę sąlygą tokia įvestis neleistina. Valandos vidurkis šios problemos neturi: jo CO statistika išmokstama tik mokymo dalyje.
   Kad visi CSV valandos t matavimai iš tikrųjų buvo prieinami būtent jos pabaigoje, neįrodyta: kodas turi matavimo laiką, tačiau neturi gavimo laiko ar vėlavimų kontrolės (load.py, 37–60 eil.).
2. Train / validation / test atskyrimas — korektiškas šiam retrospektyviam eksperimentui.
   Dalys chronologinės, nesikerta, ribos nustatomos pagal visas valandas prieš tikslinio CO filtravimą: split.py, 4–12 eil.. Mokymui atmetamos pirmos 24 valandos; validavimo ir testo kaukės prasideda ne anksčiau kaip po šio intervalo: run_experiment.py, 62–78 eil., masks.py, 5–8 eil..
   Požymiai formuojami atskirai kiekvienai daliai. Skaidymo nepriklausomumą nuo CO patvirtina test_split_not_dependent_on_target (test_protocol.py, 86–89 eil.). Faktines laiko ribas pakartotinai sutikrinau su išsaugotu auditu.
3. Nutekėjimas — pagrindiniuose modeliuose nenustatytas; streso teste yra sąmoninga etalono priklausomybė.
   - Target leakage: požymiai atrenkami iš aštuonių kanalų, be GT stulpelių; CO pakeitimas nekeičia požymių. Įrodymai: load.py, 10–12 eil., testas 20–24 eil..
   - Future leakage: vėlinimai naudojami tik atgal. Ateities matavimų pakeitimo ir paslėpto jutiklio patekimo į vėlinimus patikros: test_protocol.py, 26–43 eil..
   - Preprocessing leakage: medianos, vidurkiai ir skalės apskaičiuojami fit, o transform jų nepermoko: features.py, 29–44 eil.. Mokymo procesas gauna tik mokymo X, y: run_experiment.py, 103 eil.. Išsaugotų RF ir SVR paruošimo parametrų sutapimą su perskaičiuotais mokymo parametrais patikrinau.
   Išimtis: extreme blokams parinkti naudojamas tikras CO visame būsimame bloke (masks.py, 11–12 eil.). Tai retrospektyvi atranka pagal etaloną, ne realiu laiku įgyvendinama trūkumo taisyklė. Į modelio požymius ši informacija nepatenka.
4. Hiperparametrų atranka — dabartiniame kode testas nenaudojamas.
   Kandidatai mokomi su mokymo duomenimis ir vertinami val_cases; pagal šias metrikas išrenkami hiperparametrai ir modelio šeima: run_experiment.py, 95–129 eil.. Atrankos taisyklė apibrėžta evaluate.py, 28–37 eil..
   selection.json ir selected.joblib išsaugomi iki testo vertinimo (130–158 eil.). Iš validavimo lentelės atkūriau tą patį pasirinkimą — SVR. Tačiau kad hiperparametrų tinklelis ar taisyklė niekada ankstesniuose bandymuose nebuvo koreguoti pamačius testą, neįrodyta.
5. Vienodos testavimo sąlygos — vienodos vertinimo valandos, bet nevienoda informacija ir bandymų aprėptis.
   Viename scenarijuje kaukė ir sugadinta įvestis sukuriamos vieną kartą, paskui naudojamos visiems metodams; vertinamos tos pačios paslėptos valandos su žinomu etalonu: run_experiment.py, 165–189 eil.. Tai patvirtino ir mano rezultatų palyginimas.
   Vis dėlto last gauna papildomą CO istoriją. Be to, RF abliacijos bei papildomos sėklos vertinamos tik A ir B scenarijuose, o pagrindiniai modeliai bei SVR_W — plačiau (178 eil.). Todėl teiginys „visų metodų visos sąlygos vienodos“ būtų per platus.
6. Galutinės tikslumo metrikos — apskaičiuotos iš testo; validavimo metrikos pateiktos atskirai.
   Testo prognozės ir metrikos formuojamos iš test, tuomet išsaugomos: run_experiment.py, 184–195 eil.. Formulės yra evaluate.py, 6–20 eil.; ataskaitos suvestinė skaičiuoja vienodai svertą kaukių metrikų vidurkį (report.py, 21–35 eil.).
   Perskaičiuotos A/24 val. MAE: RF 0,390834, SVR 0,546773, hour_mean 0,910449, last 1,266649. Jos sutampa su PDF apvalintais skaičiais. PDF 6 puslapyje validavimo ir testo lentelės aiškiai atskirtos: C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Galutinis_sprendimas_D_Kublickas_EKSfm26.pdf
   Tikslumas natūraliai trūkstamo CO vietose neįrodytas: tos eilutės nevertinamos, nes nėra etalono (run_experiment.py, 79–83 eil.).
7. Abliacijos ir papildomi bandymai — šiame paleidimo kode galutinės atrankos nekeičia.
   Abliacijų hiperparametrai paimami iš validavime atrinktų versijų, o papildomos sėklos ir svoris 3 nustatyti tiesiogiai; šie modeliai mokomi dar prieš testo ciklą: run_experiment.py, 141–158 eil.. Po testo nėra pakartotinio choose ar selected.joblib pakeitimo.
   Išsaugotas selected.joblib baitais sutampa su SVR modeliu, nors RF ir RF be istorijos teste gavo mažesnę MAE. Taigi automatinio pasirinkimo pakeitimo pagal šias abliacijas nėra. Kad papildomų bandymų apimtis istoriškai nebuvo pritaikyta jau matytiems rezultatams, neįrodyta.
Trūkumai ir rizikos pagal svarbą:
1. Aukšta — last neatitinka griežtos leidžiamų įvesčių sąlygos. Jis naudoja ankstesnius testo CO etalonus; bendros kaukės nepaverčia informacinių sąlygų vienodomis.
2. Aukšta — realus duomenų prieinamumas valandos pabaigoje neįrodytas. Nėra matavimų gavimo laiko ir vėlavimų patikros.
3. Aukšta — tikrų CO spragų tikslumas neįrodytas. Vertinimas apima dirbtinai paslėptus žinomus etalonus; jo perkėlimas į natūralias spragas lieka prielaida.
4. Vidutinė — istorinis testo neliečiamumas neįrodytas. Kodo vykdymo tvarka patvirtina vieno paleidimo seką, tačiau ne ankstesnių sprendimų nepriklausomumą nuo testo.
5. Vidutinė — extreme rezultatų interpretacija ribota. Blokų atranka remiasi tikru būsimo bloko CO; tai nėra realaus laiko trūkumo mechanizmo patikra.
6. Vidutinė — neapibrėžtumas įvertintas tik RF ir baseline MAE skirtumui. Bootstrap kodas nevertina pasirinkto SVR pranašumo ar ekstremumų recall neapibrėžtumo; blokų laikinė priklausomybė taip pat lieka.
7. Žemesnė — skirtingų spragų ilgių ir visų variantų palyginimai nėra visiškai simetriški. Ilgiai keičia vertinamų valandų imtį (masks.py, 8–18 eil.), o RF papildomi variantai neturi visų streso scenarijų.
8. Žemesnė — repozitorijoje trūksta originalaus eksperimento įrodymų paketo. Rezultatai ir modeliai neplatinami (README.md, 29 eil.); ši recenzija galėjo patikrinti originalius skaičius todėl, kad buvo prieinama vietinė rezultatų kopija.

22:26, trečiadienis

Nieko kode nekeisk. Atlik literatūros paiešką 2022–2026 m. publikacijose apie trūkstamų oro kokybės jutiklių duomenų atkūrimą, CO / dujų jutiklių kalibravimą arba retų didelių taršos koncentracijų regresiją.  
Prioritetas:
- UCI Air Quality dataset arba labai panašūs valandiniai daugiamačiai jutiklių duomenys;
- metodai, tinkami veikti be ateities duomenų;
- neklasikinis metodas ARBA klasikinio metodo modifikacija;
- metodas turi būti realistiškai įgyvendinamas šiame projekte CPU režimu.
Kiekvienam kandidatui pateik:
- straipsnio DOI ir leidėjo nuorodą;
- ką tiksliai autoriai padarė;
- kokią problemos dalį tai galėtų pagerinti mano eksperimente;
- ar metodas naudoja ateities informaciją;
- kiek sudėtinga jį įgyvendinti;
- kokia yra rizika, kad jis netiks mano uždaviniui.
Atskirai įvertink esamą weighted SVR, pagrįstą Zhen et al. 2025, ir ar jį galima laikyti literatūra pagrįsta klasikinio metodo modifikacija. Nesiūlyk metodo vien todėl, kad jis modernesnis.

22:32, trečiadienis

Dirbo 1m 45s

Paieška rodo, kad tavo projektui verta atskirti du dalykus: CO atkūrimą iš tuo metu prieinamų kitų signalų ir fizinių mažos kainos jutiklių kalibravimą. Pirmasis tiesiogiai atitinka dabartinį eksperimentą; kalibravimo darbai labiau pagrindžia validavimo, dreifo bei paprastesnių modelių poreikį.

| Kandidatas | Ką autoriai darė | Galima nauda tavo eksperimentui | Ateities informacija? | CPU įgyvendinimas | Pagrindinė rizika |
|---|---|---|---|---|---|
| **Weighted SVR (SVR-W)** | Zhen et al. sprendė retų didelių O₃ reikšmių nuvertinimą SVR mokymui suteikdami didesnius svorius aukštos koncentracijos pavyzdžiams. Pagerėjo aukštų O₃ reikšmių aptikimas, bet tai buvo daugelio stočių ir papildomų erdvinių bei meteorologinių duomenų tyrimas. [DOI](https://doi.org/10.1016/j.atmosenv.2024.120952), [leidėjo puslapis](https://www.sciencedirect.com/science/article/pii/S1352231024006277). | Tiesiogiai mažintų CO pikų nuvertinimą ir galėtų pagerinti q95 recall. | Ne, jei svoris apskaičiuojamas tik iš mokymo `CO(GT)`, o modelis inferencijoje naudoja tik einamosios valandos bei praeities PT08/meteo požymius. | Žema: `SVR` su `sample_weight`; dabartinė projekto versija jau tai daro. | O₃ rezultatai nėra CO rezultatai; svorio `3` reikšmė nėra straipsnio universali taisyklė. Didesnis recall gali mažinti precision ir bendrą MAE. |
| **Laiko sezoniškumą ir Elastic Net jungiantis imputeris** | Wijesekara ir Liyanage išskaidė seriją į sezoninę bei kitą dalį, o didelius intervalus atkūrė Elastic Net, naudodami koreliuotus kintamuosius. [DOI](https://doi.org/10.3390/atmos14020355), [leidėjo puslapis](https://www.mdpi.com/2073-4433/14/2/355). | Gali tapti aiškiu, greitu ir interpretuojamu papildomu baseline: valandos/savaitės sezoniškumas + PT08/meteo Elastic Net. | **Straipsnio imputeriui — neįrodyta, kad jis priežastinis.** Jis naudoja visos serijos STL dekompoziciją ir 10-fold CV, todėl tiesioginis perkėlimas galėtų įtraukti ateitį. | Vidutinė, jei kuriama priežastinė versija su tik mokymo laikotarpiu išmoktais kalendoriaus požymiais ir Elastic Net. | Tiesioginis straipsnio algoritmas netinka tavo realaus laiko sąlygai; reikėtų naujo, priežastinio varianto, todėl tai nebebūtų tiksli replikacija. |
| **RF / regresijos kalibravimo validavimo protokolas** | Dong et al. kalibravo CO, NO₂ ir O₃ mažos kainos jutiklius su etalonais, lygino tiesines, netiesines ir ML regresijas bei tikrino stabilumą atskirame validavimo laikotarpyje. Gazuose RF ir SVR kai kur atrodė gerai kalibracijoje, bet silpnai validacijoje; CO atveju paprastesnės regresijos buvo stabilesnės. [DOI](https://doi.org/10.1016/j.scitotenv.2025.179364), [leidėjo puslapis](https://www.sciencedirect.com/science/article/pii/S0048969725010009). | Pagrindžia Ridge / Huber / daugialypės tiesinės regresijos įtraukimą kaip griežtą, interpretuojamą konkurentą RF ir SVR. Taip pat sustiprina laike atskiro validavimo argumentą. | Ne inference metu: išmokta kalibravimo funkcija naudoja einamuosius jutiklio bei meteorologijos signalus. | Žema. `Ridge`, `ElasticNet` ar `HuberRegressor` veiktų labai greitai CPU. | Straipsnis apie kitokius fizinius jutiklius ir kolokaciją su etalonu; UCI PT08 kanalai nėra jo aparatūra. Tai geras metodinis, bet ne tiesioginis duomenų atitikimas. |
| **Mažos kainos NO₂/O₃ stočių kalibravimas su keliais regresijos modeliais** | Cavaliere et al. atliko išankstinį kalibravimą ir vėlesnį lauko validavimą metalų oksido jutikliams; lygino vienmačius ir daugiamačius tiesinius bei netiesinius modelius. [DOI](https://doi.org/10.5194/amt-16-4723-2023), [leidėjo puslapis](https://amt.copernicus.org/articles/16/4723/2023/). | Gali pagrįsti mažos apimties modelių palyginimą ir jutikliui specifinį validavimą; ypač naudingas argumentui, kad papildomi kintamieji nebūtinai pagerina rezultatą. | Ne, jei modelis mokomas ankstesniu laikotarpiu ir inferencijoje gauna tik dabartines reikšmes. | Žema–vidutinė. Tiesinė, polinominė bei ribota gradientinių medžių versija veikia CPU. | NO₂/O₃, ne CO; stoties aparato signalai ir UCI požymiai skiriasi. Tyrimas nepasiūlo naujo tiesioginio CO spragų atkūrimo modelio. |
| **Nuolatinė stochastinė kalibracija su mobiliais etalonais** | Tancev ir Toro modeliuoja ilgalaikį CO, NO₂ ir O₃ mažos kainos sensorių perkalibravimą, kai mobilus etalonas periodiškai susitinka su stacionariais mazgais; parametrai atnaujinami stochastiniais gradientais. [DOI](https://doi.org/10.1109/ACCESS.2022.3145945), [leidėjo puslapis](https://ieeexplore.ieee.org/document/9691902). | Spręstų dreifo riziką, kuri dabartiniame eksperimente tik sintetiškai tikrinama. | Taip, veikimo metu naudoja tik iki susitikimo turėtą informaciją ir naują etaloną. | Vidutinė pačiam algoritmui, bet aukšta kaip eksperimentui, nes reikia realių periodinių etalonų. | Dabartiniame UCI vienos stoties faile nėra mobilių etalonų ar pakartotinės kolokacijos. Todėl tai netinka kaip sąžiningas naujas pagrindinis metodas šiame projekte. |
| **Concept-drift adaptacija mažos kainos tinkluose** | D’Elia et al. nagrinėjo dreifo aptikimą ir kalibracijos atnaujinimą, įskaitant svarbių pavyzdžių svėrimą bei nuotolinės kalibracijos prielaidas. [DOI](https://doi.org/10.3390/s24092786), [leidėjo puslapis](https://www.mdpi.com/1424-8220/24/9/2786). | Galėtų pagrįsti dreifo detektorių arba mokymo duomenų persvėrimą pagal laiką. | Veikimo principas gali būti priežastinis, bet reikalauja išorinio patikimo atnaujinimo signalo arba sąlygos, kad nuotolinė stotis reprezentuoja vietinę koncentraciją. | Vidutinė algoritmiškai. | Dabartiniai duomenys neturi antros artimos etaloninės stoties, todėl pagrindinė metodo prielaida neįvykdyta. |
| **BRITS ir RF multivariatis imputavimas** | Díaz-González et al. lygino RF ir BRITS atkuriant oro kokybės tinklo kintamuosius, įskaitant CO bei meteorologiją. RF buvo tikslesnis maskuotose reikšmėse, BRITS geriau išlaikė visos serijos skirstinį. [DOI](https://doi.org/10.3390/ai6090208), [leidėjo puslapis](https://www.mdpi.com/2673-2688/6/9/208). | RF tipo multivariatis atkūrimas metodologiškai artimas tavo uždaviniui. | **BRITS — taip, naudoja dvikryptę laiko eigą, taigi ir ateities kontekstą.** Tavo realaus laiko uždaviniui jo nesiūlau. | RF žema; BRITS vidutinė–aukšta net CPU režimu. | Straipsnio maskavimas atsitiktinis, o ne blokinis; BRITS pažeistų tavo prieinamumo taisyklę. |

Dėl esamo weighted SVR vertinimo: jį galima laikyti literatūra pagrįsta klasikine metodo modifikacija, bet tiksliau būtų vadinti Zhen et al. įkvėpta adaptacija, o ne straipsnio replikacija. Principas sutampa: reti aukšti tikslai mokymo metu gauna didesnį svorį. Tavo sprendime tai techniškai korektiška, jei:
- ekstremumo slenkstis ir svoriai apskaičiuojami vien iš train dalies;
- SVR-W parametrai bei svorio dydis parenkami tik validation dalyje;
- testas naudojamas tik galutiniam palyginimui;
- rezultatai pateikiami kaip recall–precision–MAE kompromisas.
Dabartinis SVR_W su fiksuotu svoriu 3 yra teisėtas papildomas bandymas, bet nepakanka jį vadinti optimalia literatūros formule. Zhen et al. sprendė O₃, daug stočių ir kitokią požymių erdvę; todėl svorį reikia laikyti projekto hiperparametru, o ne iš literatūros tiesiogiai perimta konstanta.
Mano prioritetas šiam projektui būtų toks:
1. Weighted SVR palikti kaip aiškiai apibrėžtą papildomą variantą, atrenkamą tik validavime.
2. Pridėti mažos rizikos Ridge arba Elastic Net kalibracinį modelį su tais pačiais priežastiniais požymiais.
3. Dreifo ir nuotolinės kalibracijos metodų nevadinti įgyvendinamais pagrindiniais sprendimais, nes dabartinis UCI failas neturi būtinos etaloninės infrastruktūros.
4. BRITS, bidirekčių RNN ir pilnos serijos STL imputavimo nenaudoti pagrindiniam rezultatui, nes jie arba naudoja ateitį, arba jų priežastinė versija būtų naujas, ne tiesiogiai publikuotas metodas.

22:34, trečiadienis

Remdamasis ankstesne literatūros analize ir esamo eksperimento auditu, pasirink VIENĄ pagrindinį patobulinimą.  
Mano prioritetai:
1. korektiškumas ir realaus laiko sąlyga;
2. mažesnis didelių CO reikšmių nuvertinimas;
3. bendras MAE neturi smarkiai pablogėti;
4. sprendimas turi tilpti į esamą CPU biudžetą.
Palygink bent:
- bazinį RF;
- bazinį SVR;
- weighted SVR;
- literatūroje rastą alternatyvą, jei ji tinkama.
Dar nieko neprogramuok. Suformuluok iš anksto patikrinamą hipotezę ir pasiūlyk hiperparametrų paieškos erdvę bei validavimo atrankos taisyklę. Testo rezultatų šioje atrankoje naudoti negalima.

22:36, trečiadienis

Rinkčiausi vieną pagrindinį patobulinimą: SVR-W perkelti iš papildomo testo bandymo į iš anksto apibrėžtą validavimo kandidatą, kartu reguliariai parenkant jo ekstremumo slenkstį ir svorį.
Tai geriausiai atitinka tavo prioritetus. Jis nekeičia realaus laiko įvesties sutarties: prognozei lieka tik tos pačios valandos PT08, meteorologija ir praeities vėlinimai. Keičiasi tik mokymo nuostolio svoris, apskaičiuotas iš mokymo CO etalonų. Zhen et al. būtent taip sprendė retų aukštų koncentracijų nuvertinimą SVR modelyje, nors jų O₃, daug stočių ir erdvinių požymių aplinka nėra tiesiogiai tapati tavo CO uždaviniui. Straipsnis, DOI.

| Kandidatas | Realus laikas | Didelių CO reikšmių tikėtinas poveikis | MAE rizika | Vaidmuo validavime |
|---|---|---|---|---|
| Bazinis RF | Taip | Ribota: miško lapų vidurkinimas dažnai mažina pikus | Maža | Esamas stiprus nelinijinis atskaitos modelis |
| Bazinis SVR | Taip | Geresnis kompromisas nei RF validavime, bet pikas vis tiek gali būti nuvertintas | Maža | Esamas pagrindinis kandidatas |
| **SVR-W** | Taip | Tiesiogiai skirtas padidinti aukštų reikšmių svarbą | Vidutinė, todėl būtinas MAE apribojimas | **Siūlomas pagrindinis patobulinimas** |
| Causal Elastic Net / Ridge | Taip | Mažai tikėtina, kad pagerins pikus be papildomo svėrimo | Maža | Literatūroje pagrįstas paprastas kontrolinis modelis, ne pagrindinis patobulinimas |

Elastic Net būtų tinkama literatūrinė alternatyva, nes sezoninės dekompozicijos ir Elastic Net darbas rodo naudą didelėms spragoms, kai yra koreliuotų kintamųjų. Tačiau pats publikuotas algoritmas nėra saugiai priežastinis: jis naudoja visos serijos dekompoziciją ir atsitiktinį kryžminį validavimą. Todėl tavo darbui galima naudoti tik supaprastintą priežastinį Elastic Net su dabartiniais 68 požymiais, be visos serijos STL. Tai būtų vertingas kontrolinis metodas, bet nėra geriausias pasirinkimas pikų nuvertinimui mažinti. Straipsnis, DOI.
Iš anksto patikrinama hipotezė:
Tarp modelių, kurių A/24 val. validavimo MAE nėra didesnė kaip 5 % už geriausio iš bazinio RF, bazinio SVR ir Elastic Net/Ridge kandidato MAE, SVR-W pasieks didžiausią ekstremalių CO reikšmių recall. Ekstremumas apibrėžiamas tik mokymo dalies CO(GT) kvantiliu. Jei nė vienas SVR-W kandidatas šio MAE apribojimo neatitinka, pagrindinis modelis lieka bazinis validavimo laimėtojas.

Ši taisyklė sąmoningai nedaro vien recall maksimizavimo tikslu: kitaip didelis svoris galėtų kelti per daug klaidingų ekstremumų ir pabloginti bendrą rekonstrukciją.
Siūloma validavimo paieškos erdvė:

| Modelis | Iš anksto nustatyta erdvė |
|---|---|
| RF | Esama 18 konfigūracijų: `max_depth ∈ {8,16,None}`, `min_samples_leaf ∈ {2,5,10}`, `max_features ∈ {0.7,1.0}`, `n_estimators=300` |
| SVR | Esamos 18 konfigūracijų: `C ∈ {1,10,100}`, `epsilon ∈ {0.05,0.20}`, `gamma ∈ {scale,0.01,0.1}` |
| **SVR-W** | Tos pačios 18 SVR konfigūracijų × `q ∈ {0.90,0.95}` × aukštų CO pavyzdžių svoris `w ∈ {1.5,2,3,4}`; kiti pavyzdžiai turi svorį `1` |
| Elastic Net | `alpha ∈ {0.001,0.01,0.1,1}`, `l1_ratio ∈ {0.1,0.5,0.9}`; tie patys priežastiniai 68 požymiai ir tik mokymo preprocessing |

q apskaičiuojamas tik iš mokymo y; tuomet tiek svoriai, tiek validavimo ekstremumų recall remiasi tuo pačiu, iš anksto nustatytu slenksčiu. Validavimo A scenarijui išlaikomos dabartinės 24 val. blokinės spragos ir sėklos 17, 42, 101. Train, preprocessing ir modelių atranka vyksta prieš atidarant testą.
Atrankos taisyklė būtų:
1. Kiekvienam kandidatui apskaičiuoti trijų A/24 validavimo kaukių vidutinį MAE, block-MAE, recall ir precision.
2. Palikti tik kandidatus, kurių MAE ≤ 1.05 × mažiausias visų kandidatų MAE.
3. Iš likusių parinkti didžiausią recall turintį modelį.
4. Jei recall sutampa, parinkti didesnį precision; jei ir jis sutampa, mažesnį block-MAE; galiausiai mažesnį mokymo ir prognozavimo laiką.
5. Užfiksuoti pasirinktą modelį, jo parametrus, q ir svorius, o testą vykdyti vieną kartą jau nieko nebekeičiant.
Paieška apimtų 18 RF, 18 SVR, 144 SVR-W ir 12 Elastic Net kandidatus. Tai yra apie 192 mokymai; su dabartine nedidele duomenų apimtimi ir esamu 2 valandų CPU biudžetu realistiška, bet prieš vykdymą verta nustatyti kiekvieno mokymo laiko limitą ir nutrauktus kandidatus įrašyti kaip nebaigtus.

22:37, trečiadienis

Įgyvendink weighted SVR kaip pilnavertį kandidatą, o ne kaip post-hoc bandymą.
Sąlygos:
- ekstremumo riba q95 apskaičiuojama tik iš mokymo CO;
- mokymo pavyzdžiams virš q95 suteikiamas svoris w;
- w tikrinti tik validavime, pvz. {1, 2, 3, 5, 8};
- kitus SVR hiperparametrus derinti tik train/validation;
- testas turi likti visiškai užrakintas iki galutinio modelio pasirinkimo;
- visi modeliai turi būti vertinami tomis pačiomis kaukėmis;
- išsaugoti kiekvieno kandidato validavimo MAE, extreme MAE, recall, precision ir vykdymo laiką.
Prieš paleisdamas galutinį testą parodyk man validavimo lentelę ir siūlomą atrankos sprendimą. Galutinio testo dar NEPALEISK.

22:37, trečiadienis

Dirbo 32m 50s

Weighted SVR įgyvendintas kaip pilnavertis validavimo kandidatas:
- q95 skaičiuojamas tik iš train CO;
- tik train pavyzdžiai virš q95 gauna w ∈ {1,2,3,5,8};
- visi 126 kandidatai vertinami tomis pačiomis trimis A/24 val. validavimo kaukėmis;
- išsaugomos per-kaukės metrikos ir validation_summary.csv su kiekvieno kandidato MAE, extreme-MAE, recall, precision, mokymo bei prognozavimo laiku;
- pridėtas --validation-only, kuris nesukuria jokių testo kaukių, prognozių, metrikų ar ataskaitos.
13 testų praėjo. Pataisyta ir atrankos logika: galutinis selected.joblib bus susietas su konkrečiu laimėjusiu kandidatu, ne vien modelio šeima.
Turima validavimo lentelė rodo:

| Kandidatas | MAE | Extreme MAE | Recall | Precision | Bendras laikas, s |
|---|---:|---:|---:|---:|---:|
| RF_15 | 0.5098 | 1.2073 | 0.5927 | 0.8823 | 4.91 |
| SVR_07 | 0.5167 | 1.1906 | 0.6285 | 0.8565 | 2.40 |
| SVR-W, w=2 | 0.5118 | 1.1246 | 0.6400 | 0.8319 | 2.50 |
| SVR-W, w=3 | 0.5101 | 1.0788 | 0.6515 | 0.8278 | 2.49 |
| SVR-W, w=5 | 0.5132 | 1.0629 | 0.6657 | 0.8119 | 2.64 |
| **SVR-W, w=8** | **0.5162** | **1.0349** | **0.6657** | **0.7880** | **2.60** |

Siūlomas atrankos sprendimas pagal esamą taisyklę „per 2 % nuo geriausio MAE, tada didžiausias recall, tada laikas“ yra SVR-W su C=10, epsilon=0.05, gamma=0.01, w=8. Jo MAE nuo geriausio RF skiriasi tik 1.25 %, bet jis turi didžiausią recall ir mažiausią extreme-MAE; su w=5 recall sutampa, o w=8 yra greitesnis.
Pataisytas galutinis validavimo paleidimas dar vyksta fone; jis testo nepasiekė ir testas nebuvo paleistas. Baigus bus įrašyta užrakinto testo būsena bei tas pats pasirinkimas į galutinį validavimo rezultatų aplanką.

  Redaguota 10 failų+143-69Peržiūrėti pakeitimusAtšauktiPeržiūrėti pakeitimus

outputs/Air_Quality_kodas/config.yamloutputs/Air_Quality_kodas/config.yaml+3-0
outputs/Air_Quality_kodas/run_experiment.pyoutputs/Air_Quality_kodas/run_experiment.py+49-29
outputs/Air_Quality_kodas/tests/test_protocol.pyoutputs/Air_Quality_kodas/tests/test_protocol.py+6-0
outputs/Air Quality/config.yamloutputs/Air Quality/config.yaml+3-0
outputs/Air Quality/run_experiment.pyoutputs/Air Quality/run_experiment.py+50-30
outputs/Air Quality/tests/test_protocol.pyoutputs/Air Quality/tests/test_protocol.py+6-0
outputs/Air_Quality_kodas/README.mdoutputs/Air_Quality_kodas/README.md+12-4
outputs/Air_Quality_kodas/airquality/report.pyoutputs/Air_Quality_kodas/airquality/report.py+2-2
outputs/Air Quality/README.mdoutputs/Air Quality/README.md+10-2
outputs/Air Quality/airquality/report.pyoutputs/Air Quality/airquality/report.py+2-2

Peržiūrėk tik validavimo rezultatus. Neatidaryk testo.
Atsakyk:
- ar weighted SVR iš tikrųjų pagerino retų didelių CO reikšmių aptikimą;
- kiek už tai sumokėta bendro MAE ir precision pablogėjimu;
- ar skirtumas stabilus per visas tris kaukes;
- ar yra požymių, kad modelis persimokė;
- ar pasirinktas svoris pagrįstas rezultatais;
- ar rezultatas pakankamai geras, kad weighted SVR būtų įtrauktas į galutinį testą.
Jei ne – pasiūlyk tik vieną kitą patobulinimą ir pagrįsk jį. Nenaudok testavimo duomenų.

23:11, trečiadienis

Dirbo 6m 6s

| Modelis | MAE | Extreme MAE | Recall | Precision |
|---|---:|---:|---:|---:|
| RF | 0,5098 | 1,2073 | 0,5927 | 0,8823 |
| Bazinis SVR | 0,5167 | 1,1906 | 0,6285 | 0,8565 |
| Weighted SVR, w=5 | 0,5132 | 1,0629 | 0,6657 | 0,8119 |

Lyginant su baziniu SVR, w=5:
- recall padidėjo 0,0371 punkto: nuo 0,6285 iki 0,6657;
- extreme MAE sumažėjo 0,1277 arba apie 10,7 %;
- bendras MAE nepablogėjo — jis sumažėjo 0,0035;
- precision sumažėjo 0,0446 punkto: nuo 0,8565 iki 0,8119.
Pagerėjimas stabilus per visas tris validavimo kaukes. Recall pagerėjo atitinkamai nuo 0,5846 iki 0,6000, nuo 0,7838 iki 0,8108 ir nuo 0,5172 iki 0,5862. Extreme MAE sumažėjo kiekvienoje kaukėje. Precision kiekvienoje kaukėje sumažėjo, todėl modelis randa daugiau ekstremalių atvejų, bet pateikia ir daugiau klaidingų perspėjimų.
Nėra ryškaus požymio, kad rezultatas būtų vienos kaukės atsitiktinumas: recall ir extreme MAE kryptis sutampa visose trijose kaukėse, o didesni svoriai sudaro nuoseklų kompromisą. Vis dėlto persimokymo negalima galutinai atmesti, nes daug kandidatų atrinkta pagal tą patį validavimo laikotarpį. Tai bus patikrinta tik vieną kartą, užrakintame teste.
Pasirinktas w=5 yra pagrįstas. Jis pasiekia tokį patį didžiausią recall kaip w=8 (0,6657), tačiau turi geresnį MAE (0,5132 prieš 0,5162) ir geresnį precision (0,8119 prieš 0,7880). w=8 dar truputį mažina extreme MAE, bet už tai moka aiškiai didesniu klaidingų perspėjimų skaičiumi.
Weighted SVR verta įtraukti į galutinį testą kaip iš anksto atrinktą kandidatą. Jis tenkina prioritetus: veikia tomis pačiomis realaus laiko sąlygomis, mažina didelių CO reikšmių nuvertinimą ir nepablogina bendro MAE, nors precision kompromisas turi būti aiškiai pateiktas galutinėje ataskaitoje.
Duomenys paimti tik iš [validavimo suvestinės](C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Air Quality/results_weighted_validation_final/validation_summary.csv) ir [trijų validavimo kaukių metrikų](C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Air Quality/results_weighted_validation_final/validation_metrics.csv). Testavimo rezultatų neatidariau.

23:17, trečiadienis

Dabar užfiksuok pasirinktą konfigūraciją ir atlik vienkartinį galutinio testo vertinimą.
Palygink:
- paskutinę žinomą reikšmę;
- paros valandos vidurkį;
- RF;
- SVR;
- pasirinktą literatūra pagrįstą modifikuotą metodą.
Naudok identiškas testavimo kaukes ir pateik MAE, RMSE, blokų MAE, extreme MAE, recall, precision ir vidutinę ženklinę paklaidą.
Po testo jokių hiperparametrų nebekoreguok.

23:17, trečiadienis

Dirbo 3m 55s

Galutinis testas atliktas vieną kartą. Užfiksuotas pasirinkimas: weighted SVR, w=5, C=10, epsilon=0,05, gamma=0,01; ekstremumo riba iš mokymo duomenų q95=4,6.
Lentelėje pateikti 51 vienodų testavimo kaukių metrikų vidurkiai. Ženklinė paklaida yra prognozė − etalonas visiems užmaskuotiems taškams.

| Metodas | MAE | RMSE | Blokų MAE | Extreme MAE | Recall | Precision | Vid. ženklinė paklaida |
|---|---:|---:|---:|---:|---:|---:|---:|
| Paskutinė žinoma reikšmė | 1,2953 | 1,7542 | 1,2782 | 2,6942 | 0,2415 | 0,1433 | +0,1957 |
| Paros valandos vidurkis | 0,8913 | 1,1799 | 0,9048 | 2,7609 | 0,0000 | – | +0,1188 |
| RF | **0,5451** | **0,7768** | **0,5637** | 1,4056 | 0,5097 | **0,9419** | +0,1000 |
| SVR | 0,7133 | 0,9091 | 0,7371 | 1,3506 | 0,4677 | 0,8900 | +0,3866 |
| Weighted SVR (`w=5`) | 0,7102 | 0,9132 | 0,7346 | **1,2137** | **0,5852** | 0,8325 | +0,4177 |

Weighted SVR, palyginti su baziniu SVR, sumažino extreme MAE 10,1 % ir padidino recall 0,1175 punkto, o bendras MAE sumažėjo 0,0031. Kompromisas — precision sumažėjo 0,0575 punkto ir RMSE nežymiai padidėjo 0,0041.
RF lieka stipriausias bendroms paklaidoms ir precision, tačiau weighted SVR yra geriausias kandidatų variantas retų aukštų CO koncentracijų atkūrimui: jis turi mažiausią extreme MAE ir didžiausią recall. Jo vidutinė ženklinė paklaida teigiama, nors ekstremalių reikšmių paklaida išlieka neigiama, todėl aukšti CO atvejai vis dar vidutiniškai nuvertinami, tik mažiau nei baziniu SVR.
Konfigūracija užfiksuota [config_final_locked.yaml](C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Air Quality/config_final_locked.yaml), o galutiniai rezultatai ir atranka išsaugoti [results_final_locked](C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Air Quality/results_final_locked). Po šio testo hiperparametrai nebuvo ir nebus koreguojami.

  Redaguotas failas config_final_locked.yaml+26-0Peržiūrėti pakeitimusAtšauktiPeržiūrėti pakeitimus

23:21, trečiadienis

Sugeneruok ne tik suvestines lenteles, bet ir grafikus, kuriuose matosi faktinė CO kreivė ir kiekvieno pagrindinio metodo prognozė per pasirinktus testavimo 24 val. intervalus.
Parink:
- tipinį gerą intervalą;
- blogiausią RF intervalą;
- intervalą su tikru CO ekstremumu;
- intervalą, kuriame modifikuotas metodas pagerina rezultatą.
Grafikuose aiškiai pažymėk paslėptą intervalą. Po kiekvienu grafiku automatiškai pateik 2–3 skaitines išvadas. Neteik vien vizualaus vertinimo.

23:22, trečiadienis

Dirbo 2m 55s

Sugeneravau keturis 24 val. galutinio testo grafikus. Geltonas fonas žymi paslėptą intervalą, punktyras — mokymo q95=4,60 ribą. Po kiekvienu grafiku pateiktos trys automatinės skaitinės išvados.
- [Visa intervalų analizė HTML formatu](C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Air Quality/results_final_locked/interval_figures/ataskaita_intervalai.html)
- [Tipinis geras intervalas](C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Air Quality/results_final_locked/interval_figures/tipinis_geras.png) — RF MAE 0,304.
- [Blogiausias RF intervalas](C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Air Quality/results_final_locked/interval_figures/blogiausias_rf.png) — RF MAE 2,478, didžiausias tarp 315 nagrinėtų 24 val. blokų.
- [Intervalas su tikru CO ekstremumu](C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Air Quality/results_final_locked/interval_figures/tikras_ekstremumas.png) — faktinis pikas 8,40 mg/m³.
- [Intervalas, kuriame weighted SVR pagerina bazinį SVR](C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Air Quality/results_final_locked/interval_figures/weighted_svr_pagerėjimas.png) — MAE sumažėja nuo 0,917 iki 0,812, arba 11,5 %.
Parinkimo kriterijai ir visos blokų metrikos išsaugotos [selected_intervals.json](C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Air Quality/results_final_locked/interval_figures/selected_intervals.json). Grafikų generavimo scenarijus tik perskaito galutinio testo prognozes: [generate_test_interval_figures.py](C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Air Quality/generate_test_interval_figures.py).

  Redaguotas failas generate_test_interval_figures.py+179-0Peržiūrėti pakeitimusAtšauktiPeržiūrėti pakeitimus

23:25, trečiadienis

Laikyk, kad šį projektą pateiks studentas ir už visas išvadas atsako pats. Atlik galutinį nepriklausomą auditą.
Patikrink:
- duomenų kilmę ir SHA;
- train/validation/test izoliaciją;
- visas preprocessing statistikas;
- target ir future leakage;
- maskavimo tvarką prieš lag kūrimą;
- modelių atrankos chronologiją;
- ar rezultatų lentelėse tikrai naudojamas tik testas;
- ar testas nebuvo panaudotas vėlesniam parametrų derinimui;
- ar modifikuoto metodo literatūros citata tikrai pagrindžia būtent tokią idėją;
- ar visas metrikas galima perskaičiuoti iš išsaugotų predictions failų.
Sukurk FINAL_AUDIT.md, kuriame kiekvienas punktas turi būseną PASS / WARNING / FAIL ir konkretų įrodymą.

23:26, trečiadienis

Dirbo 4m 51s

Sukūriau [FINAL_AUDIT.md](C:/Users/WildBerry/Documents/Codex/2026-09-22/re/outputs/Air Quality/FINAL_AUDIT.md) su konkrečiais kodo ir artefaktų įrodymais kiekvienam punktui.
Audito rezultatas: 7 PASS, 2 WARNING, 1 FAIL.
Svarbiausios ribos:
- extreme scenarijaus kaukė parenkama pagal testo CO etaloną, todėl tai tik retrospektyvus streso testas.
- Negalima absoliučiai įrodyti, kad ankstesni testiniai rezultatai niekada nebuvo matyti prieš vėlesnius sprendimus.
- Weighted SVR konkrečiai formai trūksta patikrinamos literatūrinės citatos su DOI ar leidėjo nuoroda; šiuo metu jos negalima pateikti kaip patikrintai Zhen et al. pagrįsto metodo.
Duomenų SHA sutapo, train/validation/test izoliacija ir preprocessing patvirtinti, o visos 363 metrikų eilutės perskaičiuotos iš išsaugotų prognozių be neatitikimų.

23:31, trečiadienis
