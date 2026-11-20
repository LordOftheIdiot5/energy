import json,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from osm_publication import validate,promote,stage_osm
from osm_datacentres import record,REGIONS,LICENSE,ATTRIBUTION
class OSMPublicationTests(unittest.TestCase):
    def fixtures(self,root,name="Example"):
        root.mkdir(parents=True,exist_ok=True)
        for region,slug in REGIONS.items():
            x={"schema_version":1,"provider":"osm","region":region,"source":f"https://download.geofabrik.de/europe/{slug}-latest.osm.pbf","source_sha256":"a"*64,"source_last_modified":None,"retrieved":"2026-11-20T00:00:00Z","license":LICENSE,"attribution":ATTRIBUTION,"source_notice":"Fixture","rejected_tagged_objects":0,"rows":[record("node",1,{"name":name,"telecom":"data_center"},1,2)]}
            (root/f"{region.lower()}-datacentres.json").write_text(json.dumps(x))
    def test_archive_and_separate_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.fixtures(p/"incoming");promote(p/"incoming",p/"archive")
            self.fixtures(p/"incoming","New name");promote(p/"incoming",p/"archive")
            self.assertEqual(len(list((p/"archive"/"revisions").rglob("*.json"))),2)
            stage_osm(p/"archive",p/"public");self.assertFalse((p/"public"/"revisions").exists())
            self.assertEqual(len(json.loads((p/"public"/"index-v1.json").read_text())["datasets"]),2)
    def test_unapproved_field_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.fixtures(p/"incoming");f=p/"incoming"/"is-datacentres.json";x=json.loads(f.read_text());x["rows"][0]["contact"]="not allowed";f.write_text(json.dumps(x))
            with self.assertRaises(ValueError):promote(p/"incoming",p/"archive")
            self.assertFalse((p/"archive").exists())
