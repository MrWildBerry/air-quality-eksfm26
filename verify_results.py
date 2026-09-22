"""Nepriklausomos rezultatų vientisumo ir prognozavimo patikros."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from airquality.load import load_data, TARGET, CHANNELS
from airquality.split import split_data
from airquality.masks import block_mask
from predict import predict_file

def verify(root):
    root=Path(root)
    pred=pd.read_csv(root/'predictions.csv.gz',parse_dates=['timestamp'])
    scores=pd.read_csv(root/'metrics.csv')
    config=json.loads((root/'config_used.json').read_text(encoding='utf-8'))
    data,audit=load_data(config['data'])
    pieces,_=split_data(data,config['warmup'])
    saved=json.loads((root/'data_audit.json').read_text(encoding='utf-8'))
    assert audit['sha256']==saved['sha256']
    assert pred.co_hat_mg_m3.ge(0).all() and np.isfinite(pred.co_hat_mg_m3).all()
    assert pred.y_true.notna().all()
    assert pred.timestamp.min()>=pieces['test'].index[24]
    np.testing.assert_allclose(pred.y_true.to_numpy(),data[TARGET].reindex(pred.timestamp).to_numpy())
    matched=0
    for keys,f in pred.groupby(['source','scenario','length','mask_seed']):
        name,scenario,length,seed=keys
        row=scores[(scores.source==name)&(scores.scenario==scenario)&(scores.length==length)&(scores.mask_seed==seed)].iloc[0]
        # Atskirai nuo evaluate.py apskaičiuojama MAE ir blokų MAE.
        absolute=np.abs(f.co_hat_mg_m3.to_numpy()-f.y_true.to_numpy())
        np.testing.assert_allclose(absolute.mean(),row.mae,rtol=1e-12)
        block_values=[np.abs(g.co_hat_mg_m3-g.y_true).mean() for _,g in f.groupby('block_id')]
        np.testing.assert_allclose(np.mean(block_values),row.block_mae,rtol=1e-12)
        assert len(f)==row.n
        matched+=1
    for _,f in pred.groupby(['scenario','length','mask_seed']):
        expected=f[f.source=='RF'].timestamp.sort_values().to_numpy()
        for name in ('SVR','last','hour_mean'):
            np.testing.assert_array_equal(expected,f[f.source==name].timestamp.sort_values().to_numpy())
    masks=pd.read_csv(root/'masks.csv.gz',parse_dates=['timestamp'])
    for (length,seed),f in masks[masks.scenario=='A'].groupby(['length','mask_seed']):
        expected=block_mask(pieces['test'],int(length),int(seed),config['coverage'],config['warmup'])
        np.testing.assert_array_equal(f.block_id.to_numpy(),expected)
    sample=Path('examples/unseen_format.csv')
    sample.parent.mkdir(exist_ok=True)
    d=pieces['test'].iloc[100:148][CHANNELS].copy()
    d.insert(0,'Time',d.index.strftime('%H.%M.%S'))
    d.insert(0,'Date',d.index.strftime('%d/%m/%Y'))
    d.to_csv(sample,index=False,sep=';',decimal=',')
    inference=predict_file(sample,root/'models/selected.joblib',root/'example_predictions.csv')
    assert len(inference)==48 and np.isfinite(inference.co_hat_mg_m3).all()
    summary=dict(status='passed',metric_rows_checked=matched,prediction_rows_checked=len(pred),
                 no_target_inference_rows=len(inference),sha256_match=True,common_evaluation_timestamps=True,
                 masks_reproduced=True,nonnegative_finite_predictions=True,independent_mae_recalculation=True)
    (root/'verification.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',default='results')
    verify(parser.parse_args().results)
