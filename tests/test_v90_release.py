import json,sys,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from dataset_api import catalog,page,handler
from price_rights import permitted,eur_mwh
class ReleaseTests(unittest.TestCase):
    def test_rights(self):
        self.assertTrue(permitted("NO2","CC BY 4.0"))
        self.assertFalse(permitted("FI","CC BY 4.0"))
        self.assertFalse(permitted("NO2","CC BY 4.0; private and internal use only"))
        self.assertFalse(permitted("NO2",None))
        self.assertTrue(eur_mwh("€/MWh"))
        self.assertFalse(eur_mwh("NOK/MWh"))
        d=json.loads((ROOT/"data/energy.json").read_text())
        self.assertFalse({"FI","ES"}&{x["zone"] for x in d["europe"]})
    def test_catalog_and_pagination(self):
        root=ROOT/"data";ids=catalog(root)
        self.assertEqual(len(ids),7)
        for d in ids:
            item=page(root,d["id"],0,2)
            self.assertGreater(item["total"],0);self.assertLessEqual(len(item["rows"]),2);self.assertTrue(item["license"]);self.assertEqual(len(item["source_sha256"]),64)
        with self.assertRaises(KeyError):page(root,"mixed-energy")
        with self.assertRaises(ValueError):page(root,"hydro-weekly",0,201)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);bad=json.loads((root/"commercial-catalog-v1.json").read_text());bad["datasets"][0]["path"]="energy.json";(p/"commercial-catalog-v1.json").write_text(json.dumps(bad))
            with self.assertRaises(ValueError):catalog(p)
    def test_http_auth_and_limits(self):
        key="x"*40
        server=ThreadingHTTPServer(("127.0.0.1",0),handler(ROOT/"data",key,2))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base="http://127.0.0.1:"+str(server.server_port)
        def request(path,auth=True):
            req=urllib.request.Request(base+path,headers={"Authorization":"Bearer "+key} if auth else {})
            try:
                with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.loads(r.read())
            except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
        try:
            self.assertEqual(request("/v1/catalog",False)[0],401)
            self.assertEqual(request("/v1/catalog")[0],200)
            status,row=request("/v1/datasets/hydro-weekly?limit=2")
            self.assertEqual(status,200);self.assertEqual(len(row["rows"]),2)
            self.assertEqual(request("/v1/catalog")[0],429)
        finally:server.shutdown();server.server_close();thread.join()
    def test_identity(self):
        data=json.loads((ROOT/"data/owner-company-links-v1.json").read_text())
        owners=json.loads((ROOT/"data/hydro-owners-v1.json").read_text())["rows"]
        for r in data["rows"]:
            owner=next(x for x in owners if x["orgnr"]==r["orgnr"])
            self.assertEqual(owner["name"],r["name"])
            self.assertEqual(r["identity_status"],"direct_legal_entity")
            self.assertEqual(r["isin"],"NO0003572802")
