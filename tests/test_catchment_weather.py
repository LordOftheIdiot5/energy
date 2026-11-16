import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from catchment_weather import normalize, collect

START, END = date(2018, 1, 1), date(2018, 1, 2)

def sample(theme="rr", unit="mm"):
    return {"Theme": theme, "Unit": unit, "TimeResolution": 1440,
        "StartDate": "01.01.2018 06:00:00", "EndDate": "02.01.2018 06:00:00",
        "NoDataValue": 65535, "CellTimeSeries": [
            {"CellIndex": 1, "Data": [2, 4]},
            {"CellIndex": 2, "Data": [6, 65535]}]}

class CatchmentTests(unittest.TestCase):
    def test_complete_and_missing(self):
        days = normalize("rr", sample(), START, END)["days"]
        self.assertEqual(days[0]["mean"], 4)
        self.assertIsNone(days[1]["mean"])
        self.assertEqual(days[1]["valid_cells"], 1)

    def test_reject_wrong_unit_or_resolution(self):
        for update in ({"Unit": "cm"}, {"TimeResolution": 60},
                       {"EndDate": "03.01.2018 06:00:00"}):
            with self.assertRaises(ValueError):
                normalize("rr", {**sample(), **update}, START, END)

    def test_reject_duplicate_and_invalid_values(self):
        for cells in ([{"CellIndex": 1, "Data": [0, 1]}]*2,
                      [{"CellIndex": 1, "Data": [-1, 1]}],
                      [{"CellIndex": 1, "Data": [float("nan"), 1]}]):
            with self.assertRaises(ValueError):
                normalize("rr", {**sample(), "CellTimeSeries": cells}, START, END)

    def test_mocked_collection(self):
        def get(url, body=None):
            if body is None:
                return {"spatialReference": {"wkid": 25833}, "features": [
                    {"attributes": {"OBJECTID": 42, "delfeltAreal_km2": 3},
                     "geometry": {"rings": [[[100,100],[200,100],[200,200],[100,100]]]}}]}
            theme = body["Theme"]
            return sample(theme, "Celcius" if theme == "tm" else "mm")
        result = collect(42, START, END, get)
        self.assertEqual(set(result["series"]), {"rr", "swe", "tm"})
        self.assertEqual(result["catchment"]["OBJECTID"], 42)
