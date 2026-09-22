# Galutinio egzamino kriterijų atitiktis

Šis sąrašas nurodo programinius įrodymus, bet nesuteikia ir nežada vertinimo balų.

| Kriterijus | Maks. balai | Įgyvendinimas ir įrodymai |
|---|---:|---|
| Baseline, duomenų grandinė, atkuriamumas | 10 | `load.py`, `split.py`, `baselines.py`; SHA-256, `split.json`, `requirements-lock.txt`, viena paleidimo komanda |
| Bent du intelektualieji metodai | 20 | RF ir RBF SVR; `models.py`, išsaugoti modeliai; formulės ryšys ir `formula_check.json` |
| Korektiškas eksperimentas | 20 | Chronologinės dalys; tik mokymo preprocessing; 36 konfigūracijų validavimas; bendros kaukės; atranka užfiksuota `selection.json` prieš testą; nutekėjimo testai |
| Rezultatai, abliacija, atsparumas, klaidos | 15 | `ataskaita.html`, `metrics.csv`, grafikai, RF be istorijos ir kaukių; triukšmas, dreifas, gedimai; blogiausi intervalai ir nepastebėti epizodai |
| Ribos, rizikos, praktinis tinkamumas | 10 | Ataskaitos ribų ir kokybės žymų skyriai; viena vieta, seni duomenys, natūralių spragų nežinomi etalonai, euristinė kokybė |
| AI naudojimo auditas | 5 | `AI_NAUDOJIMO_ZURNALAS.md`, testų rezultatai ir formulės patikra |
| Gyvas gynimas, nematytas testas, pakeitimas | 10 | Paruošti `predict.py`, įvesties pavyzdys ir `GYNIMAS.md`. Pats gynimas dar neatliktas; tai studento atsakomybė |

## Ryšys su koliokviumo planu

Išlaikytas tikslinis CO, 68 požymiai, sėklos, RF/SVR hiperparametrų tinkleliai, 60/20/20 chronologija, 24 val. pradžios atmetimas, 6/24/72 val. spragos ir nurodyti atsparumo bandymai. RF parinkimo hipotezė tikrinama net jei validavime pagrindiniu pasirinktas SVR. Visų konfigūracijų kandidatai mokomi tik pirmuose 60 %, po atrankos nepermokoma.

Praktiniai patikslinimai: 8 GB limitas matuojamas mokymo proceso ir jo vaikinių procesų RSS; viso kompiuterio RAM neapribojama. 2 val. biudžetas tikrinamas etapų ribose ir mokymo stebėjime; ataskaitos generavimas gali baigtis po ribos. Trūkumo žymos yra euristinės, ne tikimybės. Kandidatų lygiųjų laikas gali šiek tiek kisti tarp kompiuterių, todėl išsaugota ir konkreti atranka, ir visi parametrai.
