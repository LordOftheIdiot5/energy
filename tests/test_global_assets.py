import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from global_assets import *
class GlobalAssetsTests(unittest.TestCase):
    def test_coordinates_and_missing(self):
        r={"gppd_idnr":"test","name":"Example","latitude":"1","longitude":"2","capacity_mw":"","country":"NOR","country_long":"Norway","primary_fuel":"Hydro"}
        rows,rejected=normalize([r,dict(r,gppd_idnr="bad",latitude="nan")])
        self.assertEqual(rows[0]["geometry"],[2,1]);self.assertIsNone(rows[0]["capacity_mw"]);self.assertEqual(rejected,1)
        with self.assertRaises(ValueError):normalize([r,r])
