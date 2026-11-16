import datetime as dt,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from weather_geography import normalize_swe,POINTS
class WeatherGeographyTests(unittest.TestCase):
    def test_valid(self):
        p=POINTS[0];day=dt.date(2026,11,14)
        d={"Theme":"swe","Unit":"mm","TimeResolution":1440,"Data":[0],"NoDataValue":65535,"X":p[3],"Y":p[4],"StartDate":"14.11.2026 06:00:00","EndDate":"14.11.2026 06:00:00"}
        self.assertEqual(normalize_swe(d,p,day,"source")["value_mm"],0)
        for patch in ({"Data":[65535]},{"Data":[float("nan")]},{"Data":[-1]},{"Unit":"cm"},{"Data":[10,11]},{"StartDate":"13.11.2026"},{"X":0}):
            with self.assertRaises(ValueError):normalize_swe(dict(d,**patch),p,day,"source")
