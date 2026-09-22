"""Ataskaita generuojama tik iš išsaugotų prognozių ir metrikų."""
import html
import os
import tempfile
import json
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'air-quality-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLORS = {'RF':'#087f8c','SVR':'#6b4bc3','last':'#d78924','hour_mean':'#64748b'}
LABELS = {'A':'Tik CO spragos', 'B_S1':'Vieno jutiklio gedimas', 'B_all':'Visų PT08 gedimas',
          'noise':'Triukšmas', 'drift':'Dreifas', 'morning':'Spragos nuo 7 val.', 'extreme':'Pikų streso testas'}

def build_report(output):
    out = Path(output)
    plots = out/'plots'; plots.mkdir(exist_ok=True)
    metrics = pd.read_csv(out/'metrics.csv')
    pred = pd.read_csv(out/'predictions.csv.gz',parse_dates=['timestamp'])
    selection=json.loads((out/'selection.json').read_text(encoding='utf-8'))
    env=json.loads((out/'environment.json').read_text(encoding='utf-8'))
    audit=json.loads((out/'data_audit.json').read_text(encoding='utf-8'))
    boot=json.loads((out/'bootstrap.json').read_text(encoding='utf-8'))
    incomplete=json.loads((out/'incomplete.json').read_text(encoding='utf-8'))
    q=selection['threshold_q95']; baseline=selection['baseline']; main=selection['main_model']
    group=metrics.groupby(['scenario','length','source'],sort=False)
    summary=group[['mae','block_mae','recall','precision','extreme_mae','extreme_bias','predict_seconds','warning_fraction']].mean().reset_index()
    summary.to_csv(out/'summary.csv',index=False)
    primary=summary.query("scenario == 'A' and length == 24").set_index('source')
    rf=primary.loc['RF']; base=primary.loc[baseline]
    gain=1-rf.mae/base.mae if base.mae else np.nan
    recall_delta=rf.recall-base.recall
    evaluable=np.isfinite(gain) and np.isfinite(recall_delta)
    passed=evaluable and gain>=.10 and recall_delta>=-.05
    h1='Patvirtinta pagal projekto kriterijus' if passed else ('Nepatvirtinta' if evaluable else 'Neįvertinama')
    h1_data=dict(status=h1,rf_mae=float(rf.mae),baseline_mae=float(base.mae),relative_mae_reduction=float(gain),recall_difference=float(recall_delta))
    (out/'hypothesis.json').write_text(json.dumps({k:(v if not isinstance(v,float) or np.isfinite(v) else None) for k,v in h1_data.items()},ensure_ascii=False,indent=2),encoding='utf-8')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.titleweight':'bold'})
    fig, axes=plt.subplots(1,2,figsize=(12,4.2))
    for source,color in COLORS.items():
        d=summary[(summary.scenario=='A') & (summary.source==source)].sort_values('length')
        axes[0].plot(d.length,d.mae,'o-',label=source,color=color,lw=2)
        axes[1].plot(d.length,d.recall,'o-',label=source,color=color,lw=2)
    for ax in axes:
        ax.set_xlabel('Paslėpto intervalo trukmė, val.'); ax.set_xticks([6,24,72]); ax.grid(alpha=.15)
    axes[0].set_ylabel('MAE, mg/m³'); axes[0].set_title('Koncentracijos atkūrimo klaida')
    axes[1].set_ylabel('Ekstremumų recall'); axes[1].set_title(f'Ekstremumai: CO ≥ {q:.2f} mg/m³'); axes[1].set_ylim(-.03,1.03)
    axes[0].legend(frameon=False); fig.tight_layout(); fig.savefig(plots/'gap_lengths.png',dpi=160); plt.close(fig)
    focus=pred.query("scenario == 'A' and length == 24").copy()
    focus['month']=focus.timestamp.dt.strftime('%Y-%m')
    focus['abs_error']=(focus.co_hat_mg_m3-focus.y_true).abs()
    # Vienodas kiekvienos kaukės svoris. Kaukių persidengimas nėra papildomi nepriklausomi duomenys.
    monthly=focus.groupby(['source','mask_seed','month']).abs_error.mean().groupby(['source','month']).mean().unstack(0)
    monthly.to_csv(out/'monthly_mae.csv')
    fig,ax=plt.subplots(figsize=(10,4))
    monthly[[c for c in COLORS if c in monthly]].plot.bar(ax=ax,color=[COLORS[c] for c in COLORS if c in monthly],rot=0)
    ax.set(xlabel='Mėnuo',ylabel='MAE, mg/m³',title='Klaida pagal mėnesį • A scenarijus, 24 val.')
    ax.legend(frameon=False); fig.tight_layout(); fig.savefig(plots/'monthly.png',dpi=160); plt.close(fig)
    robust=summary[(summary.length==24)&summary.source.isin(COLORS)].pivot(index='scenario',columns='source',values='mae')
    robust=robust.reindex([s for s in LABELS if s in robust.index]).rename(index=LABELS)
    fig,ax=plt.subplots(figsize=(11,5))
    robust[list(COLORS)].plot.barh(ax=ax,color=list(COLORS.values()))
    ax.set(xlabel='MAE, mg/m³',ylabel='',title='Atsparumas • 24 val. spragos'); ax.legend(frameon=False,ncol=4,loc='lower center',bbox_to_anchor=(.5,1.08))
    fig.tight_layout(); fig.savefig(plots/'robustness.png',dpi=160); plt.close(fig)
    rf_focus=focus[focus.source=='RF'].copy()
    block_errors=rf_focus.groupby(['mask_seed','block_id']).agg(start=('timestamp','min'),end=('timestamp','max'),
                    n=('y_true','size'),mae=('abs_error','mean'),max_error=('abs_error','max'),
                    limited_fraction=('quality_flag',lambda s:s.eq('ribotas pagrįstumas').mean()),
                    peak_true=('y_true','max'),peak_predicted=('co_hat_mg_m3','max')).reset_index().sort_values('mae',ascending=False)
    worst=block_errors.head(5); worst.to_csv(out/'worst_5_intervals.csv',index=False)
    if not worst.empty:
        worst_one=worst.iloc[0]
        episode=focus[(focus.mask_seed==worst_one.mask_seed)&(focus.block_id==worst_one.block_id)]
        fig,ax=plt.subplots(figsize=(11,4.5))
        truth=episode[episode.source=='RF'].sort_values('timestamp')
        ax.plot(truth.timestamp,truth.y_true,color='#111827',lw=2.5,label='Etalonas')
        for source,color in COLORS.items():
            d=episode[episode.source==source].sort_values('timestamp')
            ax.plot(d.timestamp,d.co_hat_mg_m3,label=source,color=color)
        ax.axhline(q,color='#dc4b54',ls='--',alpha=.65,label='Mokymo q95')
        ax.set(ylabel='CO, mg/m³',title='Didžiausios RF vidutinės klaidos intervalas (A, 24 val.)')
        ax.legend(frameon=False,ncol=3); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(plots/'worst_interval.png',dpi=160); plt.close(fig)
    missed=[]
    for keys,f in pred.groupby(['source','scenario','length','mask_seed']):
        f=f.sort_values('timestamp')
        f=f[(f.y_true>=q)&(f.co_hat_mg_m3<q)].copy()
        if f.empty: continue
        f['episode']=(f.timestamp.diff()!=pd.Timedelta(hours=1)).cumsum()
        for _,d in f.groupby('episode'):
            missed.append(dict(zip(['source','scenario','length','mask_seed'],keys))|dict(start=d.timestamp.min(),end=d.timestamp.max(),hours=len(d),
                          peak_true=d.y_true.max(),peak_predicted=d.co_hat_mg_m3.max(),mean_bias=(d.co_hat_mg_m3-d.y_true).mean()))
    pd.DataFrame(missed).to_csv(out/'missed_extreme_episodes.csv',index=False)
    keys=['timestamp','mask_seed','block_id']
    rf_pair=rf_focus[keys+['y_true','co_hat_mg_m3']].rename(columns={'co_hat_mg_m3':'rf_prediction'})
    base_pair=focus[focus.source==baseline][keys+['co_hat_mg_m3']].rename(columns={'co_hat_mg_m3':'baseline_prediction'})
    paired=rf_pair.merge(base_pair,on=keys,validate='one_to_one')
    paired['rf_error']=(paired.rf_prediction-paired.y_true).abs()
    paired['baseline_error']=(paired.baseline_prediction-paired.y_true).abs()
    better=paired[paired.baseline_error<paired.rf_error].copy()
    better['advantage']=better.rf_error-better.baseline_error
    better.sort_values('advantage',ascending=False).to_csv(out/'baseline_wins.csv',index=False)
    # Ataskaitos lentelėje sumos yra kaukės-valandos; unikalios valandos pateikiamos atskirai.
    counts=metrics.query("scenario == 'A' and length == 24 and source in ['RF','SVR','last','hour_mean']")
    columns=['source','mask_seed','n','blocks','tp','fn','fp','mae','block_mae','recall','precision']
    main_table=primary.loc[list(COLORS),['mae','block_mae','recall','precision','extreme_mae','extreme_bias','predict_seconds']].reset_index()
    ablations=summary[(summary.scenario.isin(['A','B_S1','B_all']))&(summary.length==24)&summary.source.isin(['RF','RF_no_lags','RF_no_masks','RF_seed17','RF_seed101','SVR','SVR_W'])]
    def table(d): return d.to_html(index=False,float_format=lambda n:f'{n:.4f}',na_rep='neapibrėžta',border=0,classes='results',escape=True)
    def number(n): return f'{n:.3f}' if np.isfinite(n) else 'neapibrėžta'
    main_mae=primary.loc[main,'mae']; main_gain=1-main_mae/base.mae if base.mae else np.nan
    drift=summary.query("scenario == 'drift' and length == 24").set_index('source').loc[main,'mae']
    allfail=summary.query("scenario == 'B_all' and length == 24").set_index('source').loc[main,'mae']
    selected_message=(f'Validavime parinktas {main}. Teste jo MAE {number(main_mae)} mg/m³, '
                      f'o užfiksuoto {baseline} metodo MAE {number(base.mae)} mg/m³; santykinis sumažėjimas {100*main_gain:.1f} %. '
                      'Tai yra šio chronologinio laikotarpio rezultatas; modelio pasirinkimas pagal testą nekeičiamas.')
    test_winner=primary.loc[list(COLORS),'mae'].idxmin()
    selected_message += (f' Mažiausią pagrindinių metodų testo MAE gavo {test_winner} ({primary.loc[test_winner,"mae"]:.3f} mg/m³). '
                         'Validavime RF ir SVR MAE skyrėsi mažiau kaip 2 %, todėl pasirinkimą nulėmė didesnis SVR recall. '
                         'Atrankos taisyklė negarantuoja, kad pasirinktas modelis laimės kitame laikotarpyje.')
    interpretation=(f'Esant visų PT08 kanalų gedimui {main} MAE yra {number(allfail)}, o sintetiniam S1 dreifui – {number(drift)} mg/m³. '
                    'Skirtumai parodo priklausomybę nuo prieinamų signalų. Netiesiniai modeliai gali panaudoti vienalaikius jutiklių ir meteorologijos ryšius, '
                    'o pastovi paskutinė CO reikšmė ilgame bloke nebeseka pokyčių. Tai mechanistinis paaiškinimas, ne priežastinio ryšio įrodymas. '
                    'RF lapų vidurkinimas ir reti ekstremumai gali mažinti pikų įverčius; ekstremumų ženklinė paklaida lentelėje leidžia patikrinti kryptį.')
    report=f'''<!doctype html><html lang="lt"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Air Quality • Galutinio darbo rezultatai</title><style>
:root{{--ink:#17283b;--muted:#586b7c;--accent:#087f8c}}*{{box-sizing:border-box}}body{{margin:0;background:#f1f5f7;color:var(--ink);font:16px/1.6 'Segoe UI',Arial,sans-serif}}
header{{background:#102a38;color:white;padding:52px max(6vw,24px)}}header small{{color:#75d6cd;letter-spacing:2px}}h1{{font-size:42px;line-height:1.15;margin:14px 0}}header p{{color:#c9d9df;max-width:850px}}
main{{max-width:1240px;margin:32px auto;padding:0 24px}}section{{background:white;padding:30px;margin:24px 0;border-radius:14px;box-shadow:0 4px 22px #17344908}}h2{{font-size:25px;margin-top:0}}h3{{font-size:18px}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:15px}}.card{{background:white;padding:22px;border-radius:12px;border-top:4px solid var(--accent)}}.card strong{{display:block;font-size:27px}}.card span{{font-size:13px;color:var(--muted)}}
.scroll{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}}th{{background:#eaf1f4;text-align:left}}td,th{{padding:9px 12px;border-bottom:1px solid #e5edf0}}img{{width:100%;height:auto}}a{{color:#087f8c}}.note{{padding:15px;background:#eff8f7;border-left:4px solid #087f8c}}code{{background:#eaf1f4;padding:2px 5px}}nav a{{margin-right:18px}}footer{{font-size:13px;color:var(--muted);padding:20px}}@media(max-width:750px){{.cards{{grid-template-columns:1fr 1fr}}h1{{font-size:30px}}section{{padding:18px}}}}@media print{{body{{background:white}}section{{box-shadow:none;break-inside:avoid}}nav{{display:none}}}}
</style><header><small>DOMINYKAS KUBLICKAS · EKSfm-26 · INTELEKTUALIOSIOS SISTEMOS</small><h1>Oro kokybės būsenos atkūrimas</h1><p>CO koncentracijos įvertinimas esant trūkstamiems ir triukšmingiems jutiklių duomenims. Galutinio eksperimento ataskaita, automatiškai sudaryta iš išsaugotų rezultatų.</p></header><main>
<nav><a href="#results">Rezultatai</a><a href="#robust">Atsparumas</a><a href="#errors">Klaidos</a><a href="#audit">Atkuriamumas</a></nav>
<div class="cards"><div class="card"><span>VALIDAVIME PARINKTA</span><strong>{main}</strong></div><div class="card"><span>TESTO MAE · A / 24 VAL.</span><strong>{main_mae:.3f}</strong><span>mg/m³ · trijų kaukių vidurkis</span></div><div class="card"><span>EKSTREMUMŲ SLENKSTIS</span><strong>{q:.2f}</strong><span>mg/m³ · mokymo q95</span></div><div class="card"><span>EKSPERIMENTO TRUKMĖ</span><strong>{env['elapsed_seconds']/60:.1f} min.</strong><span>be ataskaitos braižymo</span></div></div>
<section><h2>Rezultatas ir hipotezė</h2><p>{selected_message}</p><p class="note"><b>H1: {h1}.</b> RF MAE sumažėjimas prieš {baseline}: {100*gain:.1f} %; recall skirtumas: {number(recall_delta)}. Reikalauta bent 10 % mažesnės MAE ir recall sumažėjimo ne daugiau kaip 0,05.</p><p>{interpretation}</p></section>
<section id="results"><h2>Vienodos palyginimo sąlygos</h2><p>Chronologinis skaidymas 60/20/20 pagal visas laiko eilutes. Kiekvienos dalies pirmos 24 valandos nevertinamos. Modeliai, medianos, skalės ir q95 mokomi tik pirmoje dalyje; po validavimo nepermokoma. Įvestyje nėra CO ar kitų etaloninių GT stulpelių. Kiekvienam ilgiui ir sėklai visi metodai naudoja tuos pačius blokus.</p>
<h3>Pagrindinis palyginimas · A scenarijus · 24 val.</h3><div class="scroll">{table(main_table)}</div><p>MAE ir blokų MAE vienetai mg/m³. Lentelėje vienodai sverti trijų kaukių rodiklių vidurkiai; tai nėra trys nepriklausomi duomenų rinkiniai. Precision be prognozuotų ekstremumų yra neapibrėžta. predict_seconds apima visos testo dalies prognozavimą, ne vieną eilutę.</p><img src="plots/gap_lengths.png" alt="MAE ir ekstremumų recall pagal spragos trukmę"><img src="plots/monthly.png" alt="Klaida pagal mėnesį">
<details><summary>Vertintų valandų, blokų ir ekstremumų skaičiai</summary><div class="scroll">{table(counts[columns])}</div><p>Unikalių žinomų testo valandų bent vienoje A/24 kaukėje: {rf_focus.timestamp.nunique()}. Persidengiančios kaukės šio skaičiaus nedidina.</p></details></section>
<section id="robust"><h2>Atsparumas ir abliacijos</h2><p>B_S1 slepia pirmą kanalą, B_all visus penkis PT08. Triukšmo standartinis nuokrypis yra 0,1 mokymo S1 standartinio nuokrypio; dreifas didėja iki 0,5 jo dydžio. Morning blokai prasideda 7 val.; extreme yra retrospektyvus streso testas, kurio blokų atrankai naudojamas etalonas. Jis nedalyvauja modelio atrankoje.</p><img src="plots/robustness.png" alt="Metodų atsparumo palyginimas">
<p>RF_no_lags pašalina visus 24 istorinius matavimus ir jų kaukes (lieka 20 požymių). RF_no_masks pašalina 32 trūkumo kaukes (lieka 36). Parametrai išlaikomi. RF_seed17 ir RF_seed101 parodo modelio sėklos jautrumą; SVR_W taiko ekstremumų svorį 3 ir bazinės SVR parametrus.</p><div class="scroll">{table(ablations[['scenario','source','mae','block_mae','recall','precision','warning_fraction']])}</div>
<details><summary>Visi scenarijai ir spragų ilgiai</summary><div class="scroll">{table(summary)}</div></details></section>
<section id="errors"><h2>Klaidų analizė</h2><p>Žemiau – penki didžiausios RF blokų MAE intervalai A/24 bandyme. Sėkla žymi slėpimo kaukę; tarp kaukių intervalai gali persidengti.</p><div class="scroll">{table(worst)}</div><img src="plots/worst_interval.png" alt="Didžiausios klaidos intervalo prognozės">
<p>{baseline} turi mažesnę absoliučią klaidą nei RF {len(better)} iš {len(paired)} kaukės ir valandos porų ({100*len(better)/max(1,len(paired)):.1f} %). Tai nereiškia, kad jis turi mažesnę bendrą MAE. Artimas ankstesnis matavimas gali laimėti ramiu laikotarpiu, o prastos ar nepilnos įvestys gali bloginti RF.</p><p><a href="baseline_wins.csv">Visi baseline laimėjimo atvejai</a> · <a href="missed_extreme_episodes.csv">Visi nepastebėtų ekstremumų epizodai</a> · <a href="worst_5_intervals.csv">Penki klaidų intervalai</a></p>
<h3>Apytiksliai 95 % porinio bootstrap intervalai</h3><p>Skirtumas = RF MAE minus baseline MAE. Kiekvienai kaukei atskirai 1 000 kartų perrenkami ištisi 24 val. blokai. Neigiama reikšmė palanki RF. Kaukės neapjungiamos į tariamai nepriklausomą imtį.</p><div class="scroll">{table(pd.DataFrame(boot))}</div><p>Jei intervalas apima nulį, tai kaukei statistinio pranašumo neteigiama. Net ir nulio neapimantys intervalai yra apytiksliai dėl laikinės priklausomybės tarp blokų.</p></section>
<section><h2>Sprendimo ribos ir praktinis naudojimas</h2><p>Vienos senos Italijos matavimo vietos rezultatai neįrodo tinkamumo kitam miestui ar dabartiniams jutikliams. UCI rinkinyje nėra kelių stočių koordinačių. Dirbtinis žinomų etalonų slėpimas neleidžia išmatuoti tikrų natūralių spragų klaidos. Sintetinis dreifas neatkuria visų fizinio senėjimo mechanizmų. Nekoreguojamas neapibrėžtas vasaros laikas.</p><p>q95 yra statistinis ekstremumas, ne sveikatos ar teisinė norma. Kokybės žymos nėra pasikliautinieji intervalai. Nė vieno dabartinio PT08 kanalo nebuvimas arba bent vieno jo išėjimas už mokymo min-max ribų suteikia žymą „ribotas pagrįstumas“. Kitų įvesčių trūkumas žymimas atskirai. Neigiamos prognozės apribojamos ties 0; jų dalis išsaugoma metrikose.</p><p>Operatorius turi peržiūrėti riboto pagrįstumo intervalus ir lyginti su etalonu. Duomenų specialistas tikrina mėnesines klaidas ir dreifą; po naujo kalibravimo reikia naujo laike atskirto vertinimo. Finansinė grąža neskaičiuojama, nes nėra diegimo ir priežiūros sąnaudų duomenų.</p></section>
<section id="audit"><h2>Atkuriamumas ir auditas</h2><p>Duomenys: {audit['hourly_rows']} valandų, {html.escape(audit['start'])} – {html.escape(audit['end'])}. Įterptos valandos: {audit['inserted_hours']}; dublikatai: {audit['duplicate_rows']}. Faktinis CSV laikotarpis naudojamas vietoj aprašo datų.</p><p>Duomenų SHA-256: <code>{audit['sha256']}</code></p><p>Komanda: <code>python run_experiment.py --config config.yaml</code>. Priklausomybės: <code>requirements-lock.txt</code>. Sėklos: 17, 42, 101; pagrindinio modelio sėkla 42. Nebaigtų bandymų: {len(incomplete)}. <a href="incomplete.json">Sąrašas</a>.</p>
<p><a href="selection.json">Atrankos parametrai</a> · <a href="split.json">Laiko ribos</a> · <a href="metrics.csv">Visos metrikos</a> · <a href="formula_check.json">RF formulės patikra</a> · <a href="environment.json">Aplinka ir trukmė</a> · <a href="training_audit.json">Mokymo laikas ir atmintis</a></p><p>UCI šaltinis: <a href="https://archive.ics.uci.edu/dataset/360/air+quality">Air Quality</a>, Vito (2008), DOI 10.24432/C59K5F. Bibliografinis metodų pagrindimas pateiktas koliokviumo plane; šios ataskaitos skaičiai apskaičiuoti šiuo kodu.</p></section><footer>Ši ataskaita pagrindžia programinę egzamino dalį. Gyvas gynimas, dėstytojo nematytas bandymas ir savarankiškas paaiškinimas dar turi būti atlikti studento.</footer></main></html>'''
    (out/'ataskaita.html').write_text(report,encoding='utf-8')
    (out/'ISVADOS.txt').write_text(selected_message+'\n\nH1: '+h1+f'. RF MAE sumažėjimas: {gain:.2%}; recall skirtumas: {recall_delta:.4f}.\n\n'+interpretation+'\n\nIšsamiau: ataskaita.html.\n',encoding='utf-8')
