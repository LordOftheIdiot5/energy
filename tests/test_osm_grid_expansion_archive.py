import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from osm_grid_expansion_archive import archive
from osm_grid_expansion import EXPANSION
from osm_grid_publication import name,LICENSE
def fixture(root):
    root.mkdir()
    reviewed={}
    for region,providers in EXPANSION.items():
        provider,url=providers[0]
        doc={"schema_version":1,"provider":"osm","region":region,"source":url,"extract_provider":provider,"source_sha256":"a"*64,"source_last_modified":None,"source_bytes":1024,"retrieved":"2026-11-24T03:51:00Z","license":LICENSE,"attribution":"© OpenStreetMap contributors; "+provider+" regional extract; selected and normalized by Nordl","source_records":2,"category_counts":{"substation":1,"overhead_line":1},"rejected_objects":{},"notice":"Fixture only","rows":[{"id":"osm:node:1","name":None,"category":"substation","voltage_v":[],"geometry":{"type":"Point","coordinates":[1,2]},"source_object":"https://www.openstreetmap.org/node/1"},{"id":"osm:way:2","name":None,"category":"overhead_line","voltage_v":[],"geometry":{"type":"LineString","coordinates":[[1,2],[1,3]]},"source_object":"https://www.openstreetmap.org/way/2"}]}
        raw=json.dumps(doc).encode();(root/name(region)).write_bytes(raw);reviewed[region]=(hashlib.sha256(raw).hexdigest(),2)
    return reviewed
class ExpansionArchiveTests(unittest.TestCase):
    def test_exact_review_and_replay(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);reviewed=fixture(root/"incoming")
            a=archive(root/"incoming",root/"archive",reviewed=reviewed)
            self.assertFalse(a["public_map_admitted"]);self.assertEqual(len(a["datasets"]),4)
            self.assertEqual(a,archive(root/"incoming",root/"archive",reviewed=reviewed))
            self.assertEqual(len(list((root/"archive").rglob("*.json"))),5)
    def test_bad_candidate_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);reviewed=fixture(root/"incoming")
            p=root/"incoming"/name("LV");p.write_bytes(p.read_bytes()+b" ")
            with self.assertRaises(ValueError):archive(root/"incoming",root/"archive",reviewed=reviewed)
            self.assertFalse((root/"archive").exists())
    def test_corrupt_retained_object_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);reviewed=fixture(root/"incoming")
            archive(root/"incoming",root/"archive",reviewed=reviewed)
            p=root/"archive"/"LV"/(reviewed["LV"][0]+".json");p.write_bytes(b"bad")
            with self.assertRaises(ValueError):archive(root/"incoming",root/"archive",reviewed=reviewed)
