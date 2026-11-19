"""Published source-reported hydropower subcatchment transfer network.
NVE nextDelfeltNr is the receiving subcatchment where water is transferred
if the source subcatchment does not drain directly to a power station.
It is not a natural river topology or a quantified flow model.
"""
import json
from collections import Counter,defaultdict
from pathlib import Path
from hydro_extended import write_json
SOURCE="https://gis3.nve.no/map/rest/services/Mapservices/VassdragsreguleringVannkraft/MapServer/8"
SPEC="https://gis3.nve.no/metadata/produktspesifikasjoner/produktspesifikasjon_vannkraft.pdf"
LICENSE="https://data.norge.no/nlod/"
def valid_id(v):return type(v) is int and v>0
def build(catchments):
    counts=Counter(r.get("delfeltNr") for r in catchments if valid_id(r.get("delfeltNr")))
    nodes={r["delfeltNr"]:r for r in catchments if valid_id(r.get("delfeltNr")) and counts[r["delfeltNr"]]==1}
    edges=[];incoming=defaultdict(list);unresolved=0
    for k,r in sorted(nodes.items()):
        d=r.get("nesteDelfeltNr")
        if not valid_id(d):continue
        if d==k or d not in nodes:
            unresolved+=1;continue
        edges.append((k,d));incoming[d].append(k)
    outgoing=dict(edges)
    rows=[]
    for k,r in sorted(nodes.items()):
        rows.append({"catchmentId":k,"recordId":r["id"],"name":r.get("delfeltNavn"),"reportedPlantId":r.get("vannkraftverkNr"),"reportedReservoirId":r.get("magasinNr"),"receivingCatchmentId":outgoing.get(k),"sourceCatchmentIds":sorted(incoming[k])})
    return rows,{"matched_directed_edges":len(edges),"unresolved_or_self_edges":unresolved,"ambiguous_ids":sum(x>1 for x in counts.values())}
def generate(directory):
    directory=Path(directory);d=json.loads((directory/"nve-catchments-v1.json").read_text())
    if d.get("source")!=SOURCE or d.get("license")!=LICENSE:raise ValueError("Unexpected catchment provenance")
    rows,stats=build(d["rows"])
    payload={"schema_version":1,"source":SOURCE,"methodology":SPEC,"license":LICENSE,"attribution":"NVE; Nordl exact identifier normalization","generated":d.get("generated"),"notice":"Direct source-reported regulated-water transfer references; not measured flow, natural river routing, or proof of current operation. Ambiguous/missing targets excluded.","coverage":stats,"rows":rows}
    path=directory/"hydro-transfer-network-v1.json";write_json(path,payload)
    print("Hydropower transfer network:",len(rows),"source identifiers;",stats)
    return path
