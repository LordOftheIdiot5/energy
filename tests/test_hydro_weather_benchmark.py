import datetime as dt,sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from hydro_weather_benchmark import normalize,weather_features,evaluate,POINTS,THEMES
class HydroWeatherBenchmark(unittest.TestCase):
    def test_daily_validation(self):
        p=POINTS[0];start=dt.date(2020,1,1);end=start+dt.timedelta(days=2)
        d={"Theme":"rr","Unit":"mm","TimeResolution":1440,"X":p[3],"Y":p[4],"StartDate":"01.01.2020 06:00","EndDate":"03.01.2020 06:00","NoDataValue":65535,"Data":[0,65535,2]}
        self.assertEqual(normalize(d,p,"rr",start,end),{start:0,end:2})
        for patch in ({"Unit":"cm"},{"Data":[0,1]},{"X":0},{"StartDate":"02.01.2020"}):
            with self.assertRaises(ValueError):normalize(dict(d,**patch),p,"rr",start,end)
    def test_lag(self):
        w=dt.date(2024,1,15);d={(p[0],t):{w-dt.timedelta(days=i):1 for i in range(14,7,-1)}|{w:9999} for p in POINTS for t in THEMES}
        self.assertEqual(weather_features(d,w),[7,1,1])
        del d[(POINTS[0][0],"rr")][w-dt.timedelta(days=9)]
        self.assertIsNone(weather_features(d,w))
    def test_split_and_weather_ablation(self):
        rows=[]
        for year in range(2012,2026):
            for week in range(1,50):
                w=dt.date.fromisocalendar(year,week,1);v=(week%7)-3
                rows.append({"week":w,"target":w+dt.timedelta(days=7),"fill":50,"actual":50+v,"x":[50,0,math.sin(week),math.cos(week)],"wx":[v,0,0],"seasonal":50})
        d=evaluate(rows)
        self.assertEqual(d["status"],"retrospective_evaluated")
        self.assertEqual(d["train"],294);self.assertEqual(d["calibration"],147);self.assertEqual(d["test"],245)
        self.assertTrue(d["weather_improves_all"])
        self.assertLess(d["mae_pp"]["weather_lagged"],d["mae_pp"]["hydro_only"])
        self.assertEqual(evaluate(rows[:10])["status"],"insufficient_data")
