"""Energinet hourly published source records; preserve corrections and quality versions."""
import argparse, hashlib, json, math, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from hydro_extended import write_json

SOURCE="https://api.energidataservice.dk/dataset/GenerationProdTypeExchange"
META="https://api.energidataservice.dk/meta/dataset/GenerationProdTypeExchange"
LICENSE="https://creativecommons.org/licenses/by/4.0/"
ATTR="Energinet (www.energidataservice.dk); normalized by Nordl"
FIELDS=("GrossCon","OffshoreWindPower","OnshoreWindPower","HydroPower","SolarPower","SolarPowerSelfCon","Biomass","Biogas","Waste","FossilGas","FossilOil","FossilHardCoal","ExchangeGreatBelt","ExchangeGermany","ExchangeSweden","ExchangeNorway","ExchangeNetherlands","ExchangeGreatBritain","CO2PerkWh")
VERSIONS={"Initial":0,"Preliminary":1,"Final":2}
MONTH=re.compile(r"\d{4}-(0[1-9]|1[0-2])")
ZONE=ZoneInfo("Europe/Copenhagen")
def get(url):
    with urlopen(Request(url,headers={"Accept":"application/json","User-Agent":"Nordl-Energy/1.0 (energy.nordl.dev)"}),timeout=45) as r:
        return json.load(r)
