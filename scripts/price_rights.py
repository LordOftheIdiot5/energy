"""Price response rights gate. Only documented open Energy-Charts zones.
Do not preserve restricted or unverified fallback data as open. Other feeds
retain their own terms and are excluded from the commercial export allowlist.
"""
OPEN_ZONES=frozenset("AT BE CH CZ DE-LU DE-AT-LU DK1 DK2 FR HU IT-North NL NO2 PL SE4 SI".split())
def permitted(zone,license_info):
    s=str(license_info or "").lower()
    return zone in OPEN_ZONES and ("cc by 4.0" in s or "creativecommons.org/licenses/by/4.0" in s) and not any(term in s for term in ("private and internal","private use","non-commercial","prohibited","not permitted"))
def eur_mwh(unit):
    return str(unit or "").replace(" ","").replace("€","EUR").lower()=="eur/mwh"
