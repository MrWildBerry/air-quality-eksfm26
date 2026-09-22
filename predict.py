"""Prognozė naujam UCI formato CSV, nereikalaujant CO(GT)."""
import argparse
from pathlib import Path
import joblib
import pandas as pd
from airquality.load import load_data
from airquality.features import make_features
from airquality.models import predict
from airquality.evaluate import quality

def predict_file(csv_path, model_path, output_path):
    data,audit=load_data(csv_path,require_target=False)
    bundle=joblib.load(model_path)
    features=make_features(data)
    values,clipped=predict(bundle['model'],features)
    frame=pd.DataFrame(dict(timestamp=data.index,co_hat_mg_m3=values,source=bundle['source'],
                           quality_flag=quality(data,bundle['train_min'],bundle['train_max'],features),
                           model_version=bundle['model_version'],clipped=clipped))
    output=Path(output_path)
    if output.resolve()==Path(csv_path).resolve(): raise ValueError('Išvestis negali perrašyti įvesties.')
    output.parent.mkdir(parents=True,exist_ok=True)
    frame.to_csv(output,index=False,encoding='utf-8-sig')
    print(f'Išsaugota {len(frame)} prognozių: {output}')
    return frame

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,help='Date;Time;PT08...;T;RH;AH CSV')
    parser.add_argument('--model',default='results/models/selected.joblib')
    parser.add_argument('--output',default='predictions/new_predictions.csv')
    args=parser.parse_args()
    predict_file(args.input,args.model,args.output)
