"""Normalize factual TYNDP portfolio fields; research output only pending reuse review."""
import hashlib, io, json, re, zipfile
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from pathlib import Path
import urllib.request
from research_audit import PORTFOLIO, NS

def rows(z, path, shared):
    root = ET.fromstring(z.read(path))
    for row in root.findall("s:sheetData/s:row", NS):
        d = {}
        for c in row.findall("s:c", NS):
            key = re.match(r"^[A-Z]+", c.get("r", ""))
            if not key:
                raise ValueError("Invalid cell reference")
            v = c.findtext("s:v", default="", namespaces=NS)
            if c.get("t") == "s" and v:
                v = shared[int(v)]
            elif c.get("t") == "inlineStr":
                v = "".join(t.text or "" for t in c.iterfind(".//s:t", NS))
            if v.strip():
                d[key.group()] = v.strip()
        yield int(row.get("r")), d

def parse_table(z, sheet, headers, shared):
    out = []
    found = False
    for n, row in rows(z, "xl/worksheets/sheet%d.xml" % sheet, shared):
        if n == 4:
            if any(row.get(col) != name for col, name in headers.items()):
                raise ValueError("Changed source headers in sheet %s" % sheet)
            found = True
        if n > 4 and row:
            if not row.get("B"):
                raise ValueError("Unexpected nonempty row")
            out.append(row)
    if not found:
        raise ValueError("No source headers")
    return out

def normalize(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if sum(i.file_size for i in z.infolist()) > 100_000_000:
            raise ValueError("Oversized workbook")
        names = [s.get("name") for s in ET.fromstring(z.read("xl/workbook.xml")).findall("s:sheets/s:sheet", NS)]
        if len(names) != 7 or names[1:4] != ["Transmission Projects","Transmission Investments","Storage Projects"] or names[6] != "Borders":
            raise ValueError("Sheet layout changed")
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            shared = ["".join(t.text or "" for t in si.iterfind(".//s:t", NS)) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("s:si", NS)]
        result = {}
        counts = {}
        for sheet, kind, cols in [
            (2, "Transmission", {"I":"Cross-border or internal","J":"Status","K":"Commissioning year","L":"Submission window"}),
            (4, "Storage", {"I":"Status","J":"Commissioning year","K":"Submission window"})]:
            headers = {"B":"Type","C":"Project ID","D":"Name","E":"Project promoters","G":"New or upgrade","H":"Project category", **cols}
            table = parse_table(z, sheet, headers, shared)
            for row in table:
                if row.get("B") != kind or not re.fullmatch(r"[0-9]+",row.get("C","")) or not row.get("D"):
                    raise ValueError("Invalid project identity")
                key = kind.lower()+":"+row["C"]
                if key in result:
                    raise ValueError("Duplicate project ID")
                result[key] = {"id":key,"source_id":row["C"],"kind":kind.lower(),"name":row["D"],
                    "promoters_reported":row.get("E"),"new_or_upgrade":row.get("G"),"category":row.get("H"),
                    "status_reported":row.get("J" if sheet==2 else "I"),
                    "commissioning_as_reported":row.get("K" if sheet==2 else "J"),
                    "submission_window":row.get("L" if sheet==2 else "K"),
                    "cross_border":row.get("I") if sheet==2 else None,"borders":[],"investments":[]}
            counts[kind.lower()]=len(table)
        if counts != {"transmission":199,"storage":69}:
            raise ValueError("Unexpected published portfolio count: "+str(counts))
        investments=set()
        for row in parse_table(z,3,{"B":"Project ID","C":"Investment ID","D":"Investment Name","F":"Commissioning month and year foreseen by the project promoter(s)","G":"Status"},shared):
            key="transmission:"+row["B"]
            ident=row.get("C")
            if key not in result or not ident or (key,ident) in investments:
                raise ValueError("Invalid investment parent or duplicate")
            investments.add((key,ident))
            result[key]["investments"].append({"source_id":ident,"name":row.get("D"),"commissioning_as_reported":row.get("F"),"status_reported":row.get("G")})
        for row in parse_table(z,7,{"B":"TransmissionProject_Id","C":"Border"},shared):
            key="transmission:"+row["B"]
            if key not in result or not row.get("C"):
                raise ValueError("Invalid border parent")
            if row["C"] not in result[key]["borders"]:
                result[key]["borders"].append(row["C"])
    return {"schema_version":1,"source":PORTFOLIO,"observed_at":datetime.now(timezone.utc).isoformat(),
        "source_sha256":hashlib.sha256(raw).hexdigest(),"complete":True,"counts":counts,"investment_count":len(investments),
        "rights_status":"review_required","notice":"Reported portfolio entries; not independently verified operational status. No source descriptions copied. Not cleared for commercial republication.","rows":list(result.values())}

def collect():
    req=urllib.request.Request(PORTFOLIO,headers={"User-Agent":"Nordl Energy (https://energy.nordl.dev/)"})
    with urllib.request.urlopen(req,timeout=45) as r:
        raw=r.read(20_000_001)
    if len(raw)>20_000_000:
        raise ValueError("Oversized source")
    return normalize(raw)

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    d=collect()
    if a.output:
        from hydro_extended import write_json
        a.output.parent.mkdir(parents=True,exist_ok=True)
        write_json(a.output,d)
    print(json.dumps({k:v for k,v in d.items() if k!="rows"},indent=2))
