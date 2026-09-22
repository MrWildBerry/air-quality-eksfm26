"""Ištisi nesikertantys blokai; jutikliai slepiami prieš vėlinimus."""
import numpy as np
from .load import SENSORS, TARGET

def block_mask(data, length, seed, coverage=.2, warmup=24, mode='random', threshold=None):
    rng = np.random.default_rng(seed)
    ids = np.full(len(data), -1, dtype=int)
    starts = np.arange(warmup, len(data) - length + 1)
    if mode == 'morning':
        starts = starts[data.index[starts].hour == 7]
    elif mode == 'extreme':
        starts = np.array([s for s in starts if (data[TARGET].iloc[s:s+length] >= threshold).any()])
    target = max(1, round((len(data) - warmup) * coverage / length))
    count = 0
    for start in rng.permutation(starts):
        if (ids[start:start+length] >= 0).any():
            continue
        ids[start:start+length] = count
        count += 1
        if count == target:
            break
    return ids

def corrupt(data, ids, scenario, seed, sensor_std):
    result = data.copy()
    result.loc[ids >= 0, TARGET] = np.nan
    if scenario == 'B_S1':
        result.loc[ids >= 0, SENSORS[0]] = np.nan
    elif scenario == 'B_all':
        result.loc[ids >= 0, SENSORS] = np.nan
    elif scenario == 'noise':
        result[SENSORS[0]] += np.random.default_rng(seed).normal(0, .1 * sensor_std, len(data))
    elif scenario == 'drift':
        result[SENSORS[0]] += np.linspace(0, .5 * sensor_std, len(data))
    return result
