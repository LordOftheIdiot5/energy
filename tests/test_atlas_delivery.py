import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from probe_atlas_delivery import verify
from stage_atlas_delivery import stage
class DeliveryTests(unittest.TestCase):
    def test_range_and_corruption(self):
        data=b"PMTiles\x03"+bytes(248);digest=hashlib.sha256(data).hexdigest()
        m={"schema_version":1,"delivery":"same-origin-static","status":"experimental_delivery","archive_sha256":digest,"path":"wri-v130-"+digest+".pmtiles","license":"https://creativecommons.org/licenses/by/4.0/","archive_bytes":len(data),"source_records":34936,"probe_ranges":[{"start":s,"end":e,"sha256":hashlib.sha256(data[s:e+1]).hexdigest()} for s,e in [(0,126),(127,255)]]}
        def reader(url,headers,maximum):
            if url.endswith("index-v1.json"):return 200,{},json.dumps(m).encode()
            s,e=map(int,headers["Range"][6:].split("-"))
            return 206,{"Content-Range":f"bytes {s}-{e}/{len(data)}","ETag":'"test"'},data[s:e+1]
        self.assertEqual(verify("https://example.invalid",reader)["source_records"],34936)
        def wrong(*args):
            status,h,b=reader(*args)
            return (200,h,b) if status==206 else (status,h,b)
        with self.assertRaises(ValueError):verify("https://example.invalid",wrong)
        m["probe_ranges"][0]["sha256"]="0"*64
        with self.assertRaises(ValueError):verify("https://example.invalid",reader)
    def test_no_partial_public_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/"data").mkdir();(p/"data/global-plants-wri-v130.json").write_text("{}")
            with patch("stage_atlas_delivery.build",side_effect=ValueError("failed encoding")):
                with self.assertRaises(ValueError):stage(p)
            self.assertFalse((p/"data/atlas-tiles").exists())
