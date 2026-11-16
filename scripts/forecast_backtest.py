"""Research-only rolling origin linear forecast benchmark on explicit as-of samples.

Input records carry origin/target/label_available timestamps (offset-aware ISO),
feature vector, target observation and externally specified baseline prediction.
Feature availability must be established by the caller. Does not fetch or fit
production data. Fits only outcomes published before the prediction origin.
"""
import math
from datetime import datetime

def number(v):
    return type(v) in (int,float) and math.isfinite(v)

def stamp(v):
    d=datetime.fromisoformat(v)
    if d.tzinfo is None: raise ValueError("Timezone required")
    return d

def validate(rows):
    out=[]
    seen=set()
    for r in rows:
        origin,target,known,feature_at=map(stamp,[r["origin"],r["target_at"],r["label_available_at"],r["features_available_at"]])
        if not feature_at<=origin<target<=known or origin in seen:
            raise ValueError("Timestamp leakage, duplicate or invalid horizon")
        x=r["features"]
        if not isinstance(x,list) or not x or not all(number(v) for v in [*x,r["actual"],r["baseline"]]):
            raise ValueError("Invalid numeric data")
        seen.add(origin);out.append((origin,target,known,x,r["actual"],r["baseline"]))
    if out and (len({len(r[3]) for r in out})!=1 or len({r[1]-r[0] for r in out})!=1):
        raise ValueError("Mixed features or forecast horizons")
    return sorted(out)

def fit(rows,features,ridge=1.0):
    n=len(rows);p=len(features)
    if not 1<=p<=20: raise ValueError("Feature count out of bounds")
    means=[sum(r[3][j] for r in rows)/n for j in range(p)]
    scales=[math.sqrt(sum((r[3][j]-means[j])**2 for r in rows)/n) or 1 for j in range(p)]
    ys=sum(r[4] for r in rows)/n
    xx=[[1]+[(v-m)/s for v,m,s in zip(r[3],means,scales)] for r in rows]
    size=p+1
    a=[[sum(x[i]*x[j] for x in xx)+(ridge if i==j and i else 0) for j in range(size)]+[sum(x[i]*(r[4]-ys) for x,r in zip(xx,rows))] for i in range(size)]
    for i in range(size):
        k=max(range(i,size),key=lambda j:abs(a[j][i]));a[i],a[k]=a[k],a[i]
        pivot=a[i][i]
        if abs(pivot)<1e-12: raise ValueError("Singular fit")
        a[i]=[v/pivot for v in a[i]]
        for j in range(size):
            if j!=i:
                f=a[j][i];a[j]=[v-f*w for v,w in zip(a[j],a[i])]
    x=[1]+[(v-m)/s for v,m,s in zip(features,means,scales)]
    return ys+sum(v*a[i][-1] for i,v in enumerate(x))

def evaluate(samples,min_train=52,min_test=26):
    rows=validate(samples);scores=[]
    if min_train<20 or min_test<10:raise ValueError("Insufficient minimum sample threshold")
    for r in rows:
        train=[t for t in rows if t[0]<r[0] and t[2]<=r[0]]
        if len(train)<min_train:continue
        predicted=fit(train,r[3])
        scores.append((abs(predicted-r[4]),abs(r[5]-r[4])))
    if len(scores)<min_test:
        return {"status":"insufficient_data","evaluated":len(scores),"required":min_test}
    return {"status":"research_evaluated","evaluated":len(scores),"model_mae":sum(s[0] for s in scores)/len(scores),"baseline_mae":sum(s[1] for s in scores)/len(scores),"notice":"Research comparison only. Feature provenance and revised labels require separate validation."}
