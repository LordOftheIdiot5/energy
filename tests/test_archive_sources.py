import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from open_history import append
class ArchiveSources(unittest.TestCase):
    def test_entsoe_and_met(self):
        source=Path(__file__).resolve().parents[1]/"data/entsoe-open.json"
        d=json.loads(source.read_text())
        payload={"generated":"2026-11-17T20:00:00+00:00","weather":{"NO1":{"sourceUpdatedAt":"2026-11-17T19:00:00Z","forecastStart":"2026-11-17T19:00:00Z","tempNow":0},"NO2":{"sourceUpdatedAt":"2026-11-17T19:00:00Z","forecastStart":"2026-11-17T19:00:00Z","tempNow":2,"stale":True}}}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"entsoe-open.json").write_text(json.dumps(d));added=append(root,payload)
            self.assertGreater(added,1);self.assertEqual(append(root,payload),0)
            index=json.loads((root/"archive/index-v1.json").read_text())
            self.assertIn("entsoe-series",{p["kind"] for p in index["partitions"]})
            weather=json.loads((root/"archive/weather-forecast/2026-11.json").read_text())["rows"]
            self.assertEqual(len(weather),1);self.assertEqual(weather[0]["tempNow"],0)
            payload["weather"]["NO1"]["tempNow"]=1
            self.assertEqual(append(root,payload),1)
