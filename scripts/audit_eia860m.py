"""Audit official monthly EIA-860M XLSX sheets without publishing unverified records.

Uses the ZIP/XML container directly to expose schema and headings with low
dependency overhead; this is a schema-inspection gate, not a data importer.
"""
import argparse
import hashlib
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE = "https://www.eia.gov/electricity/data/eia860m/xls/september_generator2026.xlsx"
SOURCE_PAGE = "https://www.eia.gov/electricity/data/eia860m/"
LICENSE = "https://www.eia.gov/about/copyrights_reuse.php"
MAX_BYTES = 65_000_000
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

def shared_strings(z):
    name="xl/sharedStrings.xml"
    if name not in z.namelist():
        return []
    values=[]
    with z.open(name) as f:
        for event, el in ET.iterparse(f,events=("end",)):
            if el.tag==S+"si":
                values.append("".join((t.text or "") for t in el.iter(S+"t")))
                el.clear()
    return values

def sheet_titles(z):
    root=ET.fromstring(z.read("xl/workbook.xml"))
    rels=ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    relation={r.attrib.get("Id"):r.attrib.get("Target") for r in rels}
    sheets=[]
    for s in root.findall(".//"+S+"sheet"):
        target=relation.get(s.attrib.get(R+"id"))
        if not target:
            raise ValueError("Missing EIA worksheet relation")
        path=target.lstrip("/")
        if not path.startswith("xl/"):
            path="xl/"+path
        path=path.replace("xl/../","")
        if not path.startswith("xl/worksheets/") or path not in z.namelist():
            raise ValueError("Unsafe EIA sheet path")
        sheets.append((s.attrib["name"],path))
    if not sheets or len(sheets)>15:
        raise ValueError("Unexpected EIA worksheet inventory")
    return sheets

def peek(z,name,strings,limit=12):
    rows=[]
    with z.open(name) as f:
        for event,el in ET.iterparse(f,events=("end",)):
            if el.tag != S+"row":
                continue
            row=[]
            for cell in el.findall(S+"c"):
                coord=cell.attrib.get("r","")
                col=re.match(r"([A-Z]+)",coord)
                raw=cell.find(S+"v")
                txt=cell.find(S+"is")
                if cell.attrib.get("t")=="s" and raw is not None and raw.text is not None:
                    idx=int(raw.text)
                    v=strings[idx] if 0<=idx<len(strings) else ""
                elif cell.attrib.get("t")=="inlineStr" and txt is not None:
                    v="".join((t.text or "") for t in txt.iter(S+"t"))
                else:
                    v=raw.text if raw is not None else ""
                if v not in ("",None):
                    row.append({"column":col.group(1) if col else "?","value":str(v)[:120]})
            if row:
                rows.append({"row":int(el.attrib.get("r",len(rows)+1)),"cells":row[:45]})
            el.clear()
            if len(rows)>=limit:
                break
    return rows

def audit(path):
    path=Path(path)
    size=path.stat().st_size
    if size<10000 or size>MAX_BYTES:
        raise ValueError("EIA workbook source size outside safe range")
    raw=path.read_bytes()
    if not zipfile.is_zipfile(path):
        raise ValueError("EIA source is not an XLSX ZIP container")
    with zipfile.ZipFile(path) as z:
        for item in z.infolist():
            if item.filename.startswith("/") or ".." in Path(item.filename).parts or item.file_size>MAX_BYTES*10:
                raise ValueError("Unsafe EIA ZIP member")
        if any("vbaProject.bin" in n or "externalLinks/" in n for n in z.namelist()):
            raise ValueError("Unexpected macro/external link")
        strings=shared_strings(z)
        sheets=[{"title":title,"sample_rows":peek(z,name,strings)} for title,name in sheet_titles(z)]
    return {"schema_version":1,"source":SOURCE_PAGE,"source_file":SOURCE,
            "rights":LICENSE,"release":"2026-09","published":"2026-10-23",
            "source_sha256":hashlib.sha256(raw).hexdigest(),"size_bytes":size,"sheets":sheets,
            "status":"schema-audit-only", "caveat":"EIA-860M records preliminary generator-unit estimates; verify IDs, statuses and plant coordinates before mapping."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("workbook")
    p.add_argument("--out",required=True)
    args=p.parse_args()
    doc=audit(args.workbook)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("EIA-860M schema audit",doc["release"],doc["size_bytes"],doc["source_sha256"])
    for sheet in doc["sheets"]:
        print("TAB",sheet["title"],"rows sampled",len(sheet["sample_rows"]))
        for row in sheet["sample_rows"][:4]:
            print(" ",row["row"]," | ".join(x["value"] for x in row["cells"][:25]))
if __name__=="__main__":
    main()
