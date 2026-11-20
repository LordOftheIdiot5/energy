"""Guarded UK DESNZ REPD normalized project projection (no raw CSV republication).

The official quarterly file is released under UK OGL v3.0. Do not treat
planning, construction or operation statuses as independently verified.
EPSG:27700 -> EPSG:4326 conversion uses pyproj in the CLI, never a guessed
postcode or municipality centroid. No current electricity output is inferred.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

SOURCE_URL = "https://assets.publishing.service.gov.uk/media/6af42ff0a4004bdbe54e54a5/REPD_Publication_Q3_2026.csv"
SOURCE_PAGE = "https://www.gov.uk/government/publications/renewable-energy-planning-database-quarterly-extract"
LICENSE = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
RELEASE = "2026-10"
PUBLISHED = "2026-11-13"
MAX_BYTES = 15_000_000
REQUIRED = (
    "Ref ID", "Site Name", "Technology Type", "Country",
    "Development Status", "Development Status (short)",
    "Installed Capacity (MWelec)", "X-coordinate", "Y-coordinate",
)
PLACES = {"England", "Scotland", "Wales"}

def clean(v):
    s = str(v or "").replace("\u00a0", " ").strip()
    return None if not s or s.lower() in {"not set", "unknown", "n/a"} else s

def number(v):
    try:
        n = float(str(v).replace(",", "").strip())
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None

def gb_date(v):
    value = clean(v)
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None

def project(data: bytes, transform, minimum: int = 5000):
    if not data or len(data) > MAX_BYTES:
        raise ValueError("REPD source size out of bounds")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    columns = set(reader.fieldnames or ())
    if not set(REQUIRED).issubset(columns):
        raise ValueError("Unexpected REPD column schema")
    seen, rows = set(), []
    counts = {"source_records": 0, "missing_location": 0, "invalid_location": 0,
              "outside_great_britain": 0, "missing_identity": 0}
    for r in reader:
        counts["source_records"] += 1
        ident = clean(r.get("Ref ID"))
        name = clean(r.get("Site Name"))
        if not ident or not ident.isdigit() or not name:
            counts["missing_identity"] += 1
            continue
        if ident in seen:
            raise ValueError("Duplicate REPD Ref ID")
        seen.add(ident)
        country = clean(r.get("Country"))
        if country not in PLACES:
            counts["outside_great_britain"] += 1
            continue
        x, y = number(r.get("X-coordinate")), number(r.get("Y-coordinate"))
        if x is None or y is None:
            counts["missing_location"] += 1
            continue
        if not (0 <= x <= 800_000 and 0 <= y <= 1_300_000):
            counts["invalid_location"] += 1
            continue
        try:
            lon, lat = transform(x, y)
        except (TypeError, ValueError):
            counts["invalid_location"] += 1
            continue
        if not (math.isfinite(lon) and math.isfinite(lat) and -13 <= lon <= 6 and 48 <= lat <= 63):
            counts["invalid_location"] += 1
            continue
        mw = number(r.get("Installed Capacity (MWelec)"))
        if mw is not None and (mw < 0 or mw > 20_000):
            raise ValueError("Invalid reported project MW")
        row = {
            "id": "uk-repd-" + ident,
            "source_record": ident,
            "name": name,
            "country": country,
            "region": clean(r.get("Region")),
            "county": clean(r.get("County")),
            "technology": clean(r.get("Technology Type")) or "Not specified",
            "status": clean(r.get("Development Status")) or "Not specified",
            "status_short": clean(r.get("Development Status (short)")),
            "reported_mw": mw,
            "geometry": [round(lon, 6), round(lat, 6)],
            "updated": gb_date(r.get("Record Last Updated (dd/mm/yyyy)")),
        }
        rows.append(row)
    if len(rows) < minimum:
        raise ValueError(f"Insufficient valid UK REPD mapped records: {len(rows)}")
    if counts["source_records"] and len(rows) / counts["source_records"] < .50:
        raise ValueError("Unsafe loss of more than half the source rows")
    rows.sort(key=lambda r: int(r["source_record"]))
    return {
        "schema_version": 1, "release": RELEASE, "published": PUBLISHED,
        "source": SOURCE_PAGE, "source_file": SOURCE_URL, "license": LICENSE,
        "attribution": "Contains public sector information licensed under the Open Government Licence v3.0 (DESNZ REPD).",
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "coordinate_system": "WGS84 reprojected from British National Grid EPSG:27700",
        "caveat": "Planning-register statuses and reported capacities are not independent verification of construction, operation or actual generation.",
        "counts": {**counts, "mapped_records": len(rows)},
        "rows": rows,
    }

def fetch_source(url=SOURCE_URL):
    # Official binary asset only; reject non-government redirects.
    if url != SOURCE_URL:
        raise ValueError("Unapproved source URL")
    req = urllib.request.Request(url, headers={"User-Agent": "Nordl-Energy-Research/1.0"})
    with urllib.request.urlopen(req, timeout=50) as response:
        if urlsplit(response.url).hostname != "assets.publishing.service.gov.uk":
            raise ValueError("Unapproved source redirect")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("REPD source too large")
    return data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-csv", help="Pre-downloaded official quarterly CSV; omit to fetch")
    ap.add_argument("--out", required=True)
    ap.add_argument("--minimum", type=int, default=5000)
    args = ap.parse_args()
    if args.minimum < 1:
        raise ValueError("Minimum source records must be positive")
    raw = Path(args.source_csv).read_bytes() if args.source_csv else fetch_source()
    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
    doc = project(raw, transformer.transform, args.minimum)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":"))+"\n", encoding="utf-8")
    print("UK REPD source:", doc["counts"]["source_records"], "mapped:", len(doc["rows"]),
          "withheld:", doc["counts"]["source_records"]-len(doc["rows"]),
          "sha256:", doc["source_sha256"])

if __name__ == "__main__":
    main()
