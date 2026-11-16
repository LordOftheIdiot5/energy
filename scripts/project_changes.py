"""Compare two dated, complete source snapshots by stable identifiers."""
from datetime import datetime

def index(rows):
    result = {}
    for row in rows:
        key = row.get("id")
        if not isinstance(key, str) or not key.strip() or key in result:
            raise ValueError("Missing or duplicate stable project ID")
        result[key] = row
    if not result:
        raise ValueError("Empty snapshot")
    return result

def compare(old, new, fields):
    if old.get("source") != new.get("source") or not old.get("source"):
        raise ValueError("Source mismatch")
    if old.get("complete") is not True or new.get("complete") is not True:
        raise ValueError("Completeness not established")
    before, after = [datetime.fromisoformat(s["observed_at"]) for s in (old,new)]
    if before.tzinfo is None or after.tzinfo is None or before >= after:
        raise ValueError("Snapshots must be ordered and timezone-aware")
    a,b = index(old["rows"]),index(new["rows"])
    events = []
    for key in sorted(a.keys() | b.keys()):
        if key not in a:
            events.append({"id":key,"event":"first_seen"})
        elif key not in b:
            events.append({"id":key,"event":"not_in_new_snapshot"})
        else:
            diff = {k:{"before":a[key].get(k),"after":b[key].get(k)}
                    for k in fields if k in a[key] and k in b[key] and a[key][k] != b[key][k]}
            if diff:
                events.append({"id":key,"event":"reported_fields_changed","fields":diff})
    return {"source":new["source"],"observed_at":new["observed_at"],"events":events,
            "notice":"Observed source changes, not verified commissioning or cancellation."}
