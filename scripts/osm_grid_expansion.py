"""Independent regional acquisition pilot; never modify an admitted production cohort."""
import argparse
from pathlib import Path
from osm_grid_pilot import collect
from osm_extract_sources import SOURCES
EXPANSION={"EE":[("Geofabrik","https://download.geofabrik.de/europe/estonia-latest.osm.pbf")],"LV":[("Geofabrik","https://download.geofabrik.de/europe/latvia-latest.osm.pbf")],"FO":[("Geofabrik","https://download.geofabrik.de/europe/faroe-islands-latest.osm.pbf")],"AL":[("Geofabrik","https://download.geofabrik.de/europe/albania-latest.osm.pbf")]}
# Independently listed public extracts, tried only on transport failures.
EXPANSION["EE"].append(("BBBike","https://data.bbbike.org/osm/pbf/region/europe/estonia.osm.pbf"))
EXPANSION["AL"].append(("BBBike","https://data.bbbike.org/osm/pbf/region/europe/albania.osm.pbf"))
# Latvia BBBike listing exceeds our current cap; keep the primary source.
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--region",choices=EXPANSION,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    collect(a.region,a.out,sources=EXPANSION)
