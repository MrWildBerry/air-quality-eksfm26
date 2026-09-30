# Air Quality

Dominykas Kublickas · EKSfm-26 · Intelektualiosios sistemos

Programa atkuria tos pačios valandos CO koncentraciją mg/m³ pagal penkis PT08 jutiklių kanalus, temperatūrą ir drėgmę. Įgyvendintas laike atskirtas paskutinės žinomos reikšmės, paros valandos vidurkio, RF, SVR ir svertinės SVR (SVR-W) palyginimas.

## Nuo ko pradėti

1. Atidarykite `Air_Quality.cmd`. Pasirinkite `1`, kad naršyklėje pamatytumėte jau apskaičiuotus rezultatus. Rezultatų peržiūrai Python ir internetas nereikalingi.
2. Perskaitykite `results/ataskaita.html`: rezultatai, grafikai, hipotezės išvada, abliacijos, atsparumas ir klaidų analizė.
3. Gynimui naudokite vadovą `GYNIMAS.md`.

## Paleidimas iš terminalo

Rekomenduojama 64 bitų Python 3.12 (būtent ši versija naudota patikrai), iki 4 CPU gijų, 8 GB eksperimento atminties biudžetas. Pirmą kartą priklausomybėms įdiegti reikia interneto. Windows meniu automatiškai sukuria `.venv`; taip pat galima atlikti rankiniu būdu:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe run_experiment.py --config config.yaml
```

Aktyvavus aplinką vienintelė pagrindinio eksperimento komanda:

```text
python run_experiment.py --config config.yaml
```

Jei rezultatų aplankas jau užpildytas, naujas paleidimas kuria `results_YYYYMMDD_HHMMSS`; ankstesni rezultatai išlieka. `--output mano_rezultatai` leidžia nurodyti kitą aplanką. UCI CSV atsisiunčiamas automatiškai tik tada, kai `data/AirQualityUCI.csv` neegzistuoja. Pateiktoje projekto kopijoje yra išbandytas duomenų failas, todėl kartotiniam eksperimentui po bibliotekų įdiegimo internetas nereikalingas.

## Nematytas failas ir prognozės

```text
python predict.py --input examples/unseen_format.csv --model results/models/selected.joblib --output predictions/demo.csv
```

Įvestis yra kabliataškiais atskirtas CSV, dešimtainė dalis žymima kableliu. Būtini laukai: `Date`, `Time`, `PT08.S1(CO)`, `PT08.S2(NMHC)`, `PT08.S3(NOx)`, `PT08.S4(NO2)`, `PT08.S5(O3)`, `T`, `RH`, `AH`. Data `DD/MM/YYYY`, laikas `HH.MM.SS`. `CO(GT)` neprivalomas ir modelio nenaudojamas. `-200` arba tuščias langelis reiškia trūkumą. Trūkstamas viso kanalo stulpelis yra formato klaida; pateikite jį tuščią, jei kanalas neveikia.

Išvestis: `timestamp`, `co_hat_mg_m3`, `source`, `quality_flag`, `model_version`, `clipped`. Pirmos 24 valandos gali turėti nepilną istoriją ir atitinkamą kokybės žymą. Naudojant veikiančią sistemą įveskite ir ankstesnes 24 istorijos valandas. Nepriskiriama numanoma UTC laiko juosta. Modelio `.joblib` failus įkelkite tik iš patikimo šaltinio, nes tai Python serializuotų modelių failai.

`examples/unseen_format.csv` yra tik formato demonstracija iš duomenų rinkinio, ne papildomas nepriklausomas tikslumo įrodymas. Naujam failui mokymas neatliekamas.

## Kas įgyvendinta

- CSV valymas, -200 keitimas į NaN, prieštaringų dublikatų kanalo žymėjimas, pilnas valandinis tinklelis ir SHA-256.
- 60/20/20 chronologinės dalys, pirmų 24 valandų pašalinimas kiekvienoje dalyje; tik mokymo medianos ir SVR skalės.
- 68 požymiai: 8 dabartiniai, 24 istoriniai, 32 trūkumo indikatoriai ir 4 cikliniai laiko požymiai. Jokių GT įvesčių.
- 18 RF, 18 SVR ir 90 svertinės SVR konfigūracijų. Svertinė SVR aukštoms mokymo CO reikšmėms taiko validavimo duomenimis parenkamą svorį `w ∈ {1,2,3,5,8}`; atranka pagal A/24h validavimą su 17, 42, 101 slėpimo sėklomis. Iki 2 % MAE skirtumo sprendžiama pagal jautrį, vėliau mokymo ir prognozavimo laiką.
- 6/24/72 valandų blokai, apie 20 % padengimas; A, vieno ir visų jutiklių gedimai, triukšmas, dreifas, sistemingi rytiniai ir ekstremumų blokai.
- Abliacijos be istorijos ir be trūkumo kaukių; RF modelio sėklos 17 ir 101; svertinės SVR ekstremumų svoris parenkamas validavime iš nustatyto tinklelio.
- MAE, blokų MAE, RMSE, jautris, preciziškumas, TP/FN/FP, ekstremumų MAE ir ženklinė paklaida; nulinio vardiklio santykiai neapibrėžti.
- 1 000 porinių blokų pakartotinės atrankos su grąžinimu kartojimų kiekvienai A/24h kaukei atskirai, klaidos pagal mėnesį, penki blogiausi intervalai, visi nepastebėti ekstremumų epizodai ir atskaitos metodų pranašumo atvejai.
- Vieno mokymo proceso 120 s riba, iki 4 gijų, 8 GB mokymo proceso ir jo vaikinių procesų RSS riba, 2 valandų eksperimento biudžetas. Tarp etapų tikrinama bendra laiko riba; paskutinio vertinimo ir ataskaitos generavimo pabaiga gali ją nežymiai viršyti. 8 GB riba taikoma mokymo procesui, o ne visos operacinės sistemos atminčiai.

## Failų struktūra

| Failas arba aplankas | Paskirtis |
|---|---|
| `run_experiment.py` | Pilna eksperimento seka ir atranka prieš testą |
| `predict.py` | Prognozės nematytam CSV |
| `config.yaml` | Hiperparametrai, sėklos, biudžetas |
| `airquality/load.py`, `split.py` | Duomenys ir laiko dalys |
| `airquality/features.py` | Formulės (1), (2), vėlinimai ir kaukės |
| `airquality/models.py` | RF/SVR ir formulės (4) skaitinė patikra |
| `airquality/baselines.py` | Formulė (5), griežtai ankstesnis prieinamas CO |
| `airquality/masks.py` | Blokų slėpimas ir jutiklių pažeidimai |
| `airquality/train.py` | Ribojamas atskiras mokymo procesas |
| `airquality/evaluate.py` | Metrikos, atranka, pakartotinė atranka su grąžinimu |
| `airquality/report.py` | Grafikai ir HTML iš saugomų CSV |
| `tests/test_protocol.py` | Nutekėjimo, formulės ir protokolo testai |
| `results/models/selected.joblib` | Validavime pasirinktas modelis |
| `results/training/` | Kandidatų modeliai ir jų mokymo žurnalai |
| `AI_NAUDOJIMO_ZURNALAS.md` | Faktinis AI indėlis ir patikrintos prielaidos |
| `KRITERIJU_ATITIKTIS.md` | Egzamino reikalavimų ir įrodymų atitiktis |

## Patikrinimai

```text
python -m unittest discover -s tests -v
```

Prieš galutinį testą galima paleisti tik validavimą ir peržiūrėti `selection.json`, `validation_metrics.csv` bei kiekvieno kandidato suvestinę `validation_summary.csv`:

```text
python run_experiment.py --config config.yaml --output results_validation --validation-only
```

Šis režimas sąmoningai negeneruoja testo kaukių, prognozių, metrikų ar ataskaitos.

RF formulė tikrinama ir realaus eksperimento metu, o rezultatas išsaugomas `results/formula_check.json`. Visos galutinės lentelės generuojamos iš `metrics.csv` ir `predictions.csv.gz`. `validation_metrics.csv` atskirai saugo atrankos rezultatus. Įverčiai natūralių spragų vietose nėra naudojami tikslumo skaičiavimui, nes tikras CO nežinomas.

## Šaltiniai ir ribos

Duomenys: Vito, S. (2008), UCI Air Quality, DOI https://doi.org/10.24432/C59K5F; https://archive.ics.uci.edu/dataset/360/air+quality. Oficialus puslapis tikrintas kuriant programą. Puslapyje yra ir CC BY 4.0 žyma, ir senesnė tik tyrimų paskirties pastaba; šis projektas skirtas akademiniam eksperimentui.

RF ir SVR metodų literatūrinis pagrindimas pateiktas atnaujintame koliokviumo plane. Svertinės SVR idėją oro teršalų retų aukštų reikšmių nuvertinimui pagrindžia Zhen, L. ir kt. (2025), *Data imbalance causes underestimation of high ozone pollution in machine learning models: A weighted support vector regression solution*, *Atmospheric Environment*, 343, 120952, DOI https://doi.org/10.1016/j.atmosenv.2024.120952. Straipsnis nagrinėja ozoną ir mokymo pavyzdžių svėrimu pagrįstą SVR-W; šiame projekte mokymo q95 ir `w=5` yra CO uždaviniui skirtas pritaikymas, patikrintas validavimo duomenimis, ne tiesioginis autoriaus algoritmo pakartojimas. Šio projekto tikslumas grindžiamas jo paties eksperimentu.

Šis prototipas nėra teisinis oro kokybės indeksas ar sertifikuotas matavimo prietaisas. Kokybės žymos yra euristinės. Galutinį gyvą gynimą, nematytą dėstytojo bandymą ir savarankišką kodo pakeitimą atlieka studentas.
