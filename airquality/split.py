"""60/20/20 ribos pagal visas valandas, prieš y filtravimą."""
from .load import TARGET

def split_data(data, warmup=24):
    n = len(data)
    a, b = int(n * .6), int(n * .8)
    pieces = dict(train=data.iloc[:a].copy(), validation=data.iloc[a:b].copy(), test=data.iloc[b:].copy())
    if min(map(len, pieces.values())) < warmup + 72:
        raise ValueError('Eksperimentui reikia ilgesnės valandinės sekos.')
    audit = {name: dict(start=str(d.index[0]), end=str(d.index[-1]), hours=len(d),
                       warmup_excluded=warmup, known_targets_after_warmup=int(d[TARGET].iloc[warmup:].notna().sum()))
             for name, d in pieces.items()}
    return pieces, audit
