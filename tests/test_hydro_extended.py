import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from hydro_extended import hydro_backfill, point_weather, plant_records, SOURCE

class HydroExtendedTests(unittest.TestCase):
    def test_backfill_no_future_median(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"hydro.json"
            p.write_text(json.dumps({"schema_version":1,"source":SOURCE,"rows":[]}))
            rows=[{"omrType":"EL","omrnr":a,"iso_aar":y,"iso_uke":10,"fyllingsgrad":0.4+(y-1995)*0.01,"fylling_TWh":2} for a in range(1,6) for y in range(1995,2020)]
            self.assertEqual(hydro_backfill(p,rows,"2026-11-16T00:00:00+00:00"),125)
            out=json.loads(p.read_text())["rows"]
            self.assertIsNone(out[0]["normal_pct"])
            self.assertEqual(next(r for r in out if r["year"]==1996 and r["zone"]=="NO1")["normal_pct"],40)
            first=p.read_bytes()
            hydro_backfill(p,rows,"2026-11-17T00:00:00+00:00")
            self.assertEqual(first,p.read_bytes())
    def test_reject_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"hydro.json"
            p.write_text(json.dumps({"schema_version":1,"source":SOURCE,"rows":[]}))
            self.assertEqual(hydro_backfill(p,[],"now"),0)
    def test_weather_no_double_count(self):
        row=lambda t,period,p,temp: {"time":t,"data":{"instant":{"details":{"air_temperature":temp}},period:{"details":{"precipitation_amount":p}}}}
        result=point_weather([row("2026-11-16T00:00:00Z","next_6_hours",6,-1),row("2026-11-16T01:00:00Z","next_1_hours",1,2),row("2026-11-16T06:00:00Z","next_1_hours",2,3)])
        self.assertEqual(result["precipMm"],8)
        self.assertEqual(result["precipCoverageHours"],7)
        self.assertEqual(result["coldPrecipMm"],6)
        self.assertEqual(result["positiveDegreeHours"],3)
    def test_plant_normalization(self):
        rows=plant_records([{"VannKraftverkID":2,"Navn":"Example","ErIDrift":True,"ElspotomraadeNummer":4,"MaksYtelse":50},{"VannKraftverkID":3,"Navn":"Inactive","ErIDrift":False}])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["zone"],"NO4")
        self.assertEqual(rows[0]["capacity_mw"],50)

if __name__=="__main__":
    unittest.main()
