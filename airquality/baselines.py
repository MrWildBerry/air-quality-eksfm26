"""Plano (5): last yra griežtai ankstesnis PRIEINAMAS etalonas."""
import numpy as np

def fit_baselines(train):
    valid = train.dropna()
    if valid.empty:
        raise ValueError('Mokymo dalyje nėra žinomų CO etalonų.')
    return {'hour': valid.groupby(valid.index.hour).mean().to_dict(), 'global': float(valid.mean())}

def predict_baselines(visible_target, state):
    hour = np.array([state['hour'].get(h, state['global']) for h in visible_target.index.hour])
    last = visible_target.shift(1).ffill().to_numpy()
    return {'hour_mean': hour, 'last': np.where(np.isnan(last), hour, last)}
