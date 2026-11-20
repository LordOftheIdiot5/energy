import json,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from osm_grid_publication import validate,promote,stage_grid,name,SOURCES,LICENSE
def fixtures(root,digest="a",date="2026-11-20T01:00:00Z"):
    root.mkdir(parents=True,exist_ok=True)
    for region,providers in SOURCES.items():
        provider,url=providers[0]
        x={"schema_version":1,"provider":"osm","region":region,"source":url,"extract_provider":provider,"source_sha256":digest*64,"source_last_modified":None,"source_bytes":1024,"retrieved":date,"license":LICENSE,"attribution":"© OpenStreetMap contributors; "+provider+" regional extract; selected and normalized by Nordl","source_records":2,"category_counts":{"substation":1,"overhead_line":1},"rejected_objects":{},"notice":"Test reference","rows":[{"id":"osm:node:1","name":None,"category":"substation","voltage_v":[],"geometry":{"type":"Point","coordinates":[1,2]},"source_object":"https://www.openstreetmap.org/node/1"},{"id":"osm:way:2","name":None,"category":"overhead_line","voltage_v":[66000],"geometry":{"type":"LineString","coordinates":[[1,2],[1,3]]},"source_object":"https://www.openstreetmap.org/way/2"}]}
        (root/name(region)).write_text(json.dumps(x))
class GridPublicationTests(unittest.TestCase):
    def test_versioned_archive_and_projection(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);fixtures(p/"incoming");promote(p/"incoming",p/"archive")
            fixtures(p/"incoming","b","2026-11-21T01:00:00Z");promote(p/"incoming",p/"archive")
            self.assertEqual(len(list((p/"archive"/"revisions").rglob("*.json"))),2)
            stage_grid(p/"archive",p/"public");self.assertFalse((p/"public"/"revisions").exists())
            self.assertEqual(sum(e["source_records"] for e in json.loads((p/"public"/"index-v1.json").read_text())["datasets"]),4)
            fixtures(p/"incoming","a")
            with self.assertRaises(ValueError):promote(p/"incoming",p/"archive")
    def test_invalid_candidate_preserves_both(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);fixtures(p/"incoming");promote(p/"incoming",p/"archive")
            fixtures(p/"incoming","b","2026-11-21T01:00:00Z")
            f=p/"incoming"/name("LU");x=json.loads(f.read_text());x["rows"][0]["geometry"]["coordinates"]=[181,2];f.write_text(json.dumps(x))
            with self.assertRaises(ValueError):promote(p/"incoming",p/"archive")
            self.assertEqual(validate(p/"archive"/name("IS"),"IS")["source_sha256"],"a"*64)
