import json,sys,tempfile,unittest,shutil,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_plant_pages import generate
class StaticPlants(unittest.TestCase):
    def test_real_register(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"data").mkdir();shutil.copy(Path(__file__).resolve().parents[1]/"data/hydro-plants-v1.json",root/"data")
            source=json.loads((root/"data/hydro-plants-v1.json").read_text())
            self.assertEqual(generate(root),len(source["rows"]))
            self.assertEqual(len(list((root/"plants/nve").glob("*/index.html"))),len(source["rows"]))
            sample=(root/"plants/nve/53/index.html").read_text()
            self.assertIn("Bøylefoss",sample);self.assertIn('href="/#asset/nve/53"',sample)
            self.assertIn('https://energy.nordl.dev/plants/nve/53/',sample)
            self.assertEqual(len(ET.parse(root/"sitemap.xml").getroot()),len(source["rows"])+3)
