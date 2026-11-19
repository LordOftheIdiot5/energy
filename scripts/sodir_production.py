"""Official NOD monthly saleable production; year partitions with immutable revisions."""
import argparse, hashlib, json, math, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from hydro_extended import write_json

API="https://factmaps.sodir.no/api/rest/services/DataService/Data/FeatureServer/7300"
PAGE="https://factpages.sodir.no/en/field/tableview/production/saleable/monthly"
LICENSE="https://data.norge.no/nlod/en/2.0"
ATTR="Norwegian Offshore Directorate (Sodir); normalized by Nordl"
FIELDS={
    "prfPrdOilNetMillSm3":"oil_million_Sm3",
    "prfPrdGasNetBillSm3":"gas_billion_Sm3",
    "prfPrdNGLNetMillSm3":"ngl_million_Sm3",
    "prfPrdCondensateNetMillSm3":"condensate_million_Sm3",
    "prfPrdOeNetMillSm3":"oil_equivalent_million_Sm3",
    "prfPrdProducedWaterInFieldMillS":"produced_water_million_Sm3"}
IDENTITY=("OBJECTID","prfYear","prfMonth","prfNpdidInformationCarrier","prfInformationCarrier","prfInformationCarrierKind")
def get(url):
    with urlopen(Request(url,headers={"Accept":"application/json","User-Agent":"Nordl-Energy/1.0 (energy.nordl.dev)"}),timeout=45) as r:
        doc=json.load(r)
    if "error" in doc:raise ValueError("Sodir API: "+str(doc["error"])[:220])
    return doc
def query(params,getter):
    return getter(API+"/query?"+urlencode({"f":"json",**params}))
def normalize(a,year):
    if any(k not in a for k in (*IDENTITY,*FIELDS)):raise ValueError("Missing source field")
    m=a["prfMonth"]; ident=a["prfNpdidInformationCarrier"]; name=a["prfInformationCarrier"]
    if a["prfYear"]!=year or type(m)!=int or not 1<=m<=12 or type(ident)!=int or ident<=0 or not isinstance(name,str) or not name.strip():raise ValueError("Invalid source identity")
    r={"id":str(ident),"name":name,"period":f"{year:04d}-{m:02d}","time":f"{year:04d}-{m:02d}-01T00:00:00Z","carrierKind":a["prfInformationCarrierKind"]}
    for src,dst in FIELDS.items():
        v=a[src]
        if v is not None and (type(v) not in (float,int) or not math.isfinite(v)):raise ValueError("Invalid numeric observation")
        r[dst]=v
    return r
def collect(root,year,getter=get,stamp=None):
    if not 1971<=year<=datetime.now(timezone.utc).year:raise ValueError("Out-of-range year")
    root=Path(root); stamp=stamp or datetime.now(timezone.utc).isoformat()
    where=f"prfYear={year} AND prfMonth>0 AND prfMonth<=12"
    count=query({"where":where,"returnCountOnly":"true"},getter)["count"]
    if type(count)!=int or not 0<count<=10000:raise ValueError("Empty or unexpected count")
    rows=[];seen=set();offset=0
    while offset<count:
        d=query({"where":where,"outFields":",".join((*IDENTITY,*FIELDS)),"returnGeometry":"false","orderByFields":"OBJECTID ASC","resultOffset":offset,"resultRecordCount":1000},getter)
        page=d["features"]
        if not page or len(page)>1000:raise ValueError("Incomplete pagination")
        for f in page:
            row=normalize(f["attributes"],year);k=(row["id"],row["period"])
            if k in seen:raise ValueError("Duplicate field-month")
            seen.add(k);rows.append(row)
        offset+=len(page)
    if len(rows)!=count or query({"where":where,"returnCountOnly":"true"},getter)["count"]!=count:raise ValueError("Source count changed during retrieval")
    rows.sort(key=lambda r:(r["period"],r["id"]))
    if not any(r["oil_million_Sm3"] is not None or r["gas_billion_Sm3"] is not None for r in rows):raise ValueError("No production measurements")
    doc={"schema_version":1,"provider":"sodir","source":API,"source_page":PAGE,"license":LICENSE,"attribution":ATTR,"year":year,"generated":stamp,"source_count":count,"notice":"Monthly saleable production per field or discovery; reported units in column names. Null means not supplied. Oil equivalent is source-reported; do not sum it with constituents. Not actual sales, revenue or company equity production.","rows":rows}
    p=root/"sodir-production"/f"{year}.json";p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        old=json.loads(p.read_text())
        if old["rows"]==rows:print("Sodir",year,count,"unchanged");return old
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        rev=root/"sodir-revisions"/str(year)/(h+".json");rev.parent.mkdir(parents=True,exist_ok=True)
        if not rev.exists():write_json(rev,old)
    write_json(p,doc)
    print("Sodir",year,count,"field-month records",len({r["id"] for r in rows}),"fields/discoveries",rows[0]["period"],rows[-1]["period"])
    return doc
def public_files(root):
    for p in sorted((root/"sodir-production").glob("*.json"),reverse=True):
        d=json.loads(p.read_text())
        if not re.fullmatch(r"\d{4}",p.stem) or d.get("year")!=int(p.stem) or d.get("provider")!="sodir" or d.get("schema_version")!=1 or d.get("source")!=API or d.get("license")!=LICENSE or d.get("attribution")!=ATTR or not d.get("rows") or d.get("source_count")!=len(d["rows"]):raise ValueError("Unexpected Sodir provenance")
        if any(not r["period"].startswith(p.stem+"-") for r in d["rows"]):raise ValueError("Wrong year partition")
        yield p.relative_to(root).as_posix()
def main():
    a=argparse.ArgumentParser();a.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]/"data");a.add_argument("--year",type=int);a.add_argument("--force",action="store_true");a.add_argument("--history",action="store_true");args=a.parse_args()
    now=datetime.now(timezone.utc);year=args.year or now.year
    if args.history:
        # Newest missing historical year first; current year has its own daily refresh.
        year=next((y for y in range(now.year-1,1970,-1) if not (args.root/"sodir-production"/f"{y}.json").exists()),now.year-1)
    try:collect(args.root,year)
    except Exception as e:
        print("::warning::Sodir collection failed; last-known retained:",type(e).__name__,str(e)[:250])
        if args.force:raise
if __name__=="__main__":main()
