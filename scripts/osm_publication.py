"""Maintain a separately licensed ODbL source archive and explicit public projection."""
import argparse, hashlib,json,math,re,shutil
from pathlib import Path
from osm_datacentres import REGIONS,LICENSE,ATTRIBUTION,classified
FIELDS={"id","name","geometry","source_object","category","geometry_kind","classification"}
META={"schema_version","provider","region","source","source_sha256","source_last_modified","retrieved","license","attribution","source_notice","rejected_tagged_objects","rows"}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def validate(p,region):
    if p.is_symlink() or not p.is_file():raise ValueError("Missing or unsafe ODbL source")
    x=json.loads(p.read_text())
    if set(x)!=META or x["schema_version"]!=1 or x["provider"]!="osm" or x["region"]!=region or x["license"]!=LICENSE or x["attribution"]!=ATTRIBUTION:raise ValueError("Unexpected ODbL metadata")
    if x["source"]!=f"https://download.geofabrik.de/europe/{REGIONS[region]}-latest.osm.pbf" or not re.fullmatch(r"[a-f0-9]{64}",x["source_sha256"]):raise ValueError("Unverified source")
    if not x["rows"] or not x["retrieved"] or not x["source_notice"]:raise ValueError("Empty or undated source; retain previous snapshot")
    ids=set()
    for r in x["rows"]:
        if set(r)!=FIELDS or r["category"]!="data_centre" or not isinstance(r["name"],str) or not r["name"].strip() or len(r["name"])>240:raise ValueError("Unexpected source record")
        m=re.fullmatch(r"osm:(node|way|relation):([1-9][0-9]*)",r["id"])
        if not m or r["id"] in ids:raise ValueError("Invalid or duplicate source identity")
        if r["source_object"]!=f"https://www.openstreetmap.org/{m[1]}/{m[2]}":raise ValueError("Source identity mismatch")
        if r["geometry_kind"]!=("mapped point" if m[1]=="node" else "representative point of mapped area"):raise ValueError("Unexpected geometry type")
        tags=r["classification"]
        if not isinstance(tags,dict) or not set(tags)<= {"telecom","building","industrial"} or not classified(tags) or any(v not in ("data_center","data_centre") for v in tags.values()):raise ValueError("Unapproved tags")
        g=r["geometry"]
        if not isinstance(g,list) or len(g)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in g) or abs(g[0])>180 or abs(g[1])>90:raise ValueError("Invalid source geometry")
        ids.add(r["id"])
    return x
def promote(incoming,root):
    incoming,root=Path(incoming),Path(root)
    # Validate both before changing either. Keep last known data on source failure.
    for region in REGIONS:validate(incoming/f"{region.lower()}-datacentres.json",region)
    for region in REGIONS:
        name=f"{region.lower()}-datacentres.json";src=incoming/name;dst=root/name
        if dst.exists():
            old=validate(dst,region)
            new=validate(src,region)
            if old["rows"]==new["rows"]:continue
            archived=root/"revisions"/region/(digest(dst)+".json")
            archived.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(dst,archived)
        root.mkdir(parents=True,exist_ok=True);tmp=dst.with_suffix(".tmp");shutil.copyfile(src,tmp);tmp.replace(dst)
def stage_osm(root,out):
    root,out=Path(root),Path(out)
    if not root.exists():return
    entries=[]
    out.mkdir(parents=True,exist_ok=True)
    for region in REGIONS:
        name=f"{region.lower()}-datacentres.json";p=root/name
        if not p.exists():continue
        x=validate(p,region);shutil.copyfile(p,out/name)
        entries.append({"region":region,"path":name,"source_records":len(x["rows"]),"retrieved":x["retrieved"],"source":x["source"],"sha256":digest(p),"license":LICENSE,"attribution":ATTRIBUTION})
    if entries:
        (out/"index-v1.json").write_text(json.dumps({"schema_version":1,"license":LICENSE,"attribution":ATTRIBUTION,"source_terms":"https://www.openstreetmap.org/copyright","notice":"Separate ODbL derived database. Mapped source records are not a complete facility census; no capacity or operating status inferred.","datasets":entries},indent=2))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--incoming",type=Path,required=True);p.add_argument("--root",type=Path,required=True);args=p.parse_args();promote(args.incoming,args.root)
