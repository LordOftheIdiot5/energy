import json,sys,tempfile,unittest,shutil,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_plant_pages import generate
class StaticPlants(unittest.TestCase):
    def test_real_register(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"data").mkdir();shutil.copy(Path(__file__).resolve().parents[1]/"data/hydro-plants-v1.json",root/"data")
            shutil.copy(Path(__file__).resolve().parents[1]/"data/europe-plants-v1.json",root/"data")
            wri=json.loads((root/"data/europe-plants-v1.json").read_text())
            source=json.loads((root/"data/hydro-plants-v1.json").read_text())
            self.assertEqual(generate(root),len(source["rows"]))
            self.assertEqual(len(list((root/"plants/nve").glob("*/index.html"))),len(source["rows"]))
            sample=(root/"plants/nve/53/index.html").read_text()
            self.assertIn("Bøylefoss",sample);self.assertIn('href="/#asset/nve/53"',sample)
            self.assertIn('https://energy.nordl.dev/plants/nve/53/',sample)
            self.assertEqual(len(ET.parse(root/"sitemap.xml").getroot()),len(source["rows"])+len(wri["rows"])+len({r["country"] for r in wri["rows"]})+6)

            self.assertEqual(len(list((root/"plants/wri").glob("*/index.html"))),len(wri["rows"]))
            sample_id=wri["rows"][0]["id"]
            profile=(root/"plants/wri"/sample_id/"index.html").read_text()
            self.assertIn("Historical archive",profile)
            self.assertIn("CC BY 4.0",profile)
            self.assertIn("/#asset/wri/"+sample_id,profile)
            self.assertTrue((root/"data-coverage/index.html").is_file())
            locs=[x[0].text for x in ET.parse(root/"sitemap.xml").getroot()]
            self.assertEqual(len(locs),len(set(locs)))
