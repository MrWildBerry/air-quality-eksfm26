"""Klaidos, ekstremumai ir kokybės žymos; neapibrėžti santykiai = NaN."""
import numpy as np
import pandas as pd
from .load import CHANNELS, SENSORS

def metrics(frame, threshold):
    f = frame.dropna(subset=['y_true', 'co_hat_mg_m3']).copy()
    if f.empty:
        return dict(n=0, blocks=0, mae=np.nan, block_mae=np.nan, recall=np.nan, precision=np.nan)
    error = f.co_hat_mg_m3 - f.y_true
    actual, predicted = f.y_true >= threshold, f.co_hat_mg_m3 >= threshold
    tp, fn, fp = int((actual & predicted).sum()), int((actual & ~predicted).sum()), int((~actual & predicted).sum())
    return dict(n=len(f), blocks=int(f.block_id.nunique()), mae=float(error.abs().mean()),
                block_mae=float(error.abs().groupby(f.block_id).mean().mean()),
                rmse=float(np.sqrt((error**2).mean())), tp=tp, fn=fn, fp=fp,
                recall=tp/(tp+fn) if tp+fn else np.nan,
                precision=tp/(tp+fp) if tp+fp else np.nan,
                extreme_mae=float(error[actual].abs().mean()), extreme_bias=float(error[actual].mean()),
                warning_fraction=float(f.quality_flag.ne('atkurtas').mean()),
                clipped_fraction=float(f.clipped.mean()))

def quality(data, train_min, train_max, features):
    out = ((data[SENSORS] < train_min) | (data[SENSORS] > train_max)).any(axis=1)
    limited = data[SENSORS].isna().all(axis=1) | out
    missing = features.isna().any(axis=1)
    return np.where(limited, 'ribotas pagrįstumas', np.where(missing, 'trūksta dalies įvesčių', 'atkurtas'))

def choose(rows):
    """<=2% nuo geriausio MAE: recall, tada mokymo+prognozės laikas."""
    table = pd.DataFrame(rows)
    table = table[np.isfinite(table.mae)]
    if table.empty:
        raise RuntimeError('Nė vienas modelis nebaigė validavimo.')
    best = table.mae.min()
    tied = table[table.mae <= best * 1.02 + 1e-12].copy()
    tied['recall_sort'] = tied.recall.fillna(-1)
    return tied.sort_values(['recall_sort', 'seconds', 'id'], ascending=[False, True, True]).iloc[0]['id']

def paired_bootstrap(predictions, baseline, iterations=1000):
    results = []
    base = predictions.query("scenario == 'A' and length == 24")
    for seed, f in base.groupby('mask_seed'):
        rf = f[f.source == 'RF'].set_index('timestamp')
        bl = f[f.source == baseline].set_index('timestamp')
        if rf.empty or bl.empty:
            continue
        delta = (rf.co_hat_mg_m3-rf.y_true).abs() - (bl.co_hat_mg_m3-bl.y_true).abs()
        blocks = pd.DataFrame({'delta': delta, 'block': rf.block_id}).dropna().groupby('block').delta.agg(['sum', 'count'])
        if len(blocks) < 2:
            continue
        rng = np.random.default_rng(int(seed))
        samples = rng.integers(0, len(blocks), size=(iterations, len(blocks)))
        values = blocks['sum'].to_numpy()[samples].sum(axis=1) / blocks['count'].to_numpy()[samples].sum(axis=1)
        results.append(dict(mask_seed=int(seed), blocks=len(blocks), difference_mae=float(blocks['sum'].sum()/blocks['count'].sum()),
                            ci_low=float(np.quantile(values, .025)), ci_high=float(np.quantile(values, .975))))
    return results
