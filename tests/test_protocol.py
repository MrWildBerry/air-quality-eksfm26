import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from airquality.load import CHANNELS, TARGET, SENSORS, load_data
from airquality.features import make_features, Prepare
from airquality.masks import block_mask, corrupt
from airquality.baselines import fit_baselines, predict_baselines
from airquality.models import create_model, verify_forest_formula
from airquality.evaluate import metrics, choose, quality
from airquality.split import split_data

class ProtocolTests(unittest.TestCase):
    def setUp(self):
        index = pd.date_range('2004-01-01', periods=1000, freq='h')
        self.d = pd.DataFrame({c:np.arange(1000,dtype=float)+i for i,c in enumerate(CHANNELS)}, index=index)
        self.d[TARGET] = np.arange(1000,dtype=float) / 100

    def test_target_never_enters_features(self):
        changed = self.d.copy()
        changed[TARGET] = 1234567.
        pd.testing.assert_frame_equal(make_features(self.d), make_features(changed))
        self.assertEqual(make_features(self.d).shape[1],68)

    def test_future_cannot_change_past_prediction(self):
        x = make_features(self.d)
        m = create_model('RF', dict(n_estimators=5,max_depth=3), threads=1).fit(x.iloc[:100], self.d[TARGET].iloc[:100])
        changed = self.d.copy()
        changed.iloc[501:, :8] = -99999
        np.testing.assert_array_equal(m.predict(x.iloc[:501]),m.predict(make_features(changed).iloc[:501]))

    def test_masked_sensor_stays_missing_in_lags(self):
        ids = np.full(len(self.d), -1); ids[40:64] = 0
        d = corrupt(self.d,ids,'B_S1',42,1)
        x = make_features(d)
        self.assertTrue(pd.isna(x.iloc[64][SENSORS[0]+'_lag1']))
        self.assertTrue(pd.isna(x.iloc[64][SENSORS[0]+'_lag24']))
        self.assertEqual(x.iloc[64][SENSORS[0]+'_lag24_missing'],1)

    def test_lag_uses_timestamp_not_row(self):
        d = self.d.drop(self.d.index[30])
        self.assertTrue(pd.isna(make_features(d).loc[self.d.index[31],CHANNELS[0]+'_lag1']))

    def test_last_ignores_hidden_truth_and_current_target(self):
        y = pd.Series([1.,2.,np.nan,np.nan,8.,9.], index=self.d.index[:6])
        state = fit_baselines(self.d[TARGET].iloc[:100])
        p = predict_baselines(y,state)['last']
        np.testing.assert_array_equal(p[2:], [2.,2.,2.,8.])

    def test_block_lengths_and_coverage(self):
        for length in (6,24,72):
            ids=block_mask(self.d,length,42)
            for b in set(ids)-{-1}:
                indices=np.flatnonzero(ids==b)
                self.assertEqual(len(indices),length)
                self.assertTrue((np.diff(indices)==1).all())
            self.assertLessEqual(abs((ids>=0).sum()-.2*(len(ids)-24)),length)
            self.assertTrue((ids[:24]==-1).all())

    def test_preprocessing_fits_training_only(self):
        x=make_features(self.d.iloc[:100])
        x[CHANNELS[0]]=np.nan
        prep=Prepare(True).fit(x)
        self.assertEqual(prep.medians_[CHANNELS[0]],0)
        med=prep.medians_.copy()
        prep.transform(make_features(self.d.iloc[100:]))
        pd.testing.assert_series_equal(med,prep.medians_)

    def test_forest_formula(self):
        x=make_features(self.d.iloc[:100])
        model=create_model('RF',dict(n_estimators=7,max_depth=3),threads=1).fit(x,self.d[TARGET].iloc[:100])
        self.assertLess(verify_forest_formula(model,x.iloc[:3])['maximum_difference'],1e-10)

    def test_undefined_extremes(self):
        frame=pd.DataFrame(dict(y_true=[1.,2.],co_hat_mg_m3=[1.,3.],block_id=[0,1],quality_flag=['atkurtas']*2,clipped=[False]*2))
        m=metrics(frame,10)
        self.assertTrue(np.isnan(m['recall']))
        self.assertTrue(np.isnan(m['precision']))
        self.assertEqual(m['mae'],.5)

    def test_selection_tie_rule(self):
        rows=[dict(id='a',mae=1,recall=.5,seconds=1),dict(id='b',mae=1.01,recall=.6,seconds=2),dict(id='c',mae=1.1,recall=1,seconds=.1)]
        self.assertEqual(choose(rows),'b')

    def test_split_not_dependent_on_target(self):
        d=self.d.copy(); d[TARGET]=np.nan
        a,_=split_data(self.d); b,_=split_data(d)
        self.assertTrue(a['test'].index.equals(b['test'].index))

    def test_duplicate_conflicts_and_missing_hour(self):
        d=self.d.iloc[:4].copy()
        duplicate=d.iloc[[0]].copy(); duplicate[CHANNELS[0]]=123
        d=pd.concat([d.drop(d.index[2]),duplicate])
        d['Date']=d.index.strftime('%d/%m/%Y'); d['Time']=d.index.strftime('%H.%M.%S')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.csv'; d.to_csv(p,sep=';',decimal=',',index=False)
            loaded,audit=load_data(p)
        self.assertEqual(audit['conflicting_cells'],1)
        self.assertEqual(audit['inserted_hours'],1)
        self.assertTrue(pd.isna(loaded.iloc[0][CHANNELS[0]]))
        self.assertTrue(loaded.iloc[2].isna().all())

if __name__ == '__main__': unittest.main()
