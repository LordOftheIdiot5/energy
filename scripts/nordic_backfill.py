"""Bounded historical backfill, independent of recent-data collection.
State records completed requests (not claims of complete historical coverage).
Never change existing revisions or fetched observations on failed requests.
"""
import json,os,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from nordic_observations import NVE,FG,FG_IDS,PARAMS,hydro_rows,fg_rows,select_samples,store,request,now,read
from hydro_extended import write_json

def jobs(root,anchor):
    day=datetime.fromisoformat(anchor).replace(tzinfo=timezone.utc)
    hydro_start=(day-timedelta(days=365)).date().isoformat()
    hydro_end=(day-timedelta(days=29)).date().isoformat()
    for s in select_samples(read(root/"hydapi-stations-v1.json",{"rows":[]})["rows"]):
        for param in sorted({x["parameter"] for x in s["series"] if x.get("serieTo") is None}&PARAMS.keys()):
            sid=s["stationId"]
            yield "hydapi",f"{sid}:{param}:{hydro_start}:{hydro_end}",NVE+"Observations?"+urlencode({"StationId":sid,"Parameter":param,"ResolutionTime":"1440","ReferenceTime":hydro_start+"/"+hydro_end}),sid
    # Seven complete UTC days immediately preceding the current day.
    for offset in range(1,8):
        start=day-timedelta(days=offset);end=start+timedelta(days=1)
        for dataset in FG_IDS:
            yield "fingrid",f"{dataset}:{start.date()}",FG+str(dataset)+"/data?"+urlencode({"startTime":start.isoformat(),"endTime":end.isoformat(),"format":"json","pageSize":1000}),dataset

def backfill(root,keys,get=request,pause=time.sleep,stamp=None,limits=None):
    root=Path(root);stamp=stamp or now();limits=limits or {"hydapi":12,"fingrid":12}
    directory=root/"observations";directory.mkdir(parents=True,exist_ok=True)
    path=directory/"backfill-state-v1.json"
    state=read(path,{"schema_version":1,"anchor":datetime.fromisoformat(stamp).date().isoformat(),"requests":{}})
    plan=list(jobs(root,state["anchor"]))
    rows={"hydapi":[],"fingrid":[]};done=dict(state["requests"]);attempts={"hydapi":0,"fingrid":0};blocked=set()
    for provider,ident,url,selector in plan:
        task=provider+":"+ident
        if task in done or provider in blocked or not keys.get(provider) or attempts[provider]>=limits.get(provider,0):continue
        attempts[provider]+=1
        try:
            data=get(url,keys[provider])
            points=hydro_rows(data,{selector}) if provider=="hydapi" else fg_rows(data,selector)
            if not points:
                print("Backfill empty or unsupported:",task)
                # A successful empty response is explicitly marked; not fabricated.
                done[task]={"status":"empty","records":0,"retrievedAt":stamp}
            else:
                rows[provider].extend(points)
                done[task]={"status":"received","records":len(points),"retrievedAt":stamp}
        except HTTPError as e:
            print("Backfill HTTP",provider,e.code)
            if e.code in (401,403,429):blocked.add(provider)
        except (OSError,ValueError,TypeError,KeyError) as e:
            print("Backfill",provider,type(e).__name__)
        finally:pause(2.2 if provider=="fingrid" else 1.0)
    # Save archive first. If it fails the cursor never advances.
    for provider,values in rows.items():
        if values:store(root,provider,values,stamp,archive_only=True)
    state["requests"]=done;state["updatedAt"]=stamp
    state["planned"]={p:sum(q==p for q,*_ in plan) for p in keys}
    write_json(path,state)
    for p in keys:print("Historical",p,"new records",len(rows[p]),"completed requests",sum(k.startswith(p+":") for k in done),"/",state["planned"][p])
    return state

if __name__=="__main__":
    backfill(Path(__file__).resolve().parents[1]/"data",{"hydapi":os.environ.get("NVE_HYDAPI_KEY"),"fingrid":os.environ.get("FINGRID_API_KEY")})
