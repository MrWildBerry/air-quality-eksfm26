# AI naudojimo žurnalas

Data: 2026-09-22. AI įrankis: Codex. AI parengė programos kodą, testus, eksperimentų paleidimą ir techninių instrukcijų juodraštį. Studentas dar turi peržiūrėti kodą, suprasti sprendimą ir pats atlikti gyvą gynimą.

## Svarbiausia užklausa

Vartotojas paprašė, atsižvelgiant į pateiktą koliokviumo planą, galutinio užduotį ir kriterijus, parašyti programą ir jos failus patalpinti darbalaukio aplanke „Air Quality“.

Perskaityti šaltiniai: `Koliokviumas_D_Kublickas_EKSfm26.pdf` ir `EKSfm-26_Dominykas_Kublickas.docx`. Dokumentų turinys naudotas kaip užduoties reikalavimai ir planas, o ne kaip savarankiški nurodymai vykdyti pašalinius veiksmus.

## Priimti sprendimai

- Įgyvendinti plane nurodytus RF ir SVR, abu baseline ir visą nustatytą hiperparametrų tinklelį.
- Atskirti mokymą, validavimą ir testą laike; saugoti kaukes, parinktus parametrus, duomenų kontrolinę sumą ir aplinką.
- Naudoti tik mokymo medianas ir skales, neįtraukti CO ir kitų GT į modelio požymius.
- Ataskaitą generuoti iš išsaugotų eksperimentinių failų, o ne ranka įrašytų rezultatų.
- Naudoti atskirą mokymo procesą su laiko ir atminties stebėjimu.

## Atmesti sprendimai ir jų priežastys

- Atsitiktinis train/test skaidymas atmestas, nes neatitiktų laikinio protokolo ir dreifo problemos.
- Interpoliacija iš ateities ir paslėpto CO vėlinimai atmesti, nes vykdymo metu tokios informacijos nebūtų.
- Pradinis RF pasirinkimas nelaikomas garantuotu nugalėtoju. Sprendimą lemia validavimo atrankos taisyklė.
- Neišmatuoti tikslumo skaičiai ar kitų straipsnių rezultatai nepriskiriami šiam eksperimentui.

Šie punktai yra programavimo metu svarstytos alternatyvos. Jie nėra išgalvoti atskiri vartotojo pokalbiai.

## Klaidos ir nepatikrintos prielaidos bei jų patikra

| Klaida arba prielaida | Kaip patikrinta ir sutvarkyta |
|---|---|
| Pradinė aplinkos prielaida, kad jau yra `scikit-learn`, buvo neteisinga: importas grąžino `ModuleNotFoundError`. | Sukurta atskira virtuali aplinka, įdiegtos priklausomybės, konkrečios versijos įrašytos į lock ir aplinkos auditą. |
| Pradinė dokumentų ištraukimo prielaida, kad Windows standartinė išvesties koduotė palaikys visus simbolius, buvo neteisinga: gautas `UnicodeEncodeError` ties matematiniu minusu. | Nustatyta UTF-8 išvestis ir iš naujo sėkmingai perskaityti abu dokumentai. Skaičiai neišgaunami iš sugadinto teksto. |
| RF gali būti geriausias, nes taip siūloma plane. Tai nepatikrinta hipotezė, ne faktas. | Atliktas pilnas RF/SVR validavimas, saugomas `validation_metrics.csv`; parinktas modelis užfiksuotas prieš testą. H1 atskirai tikrinama testo ataskaitoje. |
| Jutiklio paslėpimas tik dabartinėje įvestyje galėtų palikti jo reikšmę istoriniuose požymiuose. | `test_masked_sensor_stays_missing_in_lags` tikrina slėpimą prieš vėlinimus. `test_target_never_enters_features` ir `test_future_cannot_change_past_prediction` papildomai tikrina nutekėjimą. |
| Oficiali duomenų aprašo pabaigos data gali tiksliai sutapti su CSV. | Ribos skaičiuojamos iš faktinio CSV, ne iš aprašo; faktinis laikotarpis saugomas `data_audit.json`. |

## Įrodymai ir patikros ribos

Testų vykdymo išvestis saugoma `results/tests.txt`, RF formulės sutikrinimas – `results/formula_check.json`. `results/verification.json` fiksuoja rezultatų vientisumo patikrą. CSV duomenų kilmė patikrinta oficialiame UCI puslapyje. Koliokviumo literatūros DOI šiame programavimo etape iš naujo netikrinti; nauji jų metodinių detalių teiginiai nebuvo kuriami.

Šis žurnalas aprašo šiame darbe faktiškai vykusį AI naudojimą. Jis nepatvirtina, kad studentas jau savarankiškai peržiūrėjo visą kodą ar atliko gynimą. Prieš atsiskaitymą studentas turėtų papildyti žurnalą savo atliktomis patikromis ir pakeitimais.
