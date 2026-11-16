import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from asset_reference import normalize,aggregate
class AssetTests(unittest.TestCase):
    def test_normalize(self):
        r={"country":"NOR","gppd_idnr":"a","name":"X","longitude":"10","latitude":"60","capacity_mw":"20","primary_fuel":"Hydro"}
        self.assertEqual(normalize([r])[0]["geometry"],[10,60])
        self.assertEqual(normalize([{**r,"latitude":"nan"}]),[])
        with self.assertRaises(ValueError):normalize([r,r])
    def test_owner(self):
        r={"id":1,"owner":"A","owner_orgnr":"123456789","capacity_mw":12,"zone":"NO1"}
        d=aggregate({"generated":"test","rows":[r,{**r,"id":2,"capacity_mw":None}]})
        self.assertEqual(d["rows"][0]["reported_capacity_mw"],12)
        self.assertEqual(d["rows"][0]["plant_ids"],[1,2])
        self.assertEqual(d["rows"][0]["capacity_records"],1)
