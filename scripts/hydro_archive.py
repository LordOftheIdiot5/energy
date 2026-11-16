"""Append only validated NVE-derived weekly reservoir observations to the open archive."""
import json
import math
from pathlib import Path

SOURCE = "https://api.nve.no/doc/magasinstatistikk/"
LICENSE = "https://data.norge.no/nlod/"

def number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)

def append_snapshot(path, payload):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("source") != SOURCE:
        raise ValueError("Unexpected hydro archive schema")
    r = payload.get("reservoirs") or {}
    y, w = r.get("year"), r.get("week")
    if not isinstance(y, int) or not 1995 <= y <= 2100 or not isinstance(w, int) or not 1 <= w <= 53:
        return 0
    existing = {(v["year"], v["week"], v["zone"]): v for v in data["rows"]}
    added = 0
    for zone, z in (r.get("zones") or {}).items():
        fill = z.get("fill")
        if zone not in ("NO1", "NO2", "NO3", "NO4", "NO5") or not number(fill) or not 0 <= fill <= 1:
            continue
        key = (y, w, zone)
        if key in existing:
            continue
        normal, twh = z.get("normal"), z.get("twh")
        existing[key] = {"year": y, "week": w, "zone": zone, "fill_pct": round(fill*100, 2),
                         "normal_pct": round(normal*100, 2) if number(normal) and 0 <= normal <= 1 else None,
                         "stored_twh": twh if number(twh) and twh >= 0 else None,
                         "snapshot_generated": payload.get("generated")}
        added += 1
    if added:
        data["rows"] = [existing[k] for k in sorted(existing)]
        tmp = Path(path).with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
        tmp.replace(path)
    return added
