"""V90.1 public snapshot projection; never modifies the source payload.
Used by the public collector and allowlisted Pages artifact. Historical Git
objects are outside this forward publication gate. Unknown fields fail closed.
"""
import argparse,json
from pathlib import Path
from urllib.parse import urlsplit
from price_rights import permitted
from shared_energy import validate_shared

PRICE_FIELDS=("date","complete","marketType","intervalSeconds","startsUtc","cents","points","min","max","mean","zone","name","country","unit","priceSource","licenseInfo","sourceUrl","retrievedAt","stale")
WEATHER_FIELDS=("place","tempNow","windNow","tempMin","tempMax","windMean","heatingDegreeHours","hours","forecastStart","forecastEnd","precipCoverageHours","precipMm","coldPrecipMm","positiveDegreeHours","method","sourceUpdatedAt","retrievedAt","stale")
GAS_FIELDS=("code","name","fullPct","changePct","twh","date","stale")
EIA_KEYS={"eia:RBRTE","eia:RWTC"}
SHARED_ZONES=set("NO1 NO2 NO3 NO4 NO5 SE1 SE2 SE3 SE4 DK1 DK2 FI DE-LU FR NL".split())
def fields(row,keys):
    return {k:row[k] for k in keys if k in row}
def approved_url(url,host):
    if not isinstance(url,str):return False
    p=urlsplit(url)
    return p.scheme=="https" and p.netloc==host
def project_snapshot(d):
    prices=[]
    for r in d.get("europe",[]):
        if r.get("marketType")=="day_ahead" and r.get("complete") is True and permitted(r.get("zone"),r.get("licenseInfo")) and approved_url(r.get("sourceUrl"),"api.energy-charts.info") and r.get("unit")=="eurocent/kWh":
            prices.append(fields(r,PRICE_FIELDS))
    gas=d.get("gasStorage") or {}
    # Retain the supported renderer schema, not unapproved values or derivatives.
    return {"generated":d["generated"],"zones":[],"europe":prices,
        "marketIndex":None,"market":{},"grid":{},"fuel":{},"france":{},
        "commodities":[],"news":[],
        "reservoirs":fields(d.get("reservoirs") or {},("year","week","zones","national","stale")),
        "weather":{z:fields(w,WEATHER_FIELDS) for z,w in d.get("weather",{}).items() if z in SHARED_ZONES and isinstance(w,dict) and w.get("sourceUpdatedAt")},
        "gasStorage":{"source":"GIE AGSI","countries":[fields(r,GAS_FIELDS) for r in gas.get("countries",[])] if gas.get("source")=="GIE AGSI" else [],"status":gas.get("status","unavailable") if gas.get("source")=="GIE AGSI" else "unavailable"},
        "publication":{"policy":"v90.1_open_projection","sources":{"reservoirs":"NVE / NLOD","weather":"MET Norway / CC BY 4.0","gasStorage":"GIE AGSI / attribution required"},"unavailable":{"zones":"https://www.nordpoolgroup.com/","marketIndex":"https://bmrs.elexon.co.uk/","market":"https://finance.yahoo.com/","commodities":"https://www.eia.gov/dnav/pet/pet_pri_spt_s1_d.htm","grid":"https://transparency.entsoe.eu/"}}}
def project_economic(d):
    rows=[]
    for r in d.get("series",[]):
        if r.get("key") in EIA_KEYS and r.get("provider")=="eia" and approved_url(r.get("sourceUrl"),"www.eia.gov") and "U.S. Energy Information Administration" in r.get("license",""):
            row=fields(r,("key","provider","label","unit","country","frequency","period","value","sourceUrl","license","observedAt"))
            row["history"]=[fields(x,("date","value")) for x in r.get("history",[])]
            rows.append(row)
    if {r["key"] for r in rows}!=EIA_KEYS or len(rows)!=len(EIA_KEYS):raise ValueError("Missing approved EIA series")
    return {"generated":d["generated"],"notice":"Public-domain EIA petroleum spot observations; dated, not futures or live quotes. Source: U.S. Energy Information Administration.","series":rows}
def project_shared(d):
    d=validate_shared(d)
    series=[]
    for r in d["series"]:
        if r["kind"]=="day_ahead_load_forecast" and r.get("zone") not in SHARED_ZONES:continue
        if r["kind"]=="physical_flow" and (r.get("from") not in SHARED_ZONES or r.get("to") not in SHARED_ZONES):continue
        series.append(r)
    return {**d,"series":series}
def write_projection(root,out):
    if out.resolve()==root.resolve() or out.resolve().is_relative_to(root.resolve()):
        raise ValueError("Use separate staging directory outside source data")
    out.mkdir(parents=True,exist_ok=True)
    for file,project in (("energy.json",project_snapshot),("economic-reference-v1.json",project_economic),("entsoe-open.json",project_shared)):
        d=json.loads((root/file).read_text(encoding="utf-8"))
        (out/file).write_text(json.dumps(project(d),ensure_ascii=False,allow_nan=False,indent=1)+"\n",encoding="utf-8")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--data",type=Path,default=Path(__file__).resolve().parents[1]/"data")
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    write_projection(a.data,a.out)
