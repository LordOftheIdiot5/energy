"""What energy prices do to companies.

Two approaches, and the order matters.

A margin is arithmetic. Smelting aluminium takes roughly 14 MWh a tonne, so a
smelter's economics ARE the metal price minus fourteen times the power price.
That cannot be a coincidence or a spurious fit; it is the cost structure.

A correlation is a measurement, and a treacherous one. Six drivers against a
few dozen companies is hundreds of pairs, and at the usual thresholds a good
handful will look significant purely by chance. So correlations are reported
only above a strength floor, with the sample size attached and an explicit
count of how many false positives to expect - and they are used to CHECK the
margins, never to replace them.
"""
from __future__ import annotations

import json
import math
import statistics
import urllib.parse
import urllib.request
from datetime import datetime, timezone

UA = "nordl-energy/1.0 github.com/LordOftheIdiot5/energy"

# Electricity per tonne of primary aluminium. Modern pots run 13-15 MWh;
# 14 is the usual round figure and the number the industry quotes.
MWH_PER_TONNE_ALUMINIUM = 14.0

# A combined-cycle gas plant converts about this much of the gas it burns.
CCGT_EFFICIENCY = 0.55
# Tonnes of CO2 per MWh of gas burned in such a plant.
CO2_PER_MWH = 0.37

# Companies with a stated mechanism, not a hunch. Each is here because of
# something specific about how it makes money.
COHORTS = [
    ("Producers", "gain when energy is dear", [
        ("EQNR.OL", "Equinor"), ("AKRBP.OL", "Aker BP"),
        ("VAR.OL", "Vår Energi"), ("FORTUM.HE", "Fortum"),
        ("VER.VI", "Verbund"), ("ORSTED.CO", "Ørsted"),
    ]),
    ("Power-intensive", "pay for it as an input", [
        ("NHY.OL", "Norsk Hydro"), ("YAR.OL", "Yara"),
        ("BOL.ST", "Boliden"), ("SSAB-B.ST", "SSAB"),
        ("ELK.OL", "Elkem"), ("AMG.AS", "AMG"),
    ]),
    ("Grid build-out", "paid to fix the bottleneck", [
        ("NEX.PA", "Nexans"), ("PRY.MI", "Prysmian"),
        ("ENR.DE", "Siemens Energy"), ("ABBN.SW", "ABB"),
        ("SU.PA", "Schneider Electric"), ("HUBN.SW", "Huber+Suhner"),
    ]),
]

# How many trading days of overlap before a correlation is worth printing.
MIN_OBSERVATIONS = 60
# Below this, a correlation is noise dressed up as a finding.
MIN_ABS_R = 0.35


