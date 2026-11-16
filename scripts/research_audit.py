"""Research-only source probes and dataset inventory. Never writes public data."""
import hashlib
import json
import urllib.request
import zipfile
import io
from pathlib import Path
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

PORTFOLIO = "https://eepublicdownloads.blob.core.windows.net/public-cdn-container/tyndp-documents/TYNDP2026/20260203_TYNDP2026_project_portfolio_final.xlsx"
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

def workbook_structure(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members = z.infolist()
        if sum(m.file_size for m in members) > 100_000_000:
            raise ValueError("Expanded workbook too large")
        sheets = ET.fromstring(z.read("xl/workbook.xml")).findall("s:sheets/s:sheet", NS)
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            shared = ["".join(t.text or "" for t in si.iterfind(".//s:t", NS))
                      for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("s:si", NS)]
        result = []
        for member in sorted(m.filename for m in members if m.filename.startswith("xl/worksheets/sheet") and m.filename.endswith(".xml")):
            root = ET.fromstring(z.read(member))
            rows = root.findall("s:sheetData/s:row", NS)
            preview = []
            for row in rows[:8]:
                cells = []
                for cell in row.findall("s:c", NS):
                    v = cell.findtext("s:v", default="", namespaces=NS)
                    if cell.get("t") == "s" and v:
                        v = shared[int(v)]
                    elif cell.get("t") == "inlineStr":
                        v = "".join(t.text or "" for t in cell.iterfind(".//s:t", NS))
                    if v:
                        cells.append([cell.get("r"), v[:160]])
                preview.append(cells[:40])
            result.append({"xml": member, "nonempty_rows": len(rows), "first_rows": preview})
        return {"sheet_names": [s.get("name") for s in sheets], "worksheets": result,
                "sha256": hashlib.sha256(raw).hexdigest()}

def inventory(directory):
    directory = Path(directory)
    catalog = json.loads((directory / "catalog-v1.json").read_text(encoding="utf-8"))
    output = []
    for item in catalog["datasets"]:
        path = directory / item["path"]
        if path.parent != directory or path.suffix != ".json":
            raise ValueError("Unsafe catalog path")
        entry = {"id": item["id"], "rights_status": item["status"], "available": False,
                 "commercial_redistribution_cleared": False}
        if path.is_file():
            try:
                raw = path.read_bytes()
                d = json.loads(raw)
                if not isinstance(d, dict):
                    raise ValueError("Expected object")
                entry.update(available=True, sha256=hashlib.sha256(raw).hexdigest(),
                             size_bytes=len(raw), generated=d.get("generated"),
                             schema_version=d.get("schema_version", d.get("schemaVersion")),
                             row_count=len(d["rows"]) if isinstance(d.get("rows"), list) else None)
            except (OSError, ValueError):
                entry["error"] = "invalid_json"
        output.append(entry)
    return {"generated": datetime.now(timezone.utc).isoformat(), "datasets": output,
            "notice": "Technical availability only; not commercial rights or source freshness certification."}

def probe_portfolio():
    req = urllib.request.Request(PORTFOLIO, headers={"User-Agent": "Nordl Energy (https://energy.nordl.dev/)"})
    with urllib.request.urlopen(req, timeout=45) as response:
        raw = response.read(20_000_001)
    if len(raw) > 20_000_000:
        raise ValueError("Workbook too large")
    return workbook_structure(raw)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=["inventory", "portfolio", "plants"])
    args = parser.parse_args()
    if args.task == "inventory":
        result = inventory(Path(__file__).resolve().parents[1] / "data")
    elif args.task == "portfolio":
        result = probe_portfolio()
    else:
        import tempfile
        from asset_reference import europe
        with tempfile.TemporaryDirectory() as directory:
            europe(Path(directory))
            d = json.loads((Path(directory) / "europe-plants-v1.json").read_text())
            rows = d["rows"]
            result = {"count": len(rows), "countries": sorted({r["country"] for r in rows}),
                      "release_year": d["release_year"], "source": d["source"]}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
