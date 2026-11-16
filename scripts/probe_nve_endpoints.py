"""Compare documented NVE point and area endpoints; never substitutes point data for catchments."""
from catchment_weather import request_json
from urllib.error import HTTPError, URLError
import json

BASE="https://gts.nve.no/api"
DAY1,DAY2="2018-01-01","2018-01-02"
def probe():
    reports=[]
    polygon={"rings":[[[270915,6664551],[270872,6664362],[268633,6664858],[268682,6665047],[270405,6664796],[270518,6664739],[270915,6664551]]],"spatialReference":{"wkid":25833}}
    for label,url,body in [
        ("documented_point",BASE+f"/GridTimeSeries/953709/7938592/{DAY1}/{DAY2}/rr.json",None),
        ("documented_cell",BASE+"/AreaTimeSeries/ByCellIndexCsv",{"Theme":"rr","StartDate":DAY1,"EndDate":DAY2,"Format":"json","CellIndexCsv":"1595670"}),
        ("documented_polygon",BASE+"/AreaTimeSeries/ByGeoJson",{"Theme":"rr","StartDate":DAY1,"EndDate":DAY2,"Format":"json","Rings":json.dumps(polygon)})]:
        try:
            d=request_json(url,body)
            if not isinstance(d,dict) or d.get("Theme")!="rr":
                raise ValueError("Unexpected data schema")
            reports.append({"endpoint":label,"status":"ok","keys":sorted(d),"unit":d.get("Unit"),"start":d.get("StartDate"),"end":d.get("EndDate")})
        except HTTPError as e:
            reports.append({"endpoint":label,"status":"http_error","code":e.code})
        except (URLError,TimeoutError,ValueError) as e:
            reports.append({"endpoint":label,"status":"error","type":type(e).__name__})
    return reports
if __name__=="__main__":
    print(json.dumps(probe(),indent=2))
