import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import gdw_publication as gp
def fixture():
    return {"schema_version":1,"provider":"global-dam-watch","release":"1.0","source":"https://doi.org/"+gp.DOI,"source_file":"GDW_v1_0_shp.zip","source_sha256":"a"*64,"license":gp.LICENSE,"attribution":gp.ATTR,"retrieved":"2026-11-20T00:00:00Z","source_records":1,"notice":"Historical test source","rows":[{"id":1,"geometry":[1,2],"dam_name":None,"reservoir_name":None,"barrier_type":None,"country":"Test","river":None}]}
class GDWPublicationTests(unittest.TestCase):
    def test_fixture_rights_and_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/gp.NAME;x=fixture();p.write_text(json.dumps(x));self.assertEqual(gp.validate(p,expected=1)["source_records"],1)
            x["rows"][0]["unapproved"]="bad";p.write_text(json.dumps(x))
            with self.assertRaises(ValueError):gp.validate(p,expected=1)
    def test_immutable_and_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/"candidate.json";x=fixture();src.write_text(json.dumps(x))
            actual=gp.validate
            with patch.object(gp,"validate",side_effect=lambda p:actual(p,expected=1)):
                self.assertTrue(gp.promote(src,root/"archive"));self.assertFalse(gp.promote(src,root/"archive"))
                x["source_sha256"]="b"*64;src.write_text(json.dumps(x))
                with self.assertRaises(ValueError):gp.promote(src,root/"archive")
                gp.stage_gdw(root/"archive",root/"public")
                index=json.loads((root/"public"/"index-v1.json").read_text())
                self.assertEqual(index["source_sha256"],"a"*64)