def read(p,default):return json.loads(p.read_text()) if p.exists() else default
def digest(r):return hashlib.sha256(json.dumps(r,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def normalize(d,now):
    if d.get("dataset")!="GenerationProdTypeExchange" or not isinstance(d.get("records"),list) or not d["records"] or len(d["records"])>1700:raise ValueError("unexpected response")
    out={}
    for r in d["records"]:
        if r.get("PriceArea") not in ("DK1","DK2") or r.get("Version") not in VERSIONS or not all(k in r for k in FIELDS):raise ValueError("unknown area/version/fields")
        v=r["TimeUTC"]
        if not isinstance(v,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:00:00",v):raise ValueError("unexpected UTC interval")
        t=datetime.fromisoformat(v).replace(tzinfo=timezone.utc)
        if t<datetime(2014,12,31,23,tzinfo=timezone.utc) or t+timedelta(hours=1)>now:raise ValueError("future or out-of-scope interval")
        if r.get("TimeDK")!=t.astimezone(ZONE).replace(tzinfo=None).isoformat():raise ValueError("UTC/local mismatch")
        row={"id":r["PriceArea"],"time":t.isoformat(),"endTime":(t+timedelta(hours=1)).isoformat(),"timeDK":r["TimeDK"],"version":r["Version"]}
        for f in FIELDS:
            n=r[f]
            if n is not None and (type(n) not in (int,float) or not math.isfinite(n)):raise ValueError("non-numeric "+f)
            row[f]=n
        k=(row["id"],row["time"])
        if k in out and out[k]!=row:raise ValueError("conflicting duplicate hour")
        out[k]=row
    return list(out.values())
def envelope(rows,stamp,month=None):
    d={"schema_version":1,"provider":"energinet","source":SOURCE,"source_page":"https://www.energidataservice.dk/tso-electricity/GenerationProdTypeExchange","license":LICENSE,"attribution":ATTR,"generated":stamp,"notice":"Hourly source fields retained without conversion. Initial, Preliminary and Final are source quality versions. Null values remain null. Verify source field units and exchange sign conventions before derived calculations.","rows":rows}
    if month:d["month"]=month
    return d
def archive(root,rows,stamp):
    root=Path(root);groups={}
    for r in rows:groups.setdefault(r["time"][:7],[]).append(r)
    for month,new in groups.items():
        p=root/"energinet-history"/(month+".json");p.parent.mkdir(parents=True,exist_ok=True)
        old=read(p,{"rows":[]});by={(r["id"],r["time"]):r for r in old["rows"]}
        revp=root/"energinet-revisions"/(month+".json")
        rev=read(revp,{"rows":[]});byrev={r["revision"]:r for r in rev["rows"]}
        changed=False
        for r in new:
            k=r["id"],r["time"];prior=by.get(k)
            if prior and prior==r:continue
            if prior:
                # Never replace a higher-quality settlement record with an initial value.
                keep,discard=(prior,r) if VERSIONS[prior["version"]]>VERSIONS[r["version"]] else (r,prior)
                h=digest(discard)
                if h not in byrev:byrev[h]={**discard,"revision":h,"archivedAt":stamp}
                if keep==prior:continue
            by[k]=r;changed=True
        if byrev and list(byrev.values())!=rev["rows"]:
            revp.parent.mkdir(parents=True,exist_ok=True);write_json(revp,envelope(list(byrev.values()),stamp,month))
        if changed:write_json(p,envelope(sorted(by.values(),key=lambda r:(r["time"],r["id"])),stamp,month))
    # Latest observation window is independent of historical backfill.
    files=sorted((root/"energinet-history").glob("*.json"))
    recent=[r for p in files[-2:] for r in read(p,{"rows":[]})["rows"]]
    if recent:
        cutoff=(datetime.fromisoformat(max(r["time"] for r in recent))-timedelta(days=14)).isoformat()
        recent=sorted((r for r in recent if r["time"]>=cutoff),key=lambda r:(r["time"],r["id"]))
        p=root/"energinet-v1.json"
        if read(p,{"rows":[]})["rows"]!=recent:write_json(p,envelope(recent,stamp))
def collect(root,history=False,getter=get,now=None):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);now=now or datetime.now(timezone.utc);stamp=now.isoformat()
    statep=root/"energinet-backfill-state-v1.json";state=read(statep,{"next":"2015-01","completed":[]})
    if history:
        month=state["next"]
        if not MONTH.fullmatch(month):raise ValueError("invalid backfill state")
        y,m=map(int,month.split("-"));end=f"{y+(m==12):04d}-{m%12+1:02d}"
        if month>=now.astimezone(ZONE).strftime("%Y-%m"):return
        params={"start":month+"-01","end":end+"-01","limit":0}
    else:
        params={"start":"now","startOffset":"-P14D","end":"now","limit":0}
    d=getter(SOURCE+"?"+urlencode(params));rows=normalize(d,now)
    if history and any(r["timeDK"][:7]!=month for r in rows):raise ValueError("history outside requested local month")
    archive(root,rows,stamp)
    if history:
        state["completed"].append({"month":month,"rows":len(rows),"retrievedAt":stamp});state["next"]=end;write_json(statep,state)
    print("Energinet",len(rows),"normalized hourly rows",min(r["time"] for r in rows),max(r["time"] for r in rows),"zones",sorted({r["id"] for r in rows}),"versions",sorted({r["version"] for r in rows}))
    return rows
def public_files(root):
    paths=[root/"energinet-v1.json",*sorted((root/"energinet-history").glob("*.json"))]
    for p in paths:
        if not p.exists():continue
        d=read(p,{})
        if d.get("provider")!="energinet" or d.get("schema_version")!=1 or d.get("source")!=SOURCE or d.get("license")!=LICENSE or d.get("attribution")!=ATTR or not d.get("rows"):raise ValueError("invalid Energinet provenance")
        if p.parent.name=="energinet-history" and (not MONTH.fullmatch(p.stem) or d.get("month")!=p.stem or any(r["time"][:7]!=p.stem for r in d["rows"])):raise ValueError("invalid partition")
        yield p.relative_to(root).as_posix()
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--history",action="store_true");a.add_argument("--force",action="store_true");a.add_argument("--metadata",action="store_true");a.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]/"data");args=a.parse_args()
    try:
        if args.metadata:
            m=get(META); print("Energinet metadata",json.dumps(m,ensure_ascii=False)[:24000])
        else:collect(args.root,args.history)
    except Exception as e:
        print("Energinet:",type(e).__name__,str(e)[:250],"; last-known data retained")
        if args.force:raise
