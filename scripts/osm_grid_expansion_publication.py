"""Checksum-pinned projection; keep reviewed archive and public atlas distinct."""
import hashlib,json,shutil
from pathlib import Path
from osm_grid_expansion_archive import REVIEWED
from osm_grid_expansion import EXPANSION
from osm_grid_publication import validate,name,LICENSE

def stage_expansion(root,out):
    root,out=Path(root),Path(out)
    manifest=json.loads((root/"reviewed-cohort-v1.json").read_text(encoding="utf-8"))
    entries=manifest["datasets"]
    if manifest.get("schema_version")!=1 or manifest.get("reviewed_run")!=45322295671 or len(entries)!=4 or {e["region"] for e in entries}!=set(REVIEWED):
        raise ValueError("Unreviewed expansion cohort")
    ready=[]
    for e in entries:
        r=e["region"];digest,count=REVIEWED[r]
        if e["path"]!=r+"/"+digest+".json" or e["sha256"]!=digest or e["records"]!=count:raise ValueError("Expansion admission mismatch")
        p=root/e["path"];doc=validate(p,r,sources=EXPANSION)
        raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=digest or len(raw)!=e["bytes"] or doc["source_records"]!=count or doc["source_sha256"]!=e["source_sha256"] or doc["source"]!=e["source"] or doc["retrieved"]!=e["retrieved"]:raise ValueError("Expansion archive integrity mismatch")
        row={k:doc[k] for k in ("region","source","extract_provider","source_records","category_counts","retrieved","source_last_modified","source_sha256","license","attribution")}
        ready.append((p,row|{"path":name(r),"sha256":digest}))
    out.mkdir(parents=True,exist_ok=False)
    for p,e in ready:
        shutil.copyfile(p,out/e["path"])
        if hashlib.sha256((out/e["path"]).read_bytes()).hexdigest()!=e["sha256"]:raise ValueError("Projection readback failed")
    index={"schema_version":1,"license":LICENSE,"attribution":"© OpenStreetMap contributors","source_terms":"https://www.openstreetmap.org/copyright","notice":"Reviewed historical ODbL regional reference, not an engineering grid model or live operation. Source-object counts, not unique facilities.","datasets":[e for _,e in ready]}
    (out/"index-v1.json").write_text(json.dumps(index,indent=2)+"\n",encoding="utf-8")
