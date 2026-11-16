"""Shared economic reference data and forward point-weather archive."""
import json,math
from datetime import datetime,date
from pathlib import Path
from hydro_extended import write_json
URL="https://stocks.nordl.dev/data/economic-feeds.json"
KEYS={"eia:RBRTE","eia:RWTC","fred:DFF","fred:DGS10","fred:DGS2","fred:UNRATE"}
def refresh(directory,get_json):
    p=Path(directory)/"economic-reference-v1.json"
    d=get_json(URL,timeout=40)
    stamp=datetime.fromisoformat(d["generated"].replace("Z","+00:00"))
    if p.exists():
        prior=datetime.fromisoformat(json.loads(p.read_text(encoding="utf-8"))["generated"].replace("Z","+00:00"))
        if prior>=stamp: return
    series=[r for r in d["series"] if r.get("key") in KEYS]
    if {r["key"] for r in series}!=KEYS or len(series)!=6: raise ValueError("Missing series")
    for r in series:
        if not r.get("license") or not str(r.get("sourceUrl","")).startswith("https://") or not math.isfinite(r["value"]): raise ValueError("Invalid provenance or value")
        for x in r["history"]:
            date.fromisoformat(x["date"])
            if not math.isfinite(x["value"]): raise ValueError("Invalid observation")
    write_json(p,{"generated":d["generated"],"notice":"Dated observations via Stockwatch; not live quotes. Per-series rights apply.","series":series})
def archive_weather(directory,payload):
    p=Path(directory)/"weather-vintages-v1.json"
    old=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"schema_version":1,"source":"MET Norway; retrieved point forecasts, not original issue-time archive","rows":[]}
    day=payload["generated"][:10]
    if any(r["day"]==day for r in old["rows"]): return
    points={z:{k:v for k,v in row.items() if k in ("place","forecastStart","forecastEnd","precipCoverageHours","precipMm","coldPrecipMm","positiveDegreeHours","tempNow","windNow")} for z,row in payload["weather"].items() if isinstance(row,dict) and row.get("forecastStart")}
    if points:
        old["rows"].append({"day":day,"retrieved_at":payload["generated"],"points":points})
        write_json(p,old)
