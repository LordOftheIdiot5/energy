import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_public_site import validate_uk_repd
class UKPublicReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=json.loads((ROOT/"data/uk-repd-projects-v1.json").read_text(encoding="utf-8"))
    def test_real_release(self):
        self.assertTrue(validate_uk_repd(self.doc))
    def test_counts_gate(self):
        with self.assertRaisesRegex(ValueError,"coverage"):
            validate_uk_repd({**self.doc,"counts":{**self.doc["counts"],"mapped_records":14000}})
    def test_rights_and_hash_gate(self):
        with self.assertRaisesRegex(ValueError,"provenance"):
            validate_uk_repd({**self.doc,"source_sha256":"not-the-approved-release"})
    def test_status_inference_forbidden(self):
        rows=[dict(self.doc["rows"][0],generation_mw=1)]+self.doc["rows"][1:]
        with self.assertRaisesRegex(ValueError,"record"):
            validate_uk_repd({**self.doc,"rows":rows})
