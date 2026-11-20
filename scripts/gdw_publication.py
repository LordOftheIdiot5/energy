"""Validate and retain an immutable normalized GDW release, distinct from other sources."""
import argparse,hashlib,json,math,re,shutil
from datetime import datetime
from pathlib import Path
from gdw_barriers import DOI,LICENSE,ATTR,EXPECTED
NAME="gdw-barriers-v1.json"
META={"schema_version","provider","release","source","source_file","source_sha256","license","attribution","retrieved","source_records","notice","rows"}
ROW={"id","geometry","dam_name","reservoir_name","barrier_type","country","river"}
def validate(path,expected=EXPECTED):
    path=Path(path)
    if not path.is_file() or path.is_symlink():raise ValueError("Missing or unsafe GDW archive")
    x=json.loads(path.read_text(encoding="utf-8"))
    if set(x)!=META or x["schema_version"]!=1 or x["provider"]!="global-dam-watch" or x["release"]!="1.0" or x["source"]!="https://doi.org/"+DOI or x["source_file"]!="GDW_v1_0_shp.zip" or x["license"]!=LICENSE or x["attribution"]!=ATTR or not re.fullmatch(r"[a-f0-9]{64}",x["source_sha256"]):raise ValueError("Unapproved GDW provenance")
    if not isinstance(x["notice"],str) or not x["notice"].strip() or len(x["notice"])>1000 or datetime.fromisoformat(x["retrieved"]).tzinfo is None:raise ValueError("Missing notice or retrieval time")
    if x["source_records"]!=expected or not isinstance(x["rows"],list) or len(x["rows"])!=expected:raise ValueError("Incomplete source release")
    ids=set()
    for r in x["rows"]:
        if set(r)!=ROW or type(r["id"]) is not int or r["id"]<=0 or r["id"] in ids:raise ValueError("Invalid or duplicate GDW identity")
        ids.add(r["id"]);g=r["geometry"]
        if not isinstance(g,list) or len(g)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in g) or abs(g[0])>180 or abs(g[1])>90:raise ValueError("Invalid map coordinates")
        if any(v is not None and (not isinstance(v,str) or not v.strip() or len(v)>512) for k,v in r.items() if k not in ("id","geometry")):raise ValueError("Invalid GDW text field")
    return x
def promote(src,root):
    src,root=Path(src),Path(root);new=validate(src);dst=root/NAME
    if dst.exists():
        old=validate(dst)
        if old["source_sha256"]!=new["source_sha256"] or old["rows"]!=new["rows"]:raise ValueError("Pinned release changed; preserve prior archive and review")
        return False
    root.mkdir(parents=True,exist_ok=True);temp=dst.with_suffix(".tmp");shutil.copyfile(src,temp);temp.replace(dst);return True
def stage_gdw(root,out):
    root,out=Path(root),Path(out);src=root/NAME
    if not src.exists():return
    x=validate(src)
    out.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,out/NAME)
    index={"schema_version":1,"provider":x["provider"],"release":x["release"],"path":NAME,"source_records":x["source_records"],"source":x["source"],"source_sha256":x["source_sha256"],"sha256":hashlib.sha256(src.read_bytes()).hexdigest(),"retrieved":x["retrieved"],"license":LICENSE,"attribution":ATTR,"notice":x["notice"]}
    (out/"index-v1.json").write_text(json.dumps(index,indent=2)+"\n",encoding="utf-8")
    print("GDW publication staged",x["source_records"],"source records")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--incoming",type=Path,required=True);p.add_argument("--root",type=Path,required=True);args=p.parse_args();print("GDW release promoted",promote(args.incoming,args.root))
