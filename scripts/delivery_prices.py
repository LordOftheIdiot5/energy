"""Delivery-day validation; preserve UTC hours and explicit local labels."""
import math,statistics
from datetime import date,datetime,time,timedelta,timezone
from zoneinfo import ZoneInfo
UTC=timezone.utc
LOCAL=ZoneInfo("Europe/Oslo")
def bounds(day):
    return (datetime.combine(day,time.min,LOCAL).astimezone(UTC),datetime.combine(day+timedelta(days=1),time.min,LOCAL).astimezone(UTC))
def number(v):
    return type(v) in (int,float) and math.isfinite(v)
def instant(s):
    d=datetime.fromisoformat(str(s).replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("Timezone missing")
    return d.astimezone(UTC)
def nordic_day(slots,field,day):
    if not isinstance(slots,list) or not slots:raise ValueError("No intervals")
    start,end=bounds(day);points=[]
    for row in slots:
        a,b=instant(row["time_start"]),instant(row["time_end"])
        local,eur=row.get(field),row.get("EUR_per_kWh")
        if not number(local) or not number(eur):raise ValueError("Missing or nonfinite price")
        if (b-a).total_seconds() not in (900,3600):raise ValueError("Unexpected interval")
        points.append((a,b,local,eur))
    points.sort();cursor=start;groups={}
    for a,b,l,e in points:
        if a!=cursor or b>end:raise ValueError("Gap, overlap or date mismatch")
        cursor=b
        hour=a.replace(minute=0,second=0,microsecond=0)
        if b>hour+timedelta(hours=1):raise ValueError("Interval crosses hour")
        groups.setdefault(hour,[]).append((l,e,(b-a).total_seconds()))
    if cursor!=end or any(sum(x[2] for x in g)!=3600 for g in groups.values()):raise ValueError("Incomplete delivery day")
    local=[round(sum(l*s for l,e,s in v)/3600,4) for v in groups.values()]
    eur=[round(sum(e*s for l,e,s in v)/3600,5) for v in groups.values()]
    hours=[a.astimezone(LOCAL).hour for a in groups]
    labels=[a.astimezone(LOCAL).strftime("%H:%M")+(a.astimezone(LOCAL).strftime(" %Z") if hours.count(a.astimezone(LOCAL).hour)>1 else "") for a in groups]
    rates=[x["EXR"] for x in slots if number(x.get("EXR")) and x["EXR"]>0]
    return {"date":day.isoformat(),"resolution":len(points),"hours":hours,"hourLabels":labels,"hourStartsUtc":[a.isoformat() for a in groups],"local":local,"eur":eur,"rate":round(statistics.mean(rates),4) if rates else None,"min":min(local),"max":max(local),"mean":round(statistics.mean(local),4),"complete":True}
def european_day(d,day):
    start,end=bounds(day);a=int(start.timestamp());b=int(end.timestamp())
    ts,ps=d.get("unix_seconds"),d.get("price")
    if not isinstance(ts,list) or not isinstance(ps,list) or len(ts)!=len(ps):raise ValueError("Invalid price arrays")
    selected={}
    for t,p in zip(ts,ps):
        if type(t)!=int:raise ValueError("Invalid timestamp")
        if a<=t<b:
            if t in selected or not number(p):raise ValueError("Missing/duplicate price")
            selected[t]=p
    stamps=sorted(selected)
    if not stamps or stamps[0]!=a:raise ValueError("Missing first interval")
    step=(b-a)//len(stamps)
    if step not in (900,3600) or stamps!=list(range(a,b,step)):raise ValueError("Incomplete delivery day")
    cents=[round(selected[t]/10,3) for t in stamps]
    return {"date":day.isoformat(),"complete":True,"marketType":"day_ahead","intervalSeconds":step,"startsUtc":[datetime.fromtimestamp(t,UTC).isoformat() for t in stamps],"cents":cents,"points":len(cents),"min":min(cents),"max":max(cents),"mean":round(statistics.mean(cents),3)}
