import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from gdw_barriers import normalize,admit,DOI
class GDWTests(unittest.TestCase):
    def test_missing_and_geometry(self):
        x=normalize({"GDW_ID":1,"DAM_NAME":" Example ","RES_NAME":"-9999","COUNTRY":"Norway"},(10,60))
        self.assertEqual(x["dam_name"],"Example");self.assertIsNone(x["reservoir_name"]);self.assertIsNone(x["river"])
        with self.assertRaises(ValueError):normalize({"GDW_ID":1},(181,60))
        with self.assertRaises(ValueError):normalize({"GDW_ID":1.5},(10,60))
    def test_version_and_license(self):
        m={"doi":DOI,"version":1,"license":{"url":"https://creativecommons.org/licenses/by/4.0/"},"files":[{"name":"GDW_v1_0_shp.zip","size":1,"downloadUrl":"https://figshare.com/ndownloader/files/1"}]}
        self.assertEqual(admit(m)["size"],1)
        with self.assertRaises(ValueError):admit({**m,"version":2})
        with self.assertRaises(ValueError):admit({**m,"license":{"url":"https://creativecommons.org/licenses/by-nc/4.0/"}})
