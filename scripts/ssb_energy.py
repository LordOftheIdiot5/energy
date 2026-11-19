"""SSB PxWebApi v2 electricity statistics, exact source cells and status codes."""
import argparse, hashlib, itertools, json, math, re, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from hydro_extended import write_json

TABLES={"08307":"Annual electricity balance","14091":"Monthly electricity balance","14092":"Consumption by consumer group and price area","14093":"Generation by technology and price area"}
API="https://data.ssb.no/api/pxwebapi/v2/tables/"
LIC="https://creativecommons.org/licenses/by/4.0/"
ATTR="Statistics Norway (SSB); normalized by Nordl"
def fetch(url):
    with urlopen(Request(url,headers={"Accept":"application/json","User-Agent":"Nordl-Energy/1.0 (energy.nordl.dev)"}),timeout=45) as response:
        return json.load(response)
def codes(category):
    idx=category["index"]
    return sorted(idx,key=idx.get) if isinstance(idx,dict) else list(idx)
def normalize(doc,table):
    ids=doc["id"]; dims=doc["dimension"]; sizes=doc["size"]
    if doc.get("class")!="dataset" or doc.get("version")!="2.0" or len(ids)!=len(sizes) or len(set(ids))!=len(ids) or "Tid" not in ids or "ContentsCode" not in ids:raise ValueError("Unexpected JSON-stat dimensions")
    axes=[codes(dims[k]["category"]) for k in ids]
    if [len(a) for a in axes]!=sizes or math.prod(sizes)>800000:raise ValueError("Unexpected dimension lengths")
    values=doc["value"]; statuses=doc.get("status",{})
    if isinstance(values,list) and len(values)!=math.prod(sizes):raise ValueError("Unexpected value count")
    def at(obj,i):
        return obj.get(str(i)) if isinstance(obj,dict) else obj[i] if isinstance(obj,list) and i<len(obj) else obj if isinstance(obj,str) else None
    rows=[]
    for i,combo in enumerate(itertools.product(*axes)):
        c=dict(zip(ids,combo)); v=at(values,i); status=at(statuses,i)
        if v is not None and (type(v) not in (int,float) or not math.isfinite(v)):raise ValueError("Non-numeric source value")
        period=c["Tid"]
        if not re.fullmatch(r"\d{4}" if table=="08307" else r"\d{4}M(0[1-9]|1[0-2])",period):raise ValueError("Unexpected period")
        measure=c["ContentsCode"]; cat=dims["ContentsCode"]["category"]; u=cat.get("unit",{}).get(measure,{})
        unit=u.get("label") if isinstance(u,dict) else None
        expected="GWh" if table=="08307" else "MWh"
        if unit!=expected:raise ValueError("Unexpected unit: "+str(unit))
        other={k:c[k] for k in ids if k not in ("Tid","ContentsCode")}
        labels={k:dims[k]["category"].get("label",{}).get(c[k],c[k]) for k in other}
        rows.append({"id":json.dumps([measure,other],sort_keys=True,separators=(",",":")),"period":period,"measure":measure,"name":cat.get("label",{}).get(measure,measure),"dimensions":other,"labels":labels,"unit":unit,"value":v,"status":status})
    if not rows or not any(r["value"] is not None for r in rows):raise ValueError("Empty source data")
    return rows
def collect(root,table,get=fetch,stamp=None):
    stamp=stamp or datetime.now(timezone.utc).isoformat()
    meta=get(API+table+"/metadata?lang=en")
    ids=meta["id"]
    if "Tid" not in ids or "ContentsCode" not in ids or len(ids)>6:raise ValueError("Unexpected metadata dimensions")
    url=API+table+"/data?"+urlencode({"lang":"en","outputFormat":"json-stat2",**{"valueCodes["+k+"]":"*" for k in ids}})
    doc=get(url);rows=normalize(doc,table)
    data={"schema_version":1,"provider":"ssb","table":table,"title":TABLES[table],"source":url,"source_page":"https://www.ssb.no/en/statbank1/table/"+table,"license":LIC,"attribution":ATTR,"notice":"Source cells normalized; null and source status retained. Annual and monthly units differ. No estimates.","generated":stamp,"source_updated":doc.get("updated"),"rows":rows}
    root=Path(root);p=root/("ssb-"+table+"-v1.json")
    prior=json.loads(p.read_text()) if p.exists() else None
    if prior and prior["rows"]==rows and prior.get("source_updated")==data["source_updated"]:
        print(table,"unchanged",len(rows));return prior
    if prior:
        encoded=json.dumps(prior,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
        digest=hashlib.sha256(encoded).hexdigest()
        archive=root/"ssb-revisions"/table/(digest+".json")
        if not archive.exists():archive.parent.mkdir(parents=True,exist_ok=True);write_json(archive,prior)
    write_json(p,data)
    print(table,len(rows),"cells;",sum(r["value"] is not None for r in rows),"numeric;",min(r["period"] for r in rows),max(r["period"] for r in rows))
    return data
def public_files(root):
    for table in TABLES:
        p=root/("ssb-"+table+"-v1.json")
        if not p.exists():continue
        d=json.loads(p.read_text())
        if d.get("provider")!="ssb" or d.get("schema_version")!=1 or d.get("table")!=table or d.get("license")!=LIC or d.get("attribution")!=ATTR or not d.get("source","").startswith(API+table+"/data?") or not d.get("rows"):raise ValueError("Unexpected SSB provenance")
        yield p.name
def main():
    a=argparse.ArgumentParser();a.add_argument("--force",action="store_true");a.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]/"data");args=a.parse_args()
    now=datetime.now(timezone.utc)
    if 5<=now.astimezone(ZoneInfo("Europe/Oslo")).hour<9:print("SSB revision window; skipping collection");return
    args.root.mkdir(parents=True,exist_ok=True)
    ok=0
    for table in TABLES:
        try:collect(args.root,table);ok+=1
        except Exception as exc:print("SSB",table,type(exc).__name__,str(exc)[:200])
        time.sleep(2.2)
    if args.force and ok!=len(TABLES):raise SystemExit("Not all SSB endpoints validated")
if __name__=="__main__":main()
