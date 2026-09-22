"""CSV sutartis, struktūrinis valymas ir kilmės auditas."""
import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd

TARGET = 'CO(GT)'
SENSORS = ['PT08.S1(CO)', 'PT08.S2(NMHC)', 'PT08.S3(NOx)', 'PT08.S4(NO2)', 'PT08.S5(O3)']
CHANNELS = SENSORS + ['T', 'RH', 'AH']
URL = 'https://archive.ics.uci.edu/static/public/360/air%2Bquality.zip'

def download(path):
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(URL, timeout=60) as response:
            archive = zipfile.ZipFile(io.BytesIO(response.read()))
        names = [n for n in archive.namelist() if n.endswith('AirQualityUCI.csv')]
        if len(names) != 1:
            raise ValueError('UCI archyve nerastas vienintelis AirQualityUCI.csv')
        path.write_bytes(archive.read(names[0]))
    return path

def load_data(path, require_target=True):
    path = Path(path)
    raw = pd.read_csv(path, sep=';', decimal=',')
    original_rows = len(raw)
    raw = raw.dropna(how='all').dropna(axis=1, how='all')
    if not {'Date', 'Time'}.issubset(raw.columns):
        raise ValueError('Reikalingi Date ir Time stulpeliai (UCI CSV formatas).')
    absent = set(CHANNELS + ([TARGET] if require_target else [])) - set(raw.columns)
    if absent:
        raise ValueError(f'Trūksta stulpelių: {sorted(absent)}')
    ts = pd.to_datetime(raw.Date.astype(str) + ' ' + raw.Time.astype(str),
                        format='%d/%m/%Y %H.%M.%S', errors='coerce')
    if ts.isna().any() or (ts.dt.minute.ne(0) | ts.dt.second.ne(0)).any():
        raise ValueError('Neteisinga arba ne valandinė laiko žyma; taisykite CSV.')
    cols = CHANNELS + ([TARGET] if TARGET in raw else [])
    data = raw[cols].apply(pd.to_numeric, errors='coerce').replace([-200, np.inf, -np.inf], np.nan)
    data.index = pd.DatetimeIndex(ts, name='timestamp')
    # Kiekvieno dubliuoto laiko prieštaringas kanalas tampa neprieinamas.
    conflicts = int(data.groupby(level=0).nunique().gt(1).sum().sum())
    duplicates = int(data.index.duplicated().sum())
    if duplicates:
        data = data.groupby(level=0).agg(lambda s: s.dropna().iloc[0] if s.nunique() == 1 else np.nan)
    data = data.sort_index()
    if data.empty:
        raise ValueError('CSV neturi duomenų.')
    before_grid = len(data)
    data = data.reindex(pd.date_range(data.index.min(), data.index.max(), freq='h', name='timestamp'))
    if TARGET not in data:
        data[TARGET] = np.nan
    audit = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), source_url=URL,
                 original_rows=original_rows, hourly_rows=len(data), duplicate_rows=duplicates,
                 conflicting_cells=conflicts, inserted_hours=len(data)-before_grid,
                 missing_by_column=data.isna().sum().to_dict(), start=str(data.index.min()),
                 end=str(data.index.max()), timezone='Naive local time; DST not inferred')
    return data, audit
