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
    # Archive only explicitly CC BY shared ENTSO-E load forecasts and physical flows.
    # Input points remain source-reported; A03 constant curves are not expanded.
    shared_path=Path(directory)/"entsoe-open.json"
    if shared_path.exists():
        from shared_energy import validate_shared
        shared=validate_shared(json.loads(shared_path.read_text()))
        allowed_zones=set("NO1 NO2 NO3 NO4 NO5 SE1 SE2 SE3 SE4 DK1 DK2 FI DE-LU FR NL".split())
        for s in shared["series"]:
            if s.get("status")!="ok" or not s.get("points"):continue
            if s["kind"]=="day_ahead_load_forecast" and s.get("zone") not in allowed_zones:continue
            if s["kind"]=="physical_flow" and (s.get("from") not in allowed_zones or s.get("to") not in allowed_zones):continue
            day=datetime.fromisoformat(s["startUtc"].replace("Z","+00:00")).date().isoformat()
            record={k:s[k] for k in ("id","kind","article","startUtc","endUtc","unit","points")}
            for k in ("zone","from","to"):
                if k in s:record[k]=s[k]
            record.update({"source":shared["sourceUrl"],"attribution":"ENTSO-E Transparency Platform; normalized by Stockwatch / Nordl","license":shared["licenseUrl"],"note":"Explicit reported points, not complete interval coverage or observed load forecast actuals."})
            added+=partition(directory,"entsoe-series",day,record,shared["generated"])
    # Keep changed MET snapshots, not repeated cached runs; source validity
    # and model update time are preserved separately from retrieval time.
    for zone,w in payload.get("weather",{}).items():
        if w.get("stale") or not w.get("sourceUpdatedAt") or not w.get("forecastStart"):continue
        if zone not in ("NO1","NO2","NO3","NO4","NO5","SE1","SE2","SE3","SE4"):continue
        try:day=datetime.fromisoformat(w["sourceUpdatedAt"].replace("Z","+00:00")).date().isoformat()
        except (ValueError,TypeError):continue
        record={k:w[k] for k in ("place","sourceUpdatedAt","forecastStart","forecastEnd","tempNow","windNow","tempMin","tempMax","windMean","hours","heatingDegreeHours","precipCoverageHours","precipMm","coldPrecipMm","positiveDegreeHours") if k in w}
        record.update({"zone":zone,"source":"https://api.met.no/weatherapi/locationforecast/2.0/","attribution":"MET Norway; Nordl derived point summaries","license":"https://creativecommons.org/licenses/by/4.0/","note":"Modelled point forecast, not observed weather; precipitation/heat proxies are Nordl calculations."})
        added+=partition(directory,"weather-forecast",day,record,w.get("retrievedAt",stamp))
    root=Path(directory)/"archive";manifest=[]
    for path in sorted(root.glob("*/*.json")):
        d=json.loads(path.read_text());manifest.append({"kind":d["kind"],"month":d["month"],"rows":len(d["rows"]),"path":str(path.relative_to(directory)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    root.mkdir(parents=True,exist_ok=True)
    write_json(root/"index-v1.json",{"schema_version":1,"generated":stamp,"notice":"Own versioned collection of cleared open-source observations; revisions retained. Nordic reseller, GB, Yahoo, GIE and unchecked sources excluded.","partitions":manifest})
    print("Open history:",added,"new unique records;",len(manifest),"partitions")
    return added
