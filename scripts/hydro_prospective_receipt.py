"""Freeze a dated one-week seasonal hydro baseline for prospective evaluation.
Local research only; no weather forecast, public prediction or remote archive.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
from hydro_extended import SOURCE, num
from hydro_validation import model, monday

ZONES = ("NO1", "NO2", "NO3", "NO4", "NO5")
ROOT = Path(__file__).resolve().parents[1]
OSLO = ZoneInfo("Europe/Oslo")

def utc(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp lacks timezone")
    return dt.astimezone(timezone.utc)

def build(raw, now):
    if now.tzinfo is None:
        raise ValueError("issue timestamp lacks timezone")
    now = now.astimezone(timezone.utc)
    source = json.loads(raw)
    if source.get("schema_version") != 1 or source.get("source") != SOURCE:
        raise ValueError("unexpected source")
    groups = {z: [] for z in ZONES}
    seen = set()
    for row in source["rows"]:
        zone = row.get("zone")
        if zone not in groups:
            continue
        day = monday(row)
        key = (zone, day)
        if key in seen or not num(row.get("fill_pct")) or not 0 <= row["fill_pct"] <= 100:
            raise ValueError("duplicate or invalid observation")
        seen.add(key)
        if row.get("snapshot_generated") and utc(row["snapshot_generated"]) > now:
            raise ValueError("future source vintage")
        if (day + timedelta(days=7)).replace(tzinfo=OSLO).astimezone(timezone.utc) > now:
            raise ValueError("source contains unfinished observation week")
        groups[zone].append(row)
    origins = [max(rows, key=monday) for rows in groups.values() if rows]
    if len(origins) != len(ZONES) or len({monday(r) for r in origins}) != 1:
        raise ValueError("missing or inconsistent latest zone periods")
    origin = monday(origins[0])
    target_local = (origin + timedelta(days=7)).replace(tzinfo=OSLO)
    target = target_local.astimezone(timezone.utc)
    cutoff = (target_local + timedelta(days=7)).astimezone(timezone.utc)
    if not target <= now < cutoff:
        raise ValueError("target week already ended or not yet begun")
    rows_out = []
    for zone, last in zip(ZONES, origins):
        if not last.get("snapshot_generated"):
            raise ValueError("latest observation missing retrieval timestamp")
        if utc(last["snapshot_generated"]) < target:
            raise ValueError("latest observation retrieval predates origin completion")
        result = model(groups[zone])
        values = [result.get(k) for k in ("baseline_pct", "low_pct", "high_pct")]
        if not all(num(x) and 0 <= x <= 100 for x in values) or not values[1] <= values[0] <= values[2]:
            raise ValueError("insufficient or invalid seasonal evidence")
        if (result.get("origin_year"), result.get("origin_week")) != (last["year"], last["week"]):
            raise ValueError("model origin mismatch")
        rows_out.append({"zone": zone, "origin_fill_pct": last["fill_pct"],
                         "source_retrieved_at": last["snapshot_generated"],
                         "seasonal_pct": values[0], "low_pct": values[1], "high_pct": values[2],
                         "persistence_pct": last["fill_pct"]})
    year, week, _ = target_local.isocalendar()
    return {"schema_version": 1, "method": "seasonal_change_baseline_v1",
            "scope": "within_target_week_prospective_research",
            "issued_at": now.isoformat(), "origin_week": origin.date().isoformat(),
            "target_iso_year": year, "target_iso_week": week,
            "week_timezone": "Europe/Oslo", "target_week_start_utc": target.isoformat(), "target_week_end_exclusive_utc": cutoff.isoformat(),
            "lead_hours_to_week_end": (cutoff - now).total_seconds()/3600,
            "source": SOURCE, "source_sha256": hashlib.sha256(raw).hexdigest(),
            "model_sha256": hashlib.sha256((Path(__file__).with_name("hydro_validation.py")).read_bytes()).hexdigest(),
            "zones": rows_out, "weather_inputs": False, "operational_forecast_approved": False,
            "notice": "Research baseline issued during target week, before its Norwegian local-time end; not a full-week-ahead weather forecast. Historical revisions and actual NVE publication timing require separate evaluation."}

def freeze(output, receipt):
    output = Path(output).resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("research receipts must stay outside repository")
    output.mkdir(parents=True, exist_ok=True)
    path = output / ("hydro-seasonal-%04d-W%02d.json" % (receipt["target_iso_year"], receipt["target_iso_week"]))
    # Exclusive creation: never replace an earlier issue for this target.
    payload = json.dumps(receipt, indent=2, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8") as f:
        f.write(payload)
    return path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT/"data"/"hydro-v1.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipt = build(args.data.read_bytes(), datetime.now(timezone.utc))
    path = freeze(args.out, receipt)
    print("Research receipt:", path)

if __name__ == "__main__":
    main()
