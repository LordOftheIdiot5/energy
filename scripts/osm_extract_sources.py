"""Bounded public regional OSM extracts. Provider fallback is for transport failures only."""
import hashlib,subprocess
from pathlib import Path
from urllib.parse import urlsplit
SOURCES={
 "IS":[("Geofabrik","https://download.geofabrik.de/europe/iceland-latest.osm.pbf"),("BBBike","https://data.bbbike.org/osm/pbf/region/europe/iceland.osm.pbf")],
 "LU":[("Geofabrik","https://download.geofabrik.de/europe/luxembourg-latest.osm.pbf"),("OpenStreetMap France","https://download.openstreetmap.fr/extracts/europe/luxembourg.osm.pbf")],
}
CAP=150_000_000
# DNS/connect/timeout/transient network failures; never retry HTTP access denials via alternative routes.
TRANSPORT={5,6,7,18,28,52,55,56}
def download(region,root,run=subprocess.run):
    root=Path(root);p=root/"source.osm.pbf";headers=root/"headers.txt"
    failures=[]
    for provider,url in SOURCES[region]:
        p.unlink(missing_ok=True);headers.unlink(missing_ok=True)
        result=run(["curl","--fail","--location","--proto","=https","--proto-redir","=https","--retry","0","--connect-timeout","12","--max-time","150","--max-filesize",str(CAP),"--user-agent","Nordl Energy (https://energy.nordl.dev/)","--dump-header",str(headers),"--output",str(p),url],check=False)
        if result.returncode:
            if result.returncode not in TRANSPORT:raise RuntimeError(f"{provider} download failed with code {result.returncode}; no provider fallback for this error")
            failures.append(f"{provider}: transport error {result.returncode}")
            print(failures[-1],flush=True);continue
        h=hashlib.sha256();size=0
        with p.open("rb") as src:
            while chunk:=src.read(1024*1024):
                size+=len(chunk)
                if size>CAP:raise ValueError("Source exceeds byte limit")
                h.update(chunk)
        if size<1024:raise ValueError("Invalid PBF source size")
        modified=next((line.split(":",1)[1].strip() for line in reversed(headers.read_text(errors="replace").splitlines()) if line.lower().startswith("last-modified:")),None)
        print("OSM extract provider",region,provider,"bytes",size,"last modified",modified,flush=True)
        return p,{"source":url,"extract_provider":provider,"source_sha256":h.hexdigest(),"source_last_modified":modified,"source_bytes":size}
    raise RuntimeError("All approved regional extract providers unavailable: "+"; ".join(failures))
