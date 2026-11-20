"""Stage content-addressed tiles ONLY from the already-admitted public WRI file."""
import argparse,hashlib,json,os,re,tempfile
from pathlib import Path
from atlas_vector_tiles import build,MAX_Z
from global_assets import ATTR, LICENSE
def sha(b):return hashlib.sha256(b).hexdigest()
def stage(public):
    public=Path(public).resolve(strict=True)
    source=public/"data"/"global-plants-wri-v130.json"
    if not source.is_file() or source.is_symlink():raise ValueError("Admitted global source missing")
    target=public/"data"/"atlas-tiles"
    if target.exists():raise ValueError("Tile delivery target already exists")
    with tempfile.TemporaryDirectory(prefix="atlas-delivery-",dir=public.parent) as tmp:
        tmp=Path(tmp);work=tmp/"build";release=tmp/"release";release.mkdir()
        build(source,work)
        m=json.loads((work/"manifest.json").read_text())
        raw=(work/"wri-v130-pilot.pmtiles").read_bytes()
        if raw[:7]!=b"PMTiles" or raw[7]!=3 or len(raw)!=m["archive_bytes"] or sha(raw)!=m["archive_sha256"] or sha(source.read_bytes())!=m["source_sha256"]:raise ValueError("Archive identity mismatch")
        if m["attribution"]!=ATTR or m["license"]!=LICENSE or m["source_records"]!=m["projected_records"] or m["outside_mercator_ids"] or set(m["verified_decoded_record_counts"])!={str(z) for z in range(MAX_Z+1)} or any(n!=m["source_records"] for n in m["verified_decoded_record_counts"].values()):raise ValueError("Incomplete or unapproved map archive")
        digest=sha(raw);name=f"wri-v130-{digest}.pmtiles"
        (release/name).write_bytes(raw)
        index={"schema_version":1,"delivery":"same-origin-static","status":"experimental_delivery","path":name,"archive_sha256":digest,"archive_bytes":len(raw),"source_sha256":m["source_sha256"],"source_records":m["source_records"],"source_release":m["source_release"],"attribution":ATTR,"license":LICENSE,"min_zoom":0,"max_zoom":MAX_Z,"probe_ranges":[{"start":s,"end":e,"sha256":sha(raw[s:e+1])} for s,e in [(0,126),(127,255)]],"notice":"Historical reference. Delivery may be tested independently; the production map renderer is unchanged."}
        (release/"index-v1.json").write_text(json.dumps(index,indent=2)+"\n",encoding="utf-8")
        # No partial files in the publication artifact even if encoding or verification fails.
        os.replace(release,target)
        print("Atlas delivery staged",name,len(raw),"bytes",m["source_records"],"source records")
        return index
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--public",type=Path,required=True);stage(p.parse_args().public)