def _get(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def series(symbol: str, rng: str = "1y") -> dict | None:
    """Daily closes keyed by date, so two series can be aligned honestly."""
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(symbol)}?range={rng}&interval=1d")
    try:
        block = (_get(url).get("chart") or {}).get("result")[0]
    except Exception:
        return None
    closes = block["indicators"]["quote"][0]["close"]
    out = {}
    for ts, c in zip(block.get("timestamp") or [], closes):
        if c is None:
            continue
        out[datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")] = float(c)
    return out or None


def pct_change(by_date: dict) -> dict:
    """Daily returns. Correlating prices rather than returns manufactures
    agreement: any two things that drift upward look correlated."""
    days = sorted(by_date)
    out = {}
    for prev, cur in zip(days, days[1:]):
        if by_date[prev]:
            out[cur] = by_date[cur] / by_date[prev] - 1.0
    return out


def pearson(a: dict, b: dict) -> tuple[float | None, int]:
    shared = sorted(set(a) & set(b))
    n = len(shared)
    if n < MIN_OBSERVATIONS:
        return None, n
    xs = [a[d] for d in shared]
    ys = [b[d] for d in shared]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None, n
    return num / (dx * dy), n


# ------------------------------------------------------------- margins
def collect_margins(power_eur_mwh: float | None, fx: dict) -> list[dict]:
    """Spreads a company actually earns, in the units it earns them."""
    out = []
    eurusd = fx.get("EURUSD")

    alu = series("ALI=F", "6mo")
    if alu and power_eur_mwh and eurusd:
        metal = list(alu.values())[-1]                      # USD per tonne
        power_usd = power_eur_mwh * eurusd                  # USD per MWh
        cost = power_usd * MWH_PER_TONNE_ALUMINIUM
        out.append({
            "key": "smelter",
            "name": "Aluminium smelter margin",
            "value": round(metal - cost, 0),
            "unit": "$/tonne",
            "parts": [
                {"label": "Aluminium", "value": round(metal, 0), "unit": "$/t"},
                {"label": f"Power ({MWH_PER_TONNE_ALUMINIUM:.0f} MWh/t)",
                 "value": -round(cost, 0), "unit": "$/t"},
            ],
            "watch": "Norsk Hydro, Elkem",
            "note": ("At spot power. Most smelters buy on long contracts, so "
                     "this shows the pressure they are under rather than what "
                     "their accounts will say."),
        })

    gas = series("TTF=F", "6mo")
    if gas and power_eur_mwh:
        gas_eur = list(gas.values())[-1]                    # EUR per MWh thermal
        fuel = gas_eur / CCGT_EFFICIENCY                    # per MWh electrical
        out.append({
            "key": "spark",
            "name": "Spark spread",
            "value": round(power_eur_mwh - fuel, 1),
            "unit": "€/MWh",
            "parts": [
                {"label": "Power", "value": round(power_eur_mwh, 1), "unit": "€/MWh"},
                {"label": f"Gas at {CCGT_EFFICIENCY:.0%} efficiency",
                 "value": -round(fuel, 1), "unit": "€/MWh"},
            ],
            "watch": "Fortum, Ørsted, RWE",
            "note": ("Carbon is excluded: EUA futures have no free feed. At "
                     f"{CO2_PER_MWH} t/MWh a gas plant's real spread is lower "
                     "than this by the carbon price times that figure."),
        })

    crude, heat, petrol = series("CL=F", "6mo"), series("HO=F", "6mo"), series("RB=F", "6mo")
    if crude and heat and petrol:
        c = list(crude.values())[-1]                        # $/barrel
        h = list(heat.values())[-1] * 42                    # $/gal -> $/barrel
        p = list(petrol.values())[-1] * 42
        crack = (2 * p + h) / 3 - c                         # the 3-2-1 crack
        out.append({
            "key": "crack",
            "name": "Refining crack (3-2-1)",
            "value": round(crack, 2),
            "unit": "$/bbl",
            "parts": [
                {"label": "2 petrol + 1 diesel", "value": round((2 * p + h) / 3, 2),
                 "unit": "$/bbl"},
                {"label": "Crude", "value": -round(c, 2), "unit": "$/bbl"},
            ],
            "watch": "Equinor downstream, Neste, OMV",
            "note": ("What a refinery earns turning a barrel into fuel, and "
                     "the part of a pump price that is neither crude nor tax."),
        })
    return out


# ------------------------------------------------------------- cohorts
def collect_equities(drivers: dict) -> dict:
    """Cohort performance, then correlations as a check on the story."""
    cohorts, all_members = [], []
    for name, why, members in COHORTS:
        rows = []
        for sym, label in members:
            s = series(sym, "1y")
            if not s or len(s) < MIN_OBSERVATIONS:
                print(f"  ! {sym}: no usable history")
                continue
            vals = list(s.values())
            rows.append({
                "symbol": sym, "name": label,
                "last": round(vals[-1], 2),
                "changePct": round((vals[-1] / vals[-2] - 1) * 100, 2),
                "yearPct": round((vals[-1] / vals[0] - 1) * 100, 1),
                "returns": pct_change(s),
            })
            all_members.append((sym, label, rows[-1]["returns"]))
        if rows:
            cohorts.append({
                "name": name, "why": why,
                "members": [{k: v for k, v in r.items() if k != "returns"}
                            for r in rows],
                "medianYearPct": round(statistics.median(
                    r["yearPct"] for r in rows), 1),
            })
            print(f"  {name:<16}{len(rows)} companies, "
                  f"median {cohorts[-1]['medianYearPct']:+.1f}% over a year")

    # Correlations, with the multiple-comparisons problem stated rather than
    # hidden: tested pairs, surviving pairs, and how many of those a pure
    # coincidence would have produced anyway.
    found, tested = [], 0
    for dname, dreturns in drivers.items():
        for sym, label, rets in all_members:
            r, n = pearson(dreturns, rets)
            if r is None:
                continue
            tested += 1
            if abs(r) >= MIN_ABS_R:
                found.append({"driver": dname, "symbol": sym, "name": label,
                              "r": round(r, 2), "n": n})
    found.sort(key=lambda f: -abs(f["r"]))
    # Under the null, P(|r| >= MIN_ABS_R) for n~250 is small but not zero;
    # 0.3% is a fair rough figure and enough to keep the reader honest.
    expected_by_chance = round(tested * 0.003, 1)
    print(f"  correlations: {tested} pairs tested, {len(found)} above "
          f"|r|>={MIN_ABS_R}, ~{expected_by_chance} expected by chance")

    return {
        "cohorts": cohorts,
        "correlations": found[:12],
        # The full count, not the truncated one: the page said "top 12 of 12"
        # while fourteen had actually cleared the bar.
        "survived": len(found),
        "tested": tested,
        "threshold": MIN_ABS_R,
        "expectedByChance": expected_by_chance,
    }
