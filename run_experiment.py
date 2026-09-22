"""Vienas pilno eksperimento paleidimas: python run_experiment.py --config config.yaml."""
import os
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_name, '4')
import argparse
import importlib.metadata
import json
import platform
import shutil
import sys
import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import psutil
import yaml
from sklearn.model_selection import ParameterGrid
from airquality.load import download, load_data, CHANNELS, SENSORS, TARGET
from airquality.split import split_data
from airquality.features import make_features
from airquality.baselines import fit_baselines, predict_baselines
from airquality.masks import block_mask, corrupt
from airquality.models import predict, verify_forest_formula
from airquality.train import fit_limited
from airquality.evaluate import metrics, quality, choose, paired_bootstrap

def write_json(path, value):
    # Strict JSON: numpy scalars and undefined quantities converted explicitly.
    def clean(v):
        if isinstance(v, dict): return {str(k): clean(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)): return [clean(x) for x in v]
        if isinstance(v, np.generic): return clean(v.item())
        if isinstance(v, float) and not np.isfinite(v): return None
        return v
    Path(path).write_text(json.dumps(clean(value), ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def mean_metric(rows, key):
    a = np.array([r.get(key, np.nan) for r in rows], dtype=float)
    return float(np.nanmean(a)) if np.isfinite(a).any() else np.nan

def run(config_path, output_override=None):
    started = time.monotonic()
    cfg = yaml.safe_load(Path(config_path).read_text(encoding='utf-8'))
    out = Path(output_override or cfg['output']).resolve()
    # Naujas paleidimas nekeičia ankstesnių rezultatų.
    if out.exists() and any(out.iterdir()):
        out = out.with_name(out.name + '_' + time.strftime('%Y%m%d_%H%M%S'))
    out.mkdir(parents=True, exist_ok=False) if not out.exists() else None
    models_dir = out / 'models'
    models_dir.mkdir()
    work = out / 'training'
    work.mkdir()
    cfg['output'] = str(out)
    write_json(out / 'config_used.json', cfg)
    deadline = started + cfg['total_budget_seconds']
    data, audit = load_data(download(cfg['data']))
    write_json(out / 'data_audit.json', audit)
    pieces, split = split_data(data, cfg['warmup'])
    write_json(out / 'split.json', split)
    train = pieces['train']
    eligible = train[TARGET].notna() & (np.arange(len(train)) >= cfg['warmup'])
    y = train.loc[eligible, TARGET]
    X = make_features(train).loc[eligible]
    if len(y) < 100: raise ValueError('Per mažai mokymo etalonų.')
    q = float(y.quantile(.95))
    state = fit_baselines(y)
    train_min, train_max = train.loc[eligible, SENSORS].min(), train.loc[eligible, SENSORS].max()
    sensor_std = float(train.loc[eligible, SENSORS[0]].std(ddof=0))
    if not np.isfinite(sensor_std): sensor_std = 0.
    bounds = dict(min=train_min, max=train_max)
    model_info, tuning, failures, mask_audit = [], [], [], []
    validation = pieces['validation']
    val_cases = []
    for seed in cfg['mask_seeds']:
        ids = block_mask(validation, 24, seed, cfg['coverage'], cfg['warmup'])
        visible = corrupt(validation, ids, 'A', seed, sensor_std)
        val_cases.append((seed, ids, visible, make_features(visible)))
    def frame_for(original, visible, ids, pred, clipped, features, source):
        f = pd.DataFrame(dict(timestamp=original.index, y_true=original[TARGET].to_numpy(),
                              co_hat_mg_m3=pred, block_id=ids, clipped=clipped,
                              quality_flag=quality(visible, train_min, train_max, features), source=source))
        return f[(ids >= 0) & original[TARGET].notna().to_numpy()].copy()
    baseline_rows = []
    for name in ('last', 'hour_mean'):
        scores, elapsed = [], 0.
        for seed, ids, visible, features in val_cases:
            t = time.perf_counter()
            pred = predict_baselines(visible[TARGET], state)[name]
            elapsed += time.perf_counter()-t
            scores.append(metrics(frame_for(validation, visible, ids, pred, np.zeros(len(pred), bool), features, name), q))
        baseline_rows.append(dict(id=name, mae=mean_metric(scores, 'mae'), recall=mean_metric(scores, 'recall'), seconds=elapsed))
    best_baseline = choose(baseline_rows)
    winners, selected_rows = {}, []
    for kind in ('RF', 'SVR'):
        candidates = []
        for number, params in enumerate(ParameterGrid(cfg[kind.lower()])):
            ident = f'{kind}_{number:02d}'
            if time.monotonic() > deadline:
                failures.append(dict(id=ident, status='total_timeout', params=params)); continue
            print(f'Mokymas {ident}: {params}', flush=True)
            path = work / f'{ident}.joblib'
            model, timing = fit_limited(kind, params, X, y, path, cfg, cfg['model_seed'], deadline=deadline)
            info = dict(id=ident, kind=kind, params=params, **timing)
            model_info.append(info)
            if model is None:
                failures.append(info); continue
            scores, elapsed = [], 0.
            for seed, ids, visible, features in val_cases:
                t = time.perf_counter()
                pred, clipped = predict(model, features)
                elapsed += time.perf_counter()-t
                score = metrics(frame_for(validation, visible, ids, pred, clipped, features, kind), q)
                scores.append(score)
                tuning.append(dict(id=ident, kind=kind, mask_seed=seed, **score))
            candidates.append(dict(id=ident, mae=mean_metric(scores, 'mae'), recall=mean_metric(scores, 'recall'),
                                   seconds=timing['fit_seconds'] + elapsed, params=params, path=str(path)))
            pd.DataFrame(tuning).to_csv(out / 'validation_metrics.csv', index=False)
            write_json(out / 'training_audit.json', model_info)
        ident = choose(candidates)
        row = next(r for r in candidates if r['id'] == ident)
        winners[kind] = joblib.load(row['path'])
        selected_rows.append(row)
    chosen_id = choose(selected_rows)
    chosen = chosen_id.split('_')[0]
    selected = dict(main_model=chosen, baseline=best_baseline, threshold_q95=q,
                    candidates=selected_rows, baseline_validation=baseline_rows,
                    rule='A/24h mean MAE; <=2% tie: recall then fit+prediction seconds',
                    refit_after_validation=False)
    write_json(out / 'selection.json', selected)  # Testas dar nevertintas.
    print(f'Prieš testą užfiksuota: {chosen}; baseline: {best_baseline}', flush=True)
    for kind, model in winners.items():
        joblib.dump(dict(model=model, model_version=f'{kind}-seed42-{audit["sha256"][:12]}',
                         source=kind, train_min=train_min, train_max=train_max, threshold=q,
                         baseline=state, columns=list(X.columns)), models_dir / f'{kind}.joblib', compress=3)
    shutil.copy2(models_dir / f'{chosen}.joblib', models_dir / 'selected.joblib')
    write_json(out / 'formula_check.json', verify_forest_formula(winners['RF'], X.iloc[:5]))
    write_json(out / 'preprocessing.json', {k: dict(medians=m.named_steps['prepare'].medians_.to_dict(),
               empty_columns=m.named_steps['prepare'].empty_columns_, columns=m.named_steps['prepare'].columns_,
               means=m.named_steps['prepare'].means_.to_dict(), scales=m.named_steps['prepare'].scales_.to_dict()) for k,m in winners.items()})
    variants = {k: (m, True, True) for k,m in winners.items()}
    rf_params = next(r['params'] for r in selected_rows if r['id'].startswith('RF'))
    svr_params = next(r['params'] for r in selected_rows if r['id'].startswith('SVR'))
    extra = [('RF_no_lags', 'RF', False, True, 42, None, rf_params),
             ('RF_no_masks', 'RF', True, False, 42, None, rf_params),
             ('RF_seed17', 'RF', True, True, 17, None, rf_params),
             ('RF_seed101', 'RF', True, True, 101, None, rf_params),
             ('SVR_W', 'SVR', True, True, 42, np.where(y >= q, 3., 1.), svr_params)]
    for name, kind, lags, masks, seed, weights, params in extra:
        print(f'Papildomas bandymas: {name}', flush=True)
        if time.monotonic() > deadline:
            failures.append(dict(id=name, status='total_timeout')); continue
        features = make_features(train, lags, masks).loc[eligible]
        model, timing = fit_limited(kind, params, features, y, work/f'{name}.joblib', cfg, seed, weights, deadline)
        model_info.append(dict(id=name, kind=kind, params=params, **timing))
        if model is None: failures.append(dict(id=name, **timing))
        else: variants[name] = (model, lags, masks)
    test = pieces['test']
    frames, results, saved_masks = [], [], []
    case_specs = [(s,L,seed,'random') for s in ['A','B_S1','B_all','noise','drift'] for L in cfg['lengths'] for seed in cfg['mask_seeds']]
    case_specs += [(s,24,seed,mode) for s,mode in [('morning','morning'),('extreme','extreme')] for seed in cfg['mask_seeds']]
    for scenario, length, seed, mode in case_specs:
        if time.monotonic() > deadline:
            failures.append(dict(id=f'{scenario}_{length}_{seed}', status='total_timeout')); continue
        ids = block_mask(test, length, seed, cfg['coverage'], cfg['warmup'], mode, q)
        visible = corrupt(test, ids, scenario, seed, sensor_std)
        all_features = make_features(visible)
        mask_audit.append(dict(scenario=scenario, length=length, mask_seed=seed, hidden_hours=int((ids>=0).sum()),
                               coverage=float((ids>=0).sum()/(len(test)-cfg['warmup'])), blocks=len(set(ids)-{-1})))
        saved_masks.append(pd.DataFrame(dict(timestamp=test.index, scenario=scenario, length=length, mask_seed=seed, block_id=ids)))
        predictions = {}
        t = time.perf_counter()
        baselines = predict_baselines(visible[TARGET], state)
        baseline_seconds = time.perf_counter()-t
        for name, p in baselines.items(): predictions[name] = (p, np.zeros(len(p), bool), baseline_seconds, all_features)
        for name, (model, lags, masks) in variants.items():
            # abliacijų ir modelio sėklų jautrumas: tie patys A ir B blokai.
            if name.startswith('RF_') and scenario not in ('A', 'B_S1', 'B_all'): continue
            features = all_features if lags and masks else make_features(visible, lags, masks)
            t = time.perf_counter()
            p, clip = predict(model, features)
            predictions[name] = (p, clip, time.perf_counter()-t, features)
        for name,(p,clip,seconds,features) in predictions.items():
            frame = frame_for(test, visible, ids, p, clip, features, name)
            frame['scenario'], frame['length'], frame['mask_seed'] = scenario, length, seed
            frame['model_version'] = f'{name}-{audit["sha256"][:12]}'
            frames.append(frame)
            results.append(dict(source=name, scenario=scenario, length=length, mask_seed=seed,
                                predict_seconds=seconds, **metrics(frame,q)))
        print(f'Testas {scenario}, {length} val., kaukė {seed}', flush=True)
    pred = pd.concat(frames, ignore_index=True)
    pred.to_csv(out/'predictions.csv.gz', index=False, compression='gzip')
    pd.DataFrame(results).to_csv(out/'metrics.csv', index=False)
    pd.concat(saved_masks, ignore_index=True).to_csv(out/'masks.csv.gz', index=False, compression='gzip')
    pd.concat([pd.DataFrame(dict(timestamp=validation.index, mask_seed=seed, block_id=ids)) for seed,ids,_,_ in val_cases]).to_csv(out/'validation_masks.csv', index=False)
    write_json(out/'mask_audit.json', mask_audit)
    write_json(out/'bootstrap.json', paired_bootstrap(pred, best_baseline, cfg['bootstrap_samples']))
    write_json(out/'training_audit.json', model_info)
    write_json(out/'incomplete.json', failures)
    versions = {p:importlib.metadata.version(p) for p in ['numpy','pandas','scikit-learn','matplotlib','PyYAML','psutil','joblib','scipy']}
    write_json(out/'environment.json', dict(python=sys.version, platform=platform.platform(), processor=platform.processor(),
               logical_cpus=psutil.cpu_count(), ram_gb=psutil.virtual_memory().total/1024**3,
               versions=versions, elapsed_seconds=time.monotonic()-started,
               budget_seconds=cfg['total_budget_seconds'], threads=cfg['threads'],
               parent_peak_rss_mb=getattr(psutil.Process().memory_info(), 'peak_wset', psutil.Process().memory_info().rss)/1024**2))
    from airquality.report import build_report
    build_report(out)
    print(f'Baigta. Ataskaita: {out / "ataskaita.html"}', flush=True)
    return out

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config.yaml')
    parser.add_argument('--output', help='Naujas rezultatų aplankas')
    args = parser.parse_args()
    run(args.config, args.output)
