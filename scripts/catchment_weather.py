"""V42 pilot: retrieve daily NVE GTS cell series for one small NVE catchment.

Explicit opt-in CLI, no hourly collector integration until live schema validated.
Equal-grid-cell mean is not exact polygon-area weighting or inflow.
"""
import argparse
import json
import math
import statistics
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

from hydro_extended import write_json

GIS = "https://gis3.nve.no/map/rest/services/Mapservices/VassdragsreguleringVannkraft/MapServer/8/query"
GTS = "https://gts.nve.no/api/AreaTimeSeries/ByGeoJson"
SOURCE = "https://api.nve.no/doc/gridtimeseries-data-gts/"
LICENSE = "https://data.norge.no/nlod/"
THEMES = {"rr": {"mm"}, "swe": {"mm"}, "tm": {"c", "°c", "celcius", "celsius", "degc"}}

def request_json(url, body=None):
    req = urllib.request.Request(
        url, data=None if body is None else json.dumps(body).encode("utf-8"),
        headers={"User-Agent": "Nordl Energy (https://energy.nordl.dev/)",
                 "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read(8_000_001)
    if len(raw) > 8_000_000:
        raise ValueError("Oversized response")
    return json.loads(raw)

def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)

def fetch_catchment(identifier, get=request_json):
    if not isinstance(identifier, int) or not 0 < identifier <= 2_147_483_647:
        raise ValueError("Invalid catchment object ID")
    query = urlencode({"where": f"OBJECTID={identifier}", "outFields":
        "OBJECTID,delfeltNr,delfeltNavn,delfeltAreal_km2",
        "returnGeometry": "true", "outSR": "25833", "f": "json"})
    d = get(GIS + "?" + query)
    features = d.get("features", [])
    if len(features) != 1:
        raise ValueError("Expected exactly one catchment")
    f = features[0]
    attrs = f["attributes"]
    area = attrs.get("delfeltAreal_km2")
    if attrs.get("OBJECTID") != identifier or not finite(area) or not 0 < area <= 20:
        raise ValueError("Pilot limited to documented catchments of at most 20 km²")
    sr = d.get("spatialReference", {})
    if 25833 not in (sr.get("wkid"), sr.get("latestWkid")):
        raise ValueError("Unexpected coordinate reference system")
    rings = f["geometry"]["rings"]
    if not rings or not all(len(r) >= 4 and r[0] == r[-1] and
        all(len(p) == 2 and all(finite(v) for v in p) for p in r) for r in rings):
        raise ValueError("Invalid polygon")
    return attrs, {"rings": rings, "spatialReference": {"wkid": 25833}}

def parse_source_date(value):
    # NVE documents day-first date strings, including the reference time.
    return datetime.strptime(value, "%d.%m.%Y %H:%M:%S")

def normalize(theme, response, start, end):
    if theme not in THEMES or response.get("Theme") != theme:
        raise ValueError("Unexpected theme")
    if str(response.get("Unit", "")).strip().lower() not in THEMES[theme]:
        raise ValueError("Unexpected unit")
    if response.get("TimeResolution") != 1440:
        raise ValueError("Expected daily resolution")
    first = parse_source_date(response["StartDate"])
    last = parse_source_date(response["EndDate"])
    n = (end - start).days + 1
    if first.date() != start or last != first + timedelta(days=n-1):
        raise ValueError("Unexpected time coverage")
    missing = response["NoDataValue"]
    if not finite(missing):
        raise ValueError("Unexpected missing-value marker")
    cells = response["CellTimeSeries"]
    if not isinstance(cells, list) or not 1 <= len(cells) <= 100:
        raise ValueError("Unexpected cell count")
    ids = set()
    columns = [[] for _ in range(n)]
    for cell in cells:
        ident = cell["CellIndex"]
        if not isinstance(ident, int) or isinstance(ident, bool) or ident in ids:
            raise ValueError("Invalid or duplicate grid ID")
        ids.add(ident)
        values = cell["Data"]
        if not isinstance(values, list) or len(values) != n:
            raise ValueError("Incomplete cell series")
        for i, v in enumerate(values):
            if v is None or v == missing:
                continue
            if not finite(v) or (theme in ("rr", "swe") and v < 0):
                raise ValueError("Invalid observation")
            columns[i].append(v)
    return {"theme": theme, "source_unit": response["Unit"],
        "source_start": response["StartDate"], "source_end": response["EndDate"],
        "cell_ids": sorted(ids), "cell_count": len(cells),
        "days": [{"date": (start + timedelta(days=i)).isoformat(),
                  "valid_cells": len(v),
                  "mean": round(statistics.mean(v), 3) if len(v) == len(cells) else None}
                 for i, v in enumerate(columns)]}

def collect(identifier, start, end, get=request_json):
    if not 0 <= (end-start).days <= 30 or end >= datetime.now(timezone.utc).date() - timedelta(days=2):
        raise ValueError("Use 1–31 historical days ending at least three days ago")
    attrs, polygon = fetch_catchment(identifier, get)
    series = {}
    for theme in THEMES:
        body = {"Theme": theme, "StartDate": start.isoformat(),
                "EndDate": end.isoformat(), "Format": "json",
                "Rings": json.dumps(polygon)}
        series[theme] = normalize(theme, get(GTS, body), start, end)
    if len({tuple(s["cell_ids"]) for s in series.values()}) != 1:
        raise ValueError("Themes use different cell sets")
    if not all(any(d["mean"] is not None for d in s["days"]) for s in series.values()):
        raise ValueError("No complete daily coverage for at least one theme")
    return {"schema_version": 1, "generated": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE, "source_endpoints": [GIS, GTS], "license": LICENSE,
        "attribution": "NVE; Nordl aggregation",
        "catchment": attrs, "method": "Unweighted mean of returned grid cells; incomplete days null. Historical retrospective gridded values, possibly revised; not forecast vintages or measured runoff.",
        "series": series}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catchment-id", required=True, type=int, help="NVE layer 8 OBJECTID")
    p.add_argument("--start", required=True, type=date.fromisoformat)
    p.add_argument("--end", required=True, type=date.fromisoformat)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    result = collect(args.catchment_id, args.start, args.end)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print("Wrote", args.output)

if __name__ == "__main__":
    main()
