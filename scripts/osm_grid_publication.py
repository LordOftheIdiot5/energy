"""Separate licensed OSM grid archive; retain changed source cohorts and fail closed."""
import argparse,hashlib,json,math,re,shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from osm_extract_sources import SOURCES,CAP,PROVIDER_CAPS
from osm_datacentres import LICENSE
META={"schema_version","provider","region","source","extract_provider","source_sha256","source_last_modified","source_bytes","retrieved","license","attribution","source_records","category_counts","rejected_objects","notice","rows"}
FIELDS={"id","category","name","voltage_v","geometry","source_object"}
CATEGORIES={"substation","overhead_line","underground_power_cable","underwater_power_cable","power_cable_unspecified"}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def name(region):return region.lower()+"-grid-pilot.json"
def point(p):
    return isinstance(p,list) and len(p)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in p) and abs(p[0])<=180 and abs(p[1])<=90
def validate(p,region,*,sources=None):
    sources=SOURCES if sources is None else sources
    p=Path(p)
    if p.is_symlink() or not p.is_file() or p.stat().st_size>25_000_000:raise ValueError("Missing or oversized grid source")
    x=json.loads(p.read_text(encoding="utf-8"))
    if set(x)!=META or x["schema_version"]!=1 or x["provider"]!="osm" or x["region"]!=region or (x["extract_provider"],x["source"]) not in sources[region] or x["license"]!=LICENSE:raise ValueError("Unapproved grid provenance")
    if x["attribution"]!="© OpenStreetMap contributors; "+x["extract_provider"]+" regional extract; selected and normalized by Nordl" or not re.fullmatch(r"[a-f0-9]{64}",x["source_sha256"]) or type(x["source_bytes"]) is not int or not 1024<=x["source_bytes"]<=PROVIDER_CAPS.get((region,x['extract_provider'],x['source']),CAP) or datetime.fromisoformat(x["retrieved"]).tzinfo is None:raise ValueError("Invalid archive evidence")
    if not isinstance(x["notice"],str) or not x["notice"].strip() or not isinstance(x["rows"],list) or not 1<=len(x["rows"])<=100000 or len(x["rows"])!=x["source_records"]:raise ValueError("Invalid archive count")
    ids=set();counts=Counter()
    for r in x["rows"]:
        if set(r)!=FIELDS or r["category"] not in CATEGORIES:raise ValueError("Unapproved fields/category")
        m=re.fullmatch(r"osm:(node|way|relation):([1-9][0-9]*)",r["id"])
        if not m or r["id"] in ids or r["source_object"]!=f"https://www.openstreetmap.org/{m[1]}/{m[2]}":raise ValueError("Invalid source identity")
        ids.add(r["id"]);counts[r["category"]]+=1
        if r["name"] is not None and (not isinstance(r["name"],str) or len(r["name"])>160):raise ValueError("Invalid name")
        v=r["voltage_v"]
        if not isinstance(v,list) or any(type(n) is not int or not 0<n<=1500000 for n in v) or v!=sorted(set(v),reverse=True):raise ValueError("Invalid voltage")
        g=r["geometry"]
        if set(g)!={"type","coordinates"}:raise ValueError("Unexpected geometry fields")
        c=g["coordinates"]
        if r["category"]=="substation":
            if g["type"]!="Point" or not point(c):raise ValueError("Invalid substation reference")
        elif m[1]!="way" or g["type"]!="LineString" or not isinstance(c,list) or not 2<=len(c)<=10000 or not all(point(p) for p in c) or any(a==b for a,b in zip(c,c[1:])):raise ValueError("Invalid generalized line")
    if dict(counts)!=x["category_counts"] or not counts["overhead_line"] or not counts["substation"]:raise ValueError("Invalid category accounting")
    if not isinstance(x["rejected_objects"],dict) or any(k not in CATEGORIES or type(v) is not int or v<0 for k,v in x["rejected_objects"].items()):raise ValueError("Invalid rejection accounting")
    return x
def promote(incoming,root):
    incoming,root=Path(incoming),Path(root)
    new={r:validate(incoming/name(r),r) for r in SOURCES}
    previous={}
    for r in SOURCES:
        dst=root/name(r)
        if dst.exists():
            old=validate(dst,r);previous[r]=old
            if datetime.fromisoformat(new[r]["retrieved"])<datetime.fromisoformat(old["retrieved"]):raise ValueError("Older candidate, retain archive")
            if len(new[r]["rows"])<.8*len(old["rows"]):raise ValueError("Large coverage reduction requires review")
    for r in SOURCES:
        dst=root/name(r);src=incoming/name(r)
        if r in previous:
            if previous[r]["source_sha256"]==new[r]["source_sha256"] and previous[r]["rows"]==new[r]["rows"]:continue
            rev=root/"revisions"/r/(sha(dst)+".json");rev.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(dst,rev)
        root.mkdir(parents=True,exist_ok=True);tmp=dst.with_suffix(".tmp");shutil.copyfile(src,tmp);tmp.replace(dst)
def stage_grid(root,out):
    root,out=Path(root),Path(out)
    if not root.exists():return
    entries=[]
    docs={r:validate(root/name(r),r) for r in SOURCES}
    out.mkdir(parents=True,exist_ok=True)
    for r,x in docs.items():
        p=root/name(r);shutil.copyfile(p,out/name(r))
        entries.append({k:x[k] for k in ("region","source","extract_provider","source_records","category_counts","retrieved","source_last_modified","source_sha256","license","attribution")}|{"path":name(r),"sha256":sha(p)})
    index={"schema_version":1,"license":LICENSE,"attribution":"© OpenStreetMap contributors","source_terms":"https://www.openstreetmap.org/copyright","notice":"Separate ODbL regional display reference, generalized public geography. Not an engineering grid model or measured flow dataset. Source-object counts, not unique physical facilities.","datasets":entries}
    (out/"index-v1.json").write_text(json.dumps(index,indent=2)+"\n",encoding="utf-8")
    print("Grid publication staged",sum(e["source_records"] for e in entries),"source records")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--incoming",type=Path,required=True);p.add_argument("--root",type=Path,required=True);a=p.parse_args();promote(a.incoming,a.root)
