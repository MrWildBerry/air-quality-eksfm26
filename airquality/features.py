"""Plano (1), (2): 32 matavimai + 32 kaukės + 4 cikliniai požymiai."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from .load import CHANNELS

def make_features(data, lags=True, masks=True):
    # Reindex pagal tikslų t-k laiką veikia ir nepilname laiko tinklelyje.
    values = data[CHANNELS].copy()
    if lags:
        for lag in (1, 3, 24):
            previous = data[CHANNELS].reindex(data.index - pd.Timedelta(hours=lag))
            previous.index = data.index
            values = pd.concat([values, previous.add_suffix(f'_lag{lag}')], axis=1)
    parts = [values]
    if masks:
        parts.append(values.isna().astype(float).add_suffix('_missing'))
    clock = pd.DataFrame(index=data.index)
    for name, v, period in [('hour', data.index.hour, 24), ('weekday', data.index.dayofweek, 7)]:
        clock[name + '_sin'] = np.sin(2 * np.pi * v / period)
        clock[name + '_cos'] = np.cos(2 * np.pi * v / period)
    return pd.concat(parts + [clock], axis=1)

class Prepare(BaseEstimator, TransformerMixin):
    """Tik mokymo medianos; SVR standartizuoja tik matavimų stulpelius."""
    def __init__(self, scale=False):
        self.scale = scale

    def fit(self, X, y=None):
        self.columns_ = list(X.columns)
        self.measurements_ = [c for c in X if not c.endswith(('_missing', '_sin', '_cos'))]
        self.empty_columns_ = [c for c in self.measurements_ if X[c].isna().all()]
        self.medians_ = X[self.measurements_].median().fillna(0)
        filled = X[self.measurements_].fillna(self.medians_)
        self.means_ = filled.mean()
        self.scales_ = filled.std(ddof=0).replace(0, 1)
        return self

    def transform(self, X):
        result = X[self.columns_].copy()
        result[self.measurements_] = result[self.measurements_].fillna(self.medians_)
        if self.scale:
            result[self.measurements_] = (result[self.measurements_] - self.means_) / self.scales_
        return result.to_numpy(dtype=float)
