import sys,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from forecast_backtest import evaluate
class ForecastTests(unittest.TestCase):
    def samples(self):
        start=datetime(2020,1,1,tzinfo=timezone.utc)
        return [{"origin":(d:=start+timedelta(days=7*i)).isoformat(),"features_available_at":d.isoformat(),"target_at":(d+timedelta(days=7)).isoformat(),"label_available_at":(d+timedelta(days=8)).isoformat(),"features":[i, i%4],"actual":i*2+3,"baseline":0} for i in range(85)]
    def test_chronological_fit(self):
        result=evaluate(self.samples())
        self.assertEqual(result["status"],"research_evaluated")
        self.assertLess(result["model_mae"],result["baseline_mae"])
    def test_no_future_feature(self):
        a=self.samples();a[0]["features_available_at"]=a[0]["target_at"]
        with self.assertRaises(ValueError):evaluate(a)
    def test_not_enough_labels(self):
        self.assertEqual(evaluate(self.samples()[:20])["status"],"insufficient_data")
