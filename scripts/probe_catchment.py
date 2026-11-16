"""Run one small, bounded live NVE catchment probe; no public output."""
from datetime import date
from urllib.parse import urlencode
from catchment_weather import GIS, request_json, collect
import json

if __name__ == "__main__":
    query = urlencode({"where":"delfeltAreal_km2 > 2 AND delfeltAreal_km2 <= 10",
        "outFields":"OBJECTID,delfeltAreal_km2","returnGeometry":"false",
        "orderByFields":"OBJECTID ASC","resultRecordCount":1,"f":"json"})
    rows = request_json(GIS+"?"+query)["features"]
    if len(rows)!=1:
        raise ValueError("Expected one small catchment")
    ident = rows[0]["attributes"]["OBJECTID"]
    d = collect(ident, date(2025,1,1), date(2025,1,7))
    print(json.dumps({"catchment":d["catchment"],"source":d["source"],
        "series":{k:{"cell_count":v["cell_count"],"complete_days":sum(x["mean"] is not None for x in v["days"]),"unit":v["source_unit"]} for k,v in d["series"].items()}},indent=2))
