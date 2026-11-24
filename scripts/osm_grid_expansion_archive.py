"""Retain reviewed ODbL expansion snapshots outside the public map cohort.
Bootstrap accepts only exact reviewed artifact bytes. No raw PBF or public admission.
"""
import argparse,hashlib,json,os
from pathlib import Path
from osm_grid_expansion import EXPANSION
from osm_grid_publication import validate,name

REVIEWED={
    "AL":("526341154d6655224756a1bdd9a8dada53cf965cc4753dc3128454f79493076d",775),
    "EE":("9546f4367537349806880ba7ebac051498807c809676e6d8d04087209b0647a5",3921),
    "FO":("72fceab417aec8e5634b25b1fd1f6c0b61222a4d4441f2bcd0267aa52e8d19de",67),
    "LV":("ff2964e5efca64939e3e18544d814328c44fb7dab368fe9792f6b16638854e80",12775),
}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def archive(incoming,root,*,reviewed=None):
    incoming,root=Path(incoming),Path(root)
    reviewed=REVIEWED if reviewed is None else reviewed
    if set(reviewed)!=set(EXPANSION):raise ValueError("Incomplete cohort")
    staged=[]
    # Validate entire cohort before any writes.
    for region,(expected,count) in sorted(reviewed.items()):
        p=incoming/name(region)
        doc=validate(p,region,sources=EXPANSION)
        raw=p.read_bytes()
        if digest(raw)!=expected or doc["source_records"]!=count:raise ValueError("Reviewed artifact mismatch")
        dst=root/region/(expected+".json")
        if dst.is_symlink() or (dst.exists() and dst.read_bytes()!=raw):raise ValueError("Archive collision")
        staged.append((dst,raw,{"region":region,"sha256":expected,"path":region+"/"+dst.name,"records":count,"bytes":len(raw),"retrieved":doc["retrieved"],"source":doc["source"],"source_sha256":doc["source_sha256"],"license":doc["license"]}))
    for dst,raw,_ in staged:
        dst.parent.mkdir(parents=True,exist_ok=True)
        try:
            with dst.open("xb") as out:out.write(raw)
        except FileExistsError:
            if dst.is_symlink() or dst.read_bytes()!=raw:raise ValueError("Archive collision")
        if digest(dst.read_bytes())!=digest(raw):raise ValueError("Archive readback mismatch")
    result={"schema_version":1,"reviewed_run":45322295671,"public_map_admitted":False,"raw_pbf_retained":False,"datasets":[row for _,_,row in staged]}
    manifest=json.dumps(result,indent=2,sort_keys=True)+"\n"
    path=root/"reviewed-cohort-v1.json"
    try:
        with path.open("x",encoding="utf-8") as out:out.write(manifest)
    except FileExistsError:
        if path.is_symlink() or path.read_text(encoding="utf-8")!=manifest:raise ValueError("Manifest collision")
    return result
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--incoming",type=Path,required=True);p.add_argument("--root",type=Path,required=True);a=p.parse_args()
    print(json.dumps(archive(a.incoming,a.root),indent=2))
