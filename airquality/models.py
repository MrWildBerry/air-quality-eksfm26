"""Plano (3), (4): sklearn medžių slenksčiai ir lapų vidurkinimas."""
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.svm import SVR
from .features import Prepare

def create_model(kind, params, seed=42, threads=4):
    if kind == 'RF':
        estimator = RandomForestRegressor(**params, random_state=seed, n_jobs=threads,
                                         bootstrap=True, criterion='squared_error')
    else:
        estimator = SVR(kernel='rbf', cache_size=512, **params)
    return Pipeline([('prepare', Prepare(scale=kind != 'RF')), ('model', estimator)])

def predict(model, X):
    raw = model.predict(X)
    return np.maximum(0, raw), raw < 0

def verify_forest_formula(model, X):
    """Skaitinis bibliotekos prognozės ir (4) formulės sutikrinimas."""
    transformed = model.named_steps['prepare'].transform(X)
    forest = model.named_steps['model']
    leaf_values = np.array([t.predict(transformed) for t in forest.estimators_])
    manual = leaf_values.mean(axis=0)
    np.testing.assert_allclose(manual, model.predict(X), rtol=1e-12, atol=1e-12)
    return {'trees': len(forest.estimators_), 'first_tree_leaf_values': leaf_values[:3, 0].tolist(),
            'mean_all_trees': float(manual[0]), 'sklearn_prediction': float(model.predict(X.iloc[:1])[0]),
            'maximum_difference': float(np.max(np.abs(manual-model.predict(X))))}
