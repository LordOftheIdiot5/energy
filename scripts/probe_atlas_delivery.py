"""Verify bounded same-origin public HTTP range reads against a published manifest."""
import argparse,hashlib,json,re
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
def read(url,headers,maximum):
    with urlopen(Request(url,headers={"Accept-Encoding":"identity","User-Agent":"Nordl Atlas delivery smoke",**headers}),timeout=25) as r:
        if urlsplit(r.url).netloc!=urlsplit(url).netloc:raise ValueError("Unexpected redirect origin")
        expected_max=maximum
        data=r.read(expected_max+1)
        if len(data)>maximum:raise ValueError("Response exceeded bounded read")
        return r.status,r.headers,data
def verify(base,reader=read):
    base=base.rstrip("/")+"/data/atlas-tiles/"
    if urlsplit(base).scheme not in ("http","https"):raise ValueError("Unsupported URL")
    code,h,raw=reader(base+"index-v1.json",{},65536)
    if code!=200:raise ValueError("Manifest response")
    m=json.loads(raw)
    digest=m.get("archive_sha256","")
    if m.get("schema_version")!=1 or m.get("delivery")!="same-origin-static" or m.get("status")!="experimental_delivery" or not re.fullmatch(r"[0-9a-f]{64}",digest) or m.get("path")!=f"wri-v130-{digest}.pmtiles" or m.get("license")!="https://creativecommons.org/licenses/by/4.0/" or type(m.get("archive_bytes")) is not int or not 256<=m["archive_bytes"]<=25_000_000 or type(m.get("source_records")) is not int or m["source_records"]<30000:raise ValueError("Unapproved manifest")
    probes=m["probe_ranges"]
    if [(p["start"],p["end"]) for p in probes]!=[(0,126),(127,255)]:raise ValueError("Unexpected probe ranges")
    etag=None
    for p in probes:
        start,end=p["start"],p["end"];n=end-start+1
        code,h,b=reader(base+m["path"],{"Range":f"bytes={start}-{end}",**({"If-Match":etag} if etag and not etag.startswith("W/") else {})},n)
        if code!=206 or h.get("Content-Range")!=f"bytes {start}-{end}/{m['archive_bytes']}" or h.get("Content-Encoding","identity")!="identity" or len(b)!=n or hashlib.sha256(b).hexdigest()!=p["sha256"]:raise ValueError("Invalid HTTP 206 range or checksum")
        if start==0 and b[:8]!=b"PMTiles\x03":raise ValueError("Invalid PMTiles header")
        new=h.get("ETag")
        if etag and new!=etag:raise ValueError("Object changed between range reads")
        etag=new
        print("PASS HTTP 206",start,end,len(b),"verified bytes")
    print("PASS Atlas delivery",m["source_records"],"records",m["archive_bytes"],"archive bytes; ETag",etag or "not supplied")
    return m
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--base",required=True);verify(p.parse_args().base)
