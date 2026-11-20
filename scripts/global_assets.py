"""Pinned WRI v1.3.0 global historical plant reference. No current status inferred."""
import argparse,csv,hashlib,io,json,math,zipfile
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from hydro_extended import write_json
from asset_reference import ZIP,WRI
LICENSE="https://creativecommons.org/licenses/by/4.0/"
ATTR="Global Energy Observatory, Google, KTH Royal Institute of Technology in Stockholm, Enipedia, World Resources Institute (2021), Global Power Plant Database v1.3.0; normalized by Nordl"
FILE="global-plants-wri-v130.json"
def finite(value):
    try:
        n=float(value)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError):return None
def normalize(reader):
    rows=[];seen=set();rejected=0
    for a in reader:
        ident=a["gppd_idnr"].strip();name=a["name"].strip();lat=finite(a["latitude"]);lon=finite(a["longitude"]);mw=finite(a["capacity_mw"])
        if not ident or not name or lat is None or lon is None or abs(lat)>90 or abs(lon)>180 or (mw is not None and mw<0):
            rejected+=1;continue
        if ident in seen:raise ValueError("Duplicate WRI identity")
        seen.add(ident)
        rows.append({"id":ident,"name":name,"country":a["country"],"country_name":a["country_long"],"geometry":[lon,lat],"fuel":a["primary_fuel"] or "Unknown","capacity_mw":mw,"owner":a.get("owner") or None,"commissioning_year":finite(a.get("commissioning_year")),"source_name":a.get("source") or None})
    return rows,rejected
def validate(doc):
    rows=doc["rows"]
    if doc.get("provider")!="wri-global" or doc.get("source")!=WRI or doc.get("license")!=LICENSE or doc.get("attribution")!=ATTR or doc.get("release")!="1.3.0" or doc.get("release_year")!=2021 or doc.get("schema_version")!=1:raise ValueError("Unexpected global plant provenance")
    if not 30000<=len(rows)<=36000 or len({r["country"] for r in rows})<150 or len({r["id"] for r in rows})!=len(rows):raise ValueError("Unexpected global coverage")
    if doc["source_rows"]!=len(rows)+doc["rejected"]:raise ValueError("Source record accounting")
    for r in rows:
        x,y=r["geometry"];mw=r["capacity_mw"]
        if not math.isfinite(x) or not math.isfinite(y) or abs(x)>180 or abs(y)>90 or (mw is not None and (not math.isfinite(mw) or mw<0)):raise ValueError("Invalid asset geometry/capacity")
    return doc
def collect(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);p=root/FILE
    if p.exists():
        doc=validate(json.loads(p.read_text()));print("WRI retained",len(doc["rows"]),"rows");return doc
    with urlopen(Request(ZIP,headers={"User-Agent":"Nordl Energy (https://energy.nordl.dev/)"}),timeout=90) as response:raw=response.read(25_000_001)
    if len(raw)>25_000_000:raise ValueError("Archive exceeds bounded size")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=[m for m in z.infolist() if m.filename.lower().endswith("global_power_plant_database.csv") and m.file_size<50_000_000]
        if len(members)!=1:raise ValueError("Unexpected WRI archive")
        with z.open(members[0]) as f:rows,rejected=normalize(csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig")))
    doc={"schema_version":1,"provider":"wri-global","source":WRI,"license":LICENSE,"attribution":ATTR,"release":"1.3.0","release_year":2021,"generated":datetime.now(timezone.utc).isoformat(),"source_sha256":hashlib.sha256(raw).hexdigest(),"source_rows":len(rows)+rejected,"rejected":rejected,"notice":"Historical snapshot (2021), not current operational status or ownership. Source records may overlap other registers.","rows":rows}
    validate(doc);write_json(p,doc);print("WRI worldwide",len(rows),"rows",len({r["country"] for r in rows}),"countries",rejected,"rejected");return doc
def public_files(root):
    p=root/FILE
    if p.exists():validate(json.loads(p.read_text()));yield FILE
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]/"data");a.add_argument("--force",action="store_true");args=a.parse_args()
    try:collect(args.root)
    except Exception as e:
        print("::warning::WRI global",type(e).__name__,str(e)[:200])
        if args.force:raise
