import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from energy_geography import normalize,get_all
from hydro_validation import model
class GeoTests(unittest.TestCase):
    def test_points(self):
        r=normalize("stations",[{"properties":{"OBJECTID":1,"vannkraftverkNr":4},"geometry":{"type":"Point","coordinates":[10,61]}}])
        self.assertEqual(r[0]["vannkraftverkNr"],4)
        self.assertEqual(r[0]["geometry"],[10,61])
    def test_invalid(self):
        with self.assertRaises(ValueError): normalize("stations",[{"properties":{"OBJECTID":1},"geometry":{"type":"Point","coordinates":[100,61]}}])
    def test_partial(self):
        with self.assertRaises(ValueError): get_all("stations",lambda url,timeout: {"count":2} if "returnCountOnly" in url else {"type":"FeatureCollection","features":[]})
    def test_polygon(self):
        p=[[[10,60],[11,60],[11,61],[10,60]]]
        self.assertEqual(len(normalize("catchments",[{"properties":{"OBJECTID":1},"geometry":{"type":"Polygon","coordinates":p}}])[0]["geometry"]),1)
    def test_empty_model(self):
        self.assertEqual(model([])["evaluated"],0)
    def test_model(self):
        rows=[{"year":y,"week":w,"fill_pct":60-w} for y in range(1995,2020) for w in range(1,40)]
        r=model(rows)
        self.assertGreater(r["evaluated"],100)
        self.assertEqual(r["seasonal_mae_pp"],0)
        self.assertEqual(r["interval_coverage"],1)
if __name__=="__main__": unittest.main()
