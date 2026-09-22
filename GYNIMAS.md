# Pasiruošimas gyvam gynimui

## Trumpas pristatymas

Sprendžiama tos pačios valandos CO atkūrimo problema. Penki pigūs PT08 kanalai ir meteorologija naudojami tada, kai etalonas nežinomas. Tai nėra kitos valandos prognozė ir nėra kelių miesto stočių erdvinis modelis. UCI rinkinyje yra viena matavimo vieta.

Pirmiausia parodykite `results/ataskaita.html`, tada `results/selection.json` ir `results/split.json`. Paaiškinkite, kad RF buvo pradinė hipotezė, o galutinis metodas išrinktas validavime. Testo rezultatas gali būti neigiamas; jo negalima pakeisti parenkant kitus parametrus pagal testą.

## Formulė ir kodas

RF koncentracijos įvertis:

```text
co_hat(x) = max(0, (T_1(x) + ... + T_B(x)) / B)
```

Kiekvienas medis, tikrindamas `x[j] <= threshold`, pasiekia lapą. Lapo reikšmė yra mokymo taškų CO vidurkis tame lape, įskaitant bootstrap pasikartojimų svorį. `airquality/models.py:create_model` nustato `bootstrap=True` ir `criterion='squared_error'`. `verify_forest_formula` apskaičiuoja atskirų medžių prognozes ir jų vidurkį, palygina su `model.predict`. `predict` taiko neneigiamumo ribojimą. Realūs palyginimo skaičiai yra `formula_check.json`.

`features.py:Prepare.fit` apskaičiuoja mokymo medianą kiekvienam matavimo požymiui. `transform` naudoja ją trūkstamai reikšmei užpildyti. Kaukė išsaugoma PRIEŠ užpildymą. SVR standartizuojami tik 32 matavimų požymiai; sin/cos ir kaukės nekeičia mastelio.

## Nematytas bandymas

1. Dėstytojo CSV paverskite README aprašytu formatu; išsaugokite jo originalą atskirai.
2. Paleiskite `python predict.py --input destytojo.csv --output predictions/destytojo.csv`.
3. Paaiškinkite kokybės žymas ir parodykite, kad be CO stulpelio prognozės veikia.
4. Jei dėstytojas duoda tikrus CO, juos sujunkite su prognozėmis pagal laiką. Nežinomų etalonų neužpildykite skaičiuodami MAE.

Failas `examples/unseen_format.csv` tinka paleidimo demonstracijai. Jis paimtas iš esamo rinkinio ir nėra naujas nepriklausomas testas.

## Nedidelio pakeitimo pavyzdžiai

- `config.yaml` pakeisti RF `min_samples_leaf` reikšmes ir paleisti su `--output results_pakeitimas`. Tai naujas eksperimentas; ankstesnis testas jau matytas, todėl nauja išvada turi būti laikoma papildoma analize.
- `airquality/evaluate.py:metrics` pridėti medianinę absoliučią klaidą: `float(error.abs().median())`. Išsaugoti ją grąžinamame žodyne ir pagrįsti skirtumą nuo MAE.
- `airquality/masks.py:corrupt` triukšmo koeficientą `.1` pakeisti į `.2`, išlaikant visas kitas sąlygas. Tai atskiras streso bandymas, ne nauja pagrindinio eksperimento atranka.

Po kodo pakeitimo paleiskite `python -m unittest discover -s tests -v`. Negalima tyčia sugadinti saugomų galutinių rezultatų, kad jie atrodytų geresni.

## Klausimai, į kuriuos reikia mokėti atsakyti

- Kodėl duomenys neskaidomi atsitiktinai? Gretimos valandos priklausomos, o būsimos sąlygos gali skirtis dėl dreifo.
- Kodėl nenaudojamas CO vėlinimas modelyje? Paslėpto intervalo viduje jis neprieinamas; baseline jį naudoja tik iki spragos.
- Kodėl pirmos 24 valandos atmetamos kiekvienoje dalyje? Kad istoriniai požymiai eksperimente nekirstų dalių ribų.
- Kuo skiriasi MAE ir blokų MAE? Pirmoji vienodai sveria valandas, antroji – blokus, kuriuose žinomų etalonų gali būti skirtingai.
- Kodėl neapibrėžtas precision nėra nulis? Kai nėra prognozuotų ekstremumų, vardiklis lygus nuliui.
- Ar q95 yra pavojingos taršos norma? Ne, tik mokymo skirstinio statistinė riba.
- Ar geras streso testo rezultatas leidžia diegti? Ne; reikia naujos vietos, naujo laikotarpio ir patikimo etalono patikros.
- Kaip pagrįstas AI indėlis? Kodo testais, duomenų kilme ir apskaičiuotais failais, ne AI teiginiu.
