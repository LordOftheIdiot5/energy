import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from nordic_backfill import backfill,jobs
from nordic_observations import store
from hydapi_relationships import build,regine
class HistoryTests(unittest.TestCase):
    def test_exact_identifier(self):
        rows=build([{"stationId":"1.2.0","regineNo":"016.BA11"},{"stationId":"2.3.0","regineNo":"016.BA"},{"stationId":"3.4.0","regineNo":"16.BA11"}],[{"id":42,"name":"Plant","catchment_id":"016.BA11"}],[{"id":100,"delfeltNr":"016.BA11"}])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["plants"][0]["id"],42)
        self.assertEqual(rows[0]["catchmentRecordIds"],[100])
        self.assertIsNone(regine("16.BA11"))
    def test_backfill_resumes_and_keeps_recent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            old={"id":"192","datasetId":192,"name":"Electricity production","unit":"MW","time":"2026-11-19T00:00:00+00:00","endTime":"2026-11-19T00:03:00+00:00","value":125}
            store(root,"fingrid",[old],"2026-11-19T00:06:00+00:00")
            newest=(root/"fingrid-v1.json").read_bytes()
            calls=[]
            def fake(url,key):
                calls.append(url);dataset=int(url.split("/datasets/")[1].split("/")[0])
                return {"data":[{"datasetId":dataset,"startTime":"2026-11-18T00:00:00Z","endTime":"2026-11-18T00:03:00Z","value":100}]}
            settings=dict(get=fake,pause=lambda _:None,stamp="2026-11-19T00:10:00+00:00",limits={"hydapi":0,"fingrid":1})
            keys={"hydapi":None,"fingrid":"fixture"}
            state=backfill(root,keys,**settings)
            self.assertEqual(len(state["requests"]),1)
            self.assertEqual(len(calls),1)
            self.assertEqual((root/"fingrid-v1.json").read_bytes(),newest)
            state=backfill(root,keys,**settings)
            self.assertEqual(len(state["requests"]),2)
            self.assertNotEqual(calls[0],calls[1])
            self.assertEqual((root/"fingrid-v1.json").read_bytes(),newest)
            self.assertEqual(len(list(jobs(root,"2026-11-19"))),28)
