"""Shared public Stockwatch feed: no credentials required or copied."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

URL="https://stocks.nordl.dev/data/entsoe-open.json"

def retain_gas(now, old):
    fresh={r["code"]:r for r in now.get("countries",[]) if r.get("code") and isinstance(r.get("fullPct"),(int,float))}
    for row in old.get("countries",[]):
        if row.get("code") and row["code"] not in fresh:
            fresh[row["code"]]={**row,"stale":True}
    return {"source":"GIE AGSI","countries":list(fresh.values()),"status":"partial_or_stale" if any(r.get("stale") for r in fresh.values()) else "ok" if fresh else "unavailable"}

def retain_news(now, old):
    if now: return now
    return [{**r,"stale":True} for r in old if str(r.get("url","")).startswith("https://")][:30]

def validate_shared(d):
    if d.get("schemaVersion")!=1 or d.get("source")!="ENTSO-E Transparency Platform" or d.get("license")!="CC BY 4.0":
        raise ValueError("Unexpected ENTSO-E schema")
    datetime.fromisoformat(d["generated"].replace("Z","+00:00"))
    for s in d["series"]:
        expected={"day_ahead_load_forecast":"6.1.b","physical_flow":"12.1.g"}.get(s.get("kind"))
        if not expected or s.get("article")!=expected or s.get("unit")!="MW": raise ValueError("Unexpected series")
        for p in s.get("points",[]):
            v=p.get("mw")
            if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v): raise ValueError("Invalid point")
            datetime.fromisoformat(p["startUtc"].replace("Z","+00:00"))
    return d

def refresh_shared(path,get_json):
    d=validate_shared(get_json(URL,timeout=25))
    p=Path(path)
    if not any(s.get("status")=="ok" and s.get("points") for s in d["series"]): raise ValueError("No reported points")
    if p.exists():
        old=json.loads(p.read_text(encoding="utf-8"))
        if old.get("generated","")>=d["generated"]: return
    tmp=p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d,ensure_ascii=False,indent=1,allow_nan=False)+"\n",encoding="utf-8")
    tmp.replace(p)
