"""Approved EIA-860M public dataset partitions — never expose raw workbook.

All published rows have explicit coordinates, original source-status semantics
and a pinned September 2026 EIA checksum. Split by inventory for small
on-demand downloads; never present generator nameplate MW as actual output.
"""
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

SOURCE_SHA="bcef74e1af991680731aeecfda967f5950db4ce739bb584edd8b8774c7e6da17"
SOURCE_PAGE="https://www.eia.gov/electricity/data/eia860m/"
RIGHTS="https://www.eia.gov/about/copyrights_reuse.php"
SPLITS={"operating":28712,"planned":2357,"retired":7303,"canceled_postponed":1676}
TABS={"Operating":"operating","Operating_PR":"operating","Planned":"planned","Planned_PR":"planned",
      "Retired":"retired","Retired_PR":"retired","Canceled or Postponed":"canceled_postponed"}
TOTAL=40048
SOURCE_ROWS=40163
def sha(data): return hashlib.sha256(data).hexdigest()
def encode(doc): return (json.dumps(doc,ensure_ascii=False,separators=(",",":"))+"\n").encode("utf-8")
def check(doc):
    if doc.get("schema_version")!=1 or doc.get("release")!="2026-09" or doc.get("published")!="2026-10-23" or doc.get("source")!=SOURCE_PAGE or doc.get("rights")!=RIGHTS or doc.get("source_sha256")!=SOURCE_SHA:
        raise ValueError("Unapproved EIA source, rights or release")
    counts=doc.get("counts")
    rows=doc.get("rows")
    if not isinstance(counts,dict) or counts.get("mapped_rows")!=TOTAL or counts.get("source_rows")!=SOURCE_ROWS or not isinstance(rows,list) or len(rows)!=TOTAL:
        raise ValueError("EIA coverage regression")
    observed=Counter()
    seen=set()
    for row in rows:
        rid=row.get("id")
        inventory=row.get("inventory")
        tab=row.get("source_tab")
        point=row.get("coordinates")
        mw=row.get("nameplate_mw")
        if inventory not in SPLITS or TABS.get(tab)!=inventory or not isinstance(rid,str) or rid in seen or not re.fullmatch(r"eia860m-[a-z_]+:[0-9]{1,8}:[^\s:]{1,40}",rid) or not rid.startswith("eia860m-"+tab.lower().replace(" ","_")+":"):
            raise ValueError("Unsafe EIA generator identity/category")
        if not row.get("plant") or not row.get("technology") or not row.get("status") or not row.get("plant_id") or not row.get("generator_id") or not row.get("state"):
            raise ValueError("Missing EIA generator identity or classification")
        if not isinstance(point,list) or len(point)!=2 or not all(type(v) in (int,float) and math.isfinite(v) for v in point) or not (-180<=point[0]<=180 and -90<=point[1]<=90) or not (point[0]!=0 and point[1]!=0):
            raise ValueError("Invalid EIA geographic location")
        if mw is not None and (type(mw) not in (int,float) or not math.isfinite(mw) or not 0<=mw<=30000):
            raise ValueError("Unapproved EIA nameplate capacity")
        if any(key in row for key in ("generation_mw","power_output_mw","capacity_factor","is_operational")):
            raise ValueError("Inferred generation or operating claim is prohibited")
        seen.add(rid);observed[inventory]+=1
    if dict(observed)!=SPLITS:
        raise ValueError("Unexpected EIA inventory coverage")
    return True

def stage(data_dir,out_dir):
    data_dir=Path(data_dir);out_dir=Path(out_dir)
    src=data_dir/"eia860m-generators-v1.json"
    if not src.is_file() or src.is_symlink():
        raise ValueError("Missing pinned EIA source projection")
    doc=json.loads(src.read_text(encoding="utf-8"))
    check(doc)
    out_dir.mkdir(parents=True,exist_ok=True)
    manifest={"schema_version":1,"release":doc["release"],"published":doc["published"],
              "source":SOURCE_PAGE,"rights":RIGHTS,"source_sha256":SOURCE_SHA,
              "attribution":doc["attribution"],"caveat":doc["caveat"],
              "counts":doc["counts"],"inventories":[]}
    for kind,count in SPLITS.items():
        records=[r for r in doc["rows"] if r["inventory"]==kind]
        if len(records)!=count:
            raise ValueError("EIA category count mismatch")
        name=kind+"-v1.json"
        part={"schema_version":1,"release":doc["release"],"inventory":kind,
              "source_sha256":SOURCE_SHA,"source":SOURCE_PAGE,"rights":RIGHTS,
              "rows":records}
        payload=encode(part)
        (out_dir/name).write_bytes(payload)
        manifest["inventories"].append({"id":kind,"path":"data/eia860m/"+name,
                                         "records":count,"sha256":sha(payload)})
    (out_dir/"index-v1.json").write_bytes(encode(manifest))
    return manifest
