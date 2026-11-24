"""Decide whether to collect, republish, or skip a scheduled fallback.
Never advance a generated timestamp or change the underlying observations.
"""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
MAX_AGE_MINUTES=70
PUBLIC="https://energy.nordl.dev/data/energy.json"
def stamp(doc):
    try:
        t=datetime.fromisoformat(doc["generated"].replace("Z","+00:00"))
        return t if t.tzinfo is not None else None
    except (ValueError,TypeError,KeyError,AttributeError):return None
def decide(local,public,now):
    t,p=stamp(local),stamp(public)
    if t is None or t>now or (now-t).total_seconds()>=MAX_AGE_MINUTES*60:
        return "collect"
    if p is None or p>now or p<t:return "deploy"
    return "skip"
def public_snapshot():
    try:
        with urlopen(Request(PUBLIC,headers={"Cache-Control":"no-cache","User-Agent":"Nordl freshness guard"}),timeout=12) as r:
            raw=r.read(10_000_001)
        if len(raw)>10_000_000:return {}
        return json.loads(raw)
    except Exception as e:
        print("Public snapshot check unavailable:",type(e).__name__)
        return {}
def main():
    p=argparse.ArgumentParser();p.add_argument("--event",required=True);p.add_argument("--snapshot",type=Path,default=Path("data/energy.json"));p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    try:local=json.loads(a.snapshot.read_text())
    except (OSError,ValueError):local={}
    result=decide(local,public_snapshot(),datetime.now(timezone.utc)) if a.event=="schedule" else "collect"
    print("Freshness guard:",result,"repository generated:",local.get("generated"))
    with a.output.open("a") as f:f.write(f"mode={result}\n")
if __name__=="__main__":main()
