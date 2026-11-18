import json,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from nordic_observations import *
class NordicObservationsTests(unittest.TestCase):
    def test_station_and_hydro(self):
        license="https://data.norge.no/nlod/en"
        rows=normalize_stations({"license":license,"data":[{"stationId":"1.2.0","stationName":"Test","latitude":60,"longitude":10,"stationStatusName":"Aktiv","seriesList":[{"parameter":1001}]}]})
        self.assertEqual(select_samples(rows)[0]["stationId"],"1.2.0")
        d={"license":license,"data":[{"stationId":"1.2.0","parameter":1001,"unit":"m3/s","versionNo":1,"observations":[{"time":"2026-11-17T11:00:00Z","value":0,"quality":2,"correction":0},{"time":"2026-11-18T11:00:00Z","value":None}]}]}
        row=hydro_rows(d,{"1.2.0"})[0]
        self.assertEqual(row["value"],0);self.assertEqual(row["quality"],2)
        with self.assertRaises(ValueError):normalize_stations({"license":"private","data":[]})
    def test_fingrid_archive(self):
        p={"datasetId":192,"startTime":"2026-11-17T00:00:00Z","endTime":"2026-11-17T00:03:00Z","value":100}
        rows=fg_rows({"data":[p]},192);self.assertEqual(len(rows),1)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store(root,"fingrid",rows,"2026-11-17T01:00:00+00:00");store(root,"fingrid",rows,"2026-11-17T02:00:00+00:00")
            archive=root/"observations/fingrid/2026-11.json"
            self.assertEqual(len(json.loads(archive.read_text())["rows"]),1)
            store(root,"fingrid",fg_rows([dict(p,value=101)],192),"2026-11-17T03:00:00+00:00")
            self.assertEqual(len(json.loads(archive.read_text())["rows"]),2)
            self.assertEqual(json.loads((root/"fingrid-v1.json").read_text())["rows"][0]["value"],101)
            self.assertIn("observations/fingrid/2026-11.json",list(public_files(root)))
