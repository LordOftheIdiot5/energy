import datetime as dt,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from price_benchmark import day_prices,open_license,feature_rows,evaluate
class PriceBenchmarkTests(unittest.TestCase):
    def test_license(self):
        self.assertTrue(open_license("CC BY 4.0"))
        self.assertFalse(open_license("CC BY 4.0; private and internal use only"))
        self.assertFalse(open_license(None))
    def test_price_intervals(self):
        day=dt.date(2025,9,30);start=int(dt.datetime.combine(day,dt.time(),dt.timezone.utc).timestamp());ts=[start+i*3600 for i in range(22)]+[start+22*3600+i*900 for i in range(8)]
        d={"license_info":"CC BY 4.0","unit":"EUR/MWh","unix_seconds":ts,"price":[-10]*22+[20]*8}
        self.assertEqual(day_prices(dict(d,unit="€/MWh"),day,day)[1],0)
        out,bad=day_prices(d,day,day);self.assertEqual(bad,0);self.assertAlmostEqual(out[day],-7.5)
        out,bad=day_prices(dict(d,price=[None]+d["price"][1:]),day,day);self.assertEqual((out,bad),({},1))
        with self.assertRaises(ValueError):day_prices(dict(d,license_info="private"),day,day)
    def test_no_future_weather_or_prices(self):
        day=dt.date(2024,3,1);d={day-dt.timedelta(days=i):float(i) for i in range(30)}
        r=feature_rows(d)[-1];self.assertEqual(r["recent"],2);self.assertEqual(r["weekly"],7);self.assertEqual(r["actual"],0)
        d[day-dt.timedelta(days=1)]=999;self.assertEqual(feature_rows(d)[-1]["x"],r["x"])
