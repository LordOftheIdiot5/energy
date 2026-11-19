import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sodir_production import *
def fixture():
    return {**{k:0 for k in FIELDS},"OBJECTID":1,"prfYear":2025,"prfMonth":1,"prfNpdidInformationCarrier":123,"prfInformationCarrier":"Example","prfInformationCarrierKind":"FIELD","prfPrdOilNetMillSm3":None}
class SodirTests(unittest.TestCase):
    def test_null_and_units(self):
        r=normalize(fixture(),2025)
        self.assertIsNone(r["oil_million_Sm3"]);self.assertEqual(r["gas_billion_Sm3"],0)
        with self.assertRaises(ValueError):normalize(dict(fixture(),prfMonth=13),2025)
    def test_archive_and_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            def get(url):return {"count":1} if "returnCountOnly" in url else {"features":[{"attributes":fixture()}]}
            collect(p,2025,getter=get,stamp="first")
            self.assertEqual(list(public_files(p)),["sodir-production/2025.json"])
            def next_get(url):return {"count":1} if "returnCountOnly" in url else {"features":[{"attributes":dict(fixture(),prfPrdGasNetBillSm3=2)}]}
            collect(p,2025,getter=next_get,stamp="second")
            self.assertEqual(len(list((p/"sodir-revisions/2025").glob("*.json"))),1)
            old=(p/"sodir-production/2025.json").read_bytes()
            with self.assertRaises(ValueError):collect(p,2025,getter=lambda u:{"count":2} if "returnCountOnly" in u else {"features":[]})
            self.assertEqual(old,(p/"sodir-production/2025.json").read_bytes())
