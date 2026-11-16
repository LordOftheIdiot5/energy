"""Optional local authenticated API. Do not expose directly to the internet;
deploy behind a TLS reverse proxy with independent rate limits and access logs.
No keys or private datasets are written into the static Pages build.
"""
import argparse,collections,hashlib,hmac,json,os,re,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
ALLOWED=frozenset(("hydro-weekly","hydro-plants","hydro-stations","hydro-reservoirs","hydro-catchments","hydro-owners","europe-plants"))
def catalog(root):
    d=json.loads((root/"commercial-catalog-v1.json").read_text(encoding="utf-8"))
    rows=d["datasets"];ids={x["id"] for x in rows}
    if d["schema_version"]!=1 or ids!=ALLOWED or len(rows)!=len(ALLOWED):raise ValueError("Invalid export allowlist")
    for x in rows:
        if not re.fullmatch(r"[a-z0-9-]+\.json",x["path"]) or x["access"]!="open_with_attribution" or not x["license"].startswith(("https://data.norge.no/nlod/","https://creativecommons.org/licenses/by/4.0/")):raise ValueError("Invalid rights gate")
    return rows
def page(root,dataset,offset=0,limit=100):
    if dataset not in ALLOWED:raise KeyError(dataset)
    if type(offset)!=int or type(limit)!=int or offset<0 or not 1<=limit<=200:raise ValueError("Invalid pagination")
    item=next(x for x in catalog(root) if x["id"]==dataset)
    path=(root/item["path"]).resolve()
    if path.parent!=root.resolve():raise ValueError("Unsafe path")
    raw=path.read_bytes();d=json.loads(raw)
    if d.get("schema_version")!=item["schema_version"] or not isinstance(d.get("rows"),list):raise ValueError("Invalid source")
    rows=d["rows"];result={"schema_version":1,"dataset":dataset,"source":item["source"],"license":item["license"],"attribution":item["attribution"],"notes":item["notes"],"source_generated":d.get("generated"),"source_sha256":hashlib.sha256(raw).hexdigest(),"offset":offset,"limit":limit,"total":len(rows),"next_offset":offset+limit if offset+limit<len(rows) else None,"rows":rows[offset:offset+limit]}
    return result
def handler(root,key,max_per_minute=60):
    seen=collections.deque();lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def reply(self,status,d):
            raw=json.dumps(d,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
            self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(raw)));self.send_header("Cache-Control","private, no-store");self.send_header("X-Content-Type-Options","nosniff");self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if not hmac.compare_digest(self.headers.get("Authorization","").encode(),("Bearer "+key).encode()):
                return self.reply(401,{"error":"unauthorized"})
            with lock:
                now=time.monotonic()
                while seen and seen[0]<=now-60:seen.popleft()
                if len(seen)>=max_per_minute:return self.reply(429,{"error":"rate_limit"})
                seen.append(now)
            try:
                u=urlsplit(self.path);q=parse_qs(u.query,strict_parsing=True)
                if u.path=="/v1/catalog" and not q:return self.reply(200,{"schema_version":1,"datasets":catalog(root)})
                m=re.fullmatch(r"/v1/datasets/([a-z0-9-]+)",u.path)
                if not m:return self.reply(404,{"error":"not_found"})
                if set(q)-{"offset","limit"} or any(len(v)!=1 for v in q.values()):raise ValueError("Invalid parameters")
                self.reply(200,page(root,m[1],int(q.get("offset",["0"])[0]),int(q.get("limit",["100"])[0])))
            except KeyError:self.reply(404,{"error":"not_found"})
            except (ValueError,TypeError):self.reply(400,{"error":"invalid_request"})
            except (OSError,RuntimeError):self.reply(503,{"error":"source_unavailable"})
        def log_message(self,fmt,*args):pass
    return Handler
def main():
    p=argparse.ArgumentParser();p.add_argument("--data",type=Path,default=Path(__file__).resolve().parents[1]/"data");p.add_argument("--port",type=int,default=8788);a=p.parse_args()
    key=os.environ.get("NORDL_ENERGY_API_KEY","")
    if len(key)<32:raise SystemExit("Set NORDL_ENERGY_API_KEY to a unique secret of at least 32 characters")
    catalog(a.data);ThreadingHTTPServer(("127.0.0.1",a.port),handler(a.data,key)).serve_forever()
if __name__=="__main__":main()
