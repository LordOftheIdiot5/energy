"""Append validated, rights-cleared records into monthly datasets."""
import hashlib,json
from pathlib import Path
from datetime import date,datetime,timezone
from hydro_extended import write_json
from price_rights import permitted
from delivery_prices import bounds,number
def partition(directory,kind,day,record,observed):
    month=date.fromisoformat(day).strftime("%Y-%m")
    parent=Path(directory)/"archive"/kind;parent.mkdir(parents=True,exist_ok=True)
    path=parent/(month+".json")
    data=json.loads(path.read_text()) if path.exists() else {"schema_version":1,"kind":kind,"month":month,"rows":[]}
    if data.get("schema_version")!=1 or data.get("kind")!=kind or data.get("month")!=month:raise ValueError("Invalid archive")
    sha=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    if any(r.get("sha256")==sha for r in data["rows"]):return False
    data["rows"].append({**record,"first_retrieved_at":observed,"sha256":sha})
    write_json(path,data);return True
def append(directory,payload,snow=None):
    stamp=payload["generated"];datetime.fromisoformat(stamp)
    added=0
    for r in payload.get("europe",[]):
        if r.get("stale") or not r.get("complete") or r.get("marketType")!="day_ahead" or not permitted(r.get("zone"),r.get("licenseInfo")):continue
        day=r["date"];a,b=bounds(date.fromisoformat(day))
        ts=r.get("startsUtc",[]);v=r.get("cents",[]);step=r.get("intervalSeconds")
        if step not in (900,3600) or len(ts)!=len(v) or len(ts)*step!=(b-a).total_seconds() or not all(number(x) for x in v):continue
        expected=[datetime.fromtimestamp(a.timestamp()+i*step,timezone.utc).isoformat() for i in range(len(v))]
        if ts!=expected:continue
        record={"zone":r["zone"],"delivery_date":day,"unit":"EUR/MWh","interval_seconds":step,"start_utc":ts[0],"prices":[round(x*10,3) for x in v],"source":r.get("sourceUrl","https://api.energy-charts.info/price"),"attribution":r["priceSource"],"license":r["licenseInfo"]}
        added+=partition(directory,"day-ahead",day,record,r.get("retrievedAt",stamp))
    for r in (snow or {}).get("snow",[]):
        if not number(r.get("value_mm")) or r["value_mm"]<0 or r.get("stale") or not r.get("source","").startswith("https://gts.nve.no/api/GridTimeSeries/"):continue
        record={k:r[k] for k in ("id","date","geometry","source_utm33","value_mm","source")}
        record.update({"unit":"mm water","attribution":"NVE / seNorge","license":"https://data.norge.no/nlod/"})
        added+=partition(directory,"snow-water",r["date"],record,r.get("retrievedAt",(snow or {}).get("generated",stamp)))
    root=Path(directory)/"archive";manifest=[]
    for path in sorted(root.glob("*/*.json")):
        d=json.loads(path.read_text());manifest.append({"kind":d["kind"],"month":d["month"],"rows":len(d["rows"]),"path":str(path.relative_to(directory)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    root.mkdir(parents=True,exist_ok=True)
    write_json(root/"index-v1.json",{"schema_version":1,"generated":stamp,"notice":"Own versioned collection of cleared open-source observations; revisions retained. Nordic reseller, GB, Yahoo, GIE and unchecked sources excluded.","partitions":manifest})
    print("Open history:",added,"new unique records;",len(manifest),"partitions")
    return added
