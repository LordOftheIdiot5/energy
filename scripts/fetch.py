"""Gather everything that sets an energy price, into one file the page reads.

Sources, all keyless and public:

  spot        hvakosterstrommen.no (NO1-5) and elprisetjustnu.se (SE1-4),
              both over Nord Pool day-ahead. They return local currency AND
              EUR plus the exchange rate used, which is what lets the page
              separate "power got dearer" from "the krone got weaker".
  reservoirs  NVE, weekly fill per Norwegian price zone, back to 1995. The
              history is the point: a fill percentage on its own means
              nothing without the normal for that week of the year.
  commodities Yahoo, the same endpoint stockwatch already reads.

Nothing here needs a key, a quota or a registration, which is the only way a
page like this is still working in a year.
"""
from __future__ import annotations

import json
import statistics
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "energy.json"
UA = "Mozilla/5.0 (compatible; nordl-energy/1.0; +https://nordl.dev)"

# Norwegian zones are hourly, Swedish zones moved to 15-minute settlement and
# return 96 slots. Anything comparing them has to normalise or it silently
# plots four times too many points for half the map.
ZONES = [
    ("NO1", "NO", "Oslo & the south-east", "hvakosterstrommen.no", "NOK_per_kWh"),
    ("NO2", "NO", "Kristiansand & the south", "hvakosterstrommen.no", "NOK_per_kWh"),
    ("NO3", "NO", "Trondheim & the middle", "hvakosterstrommen.no", "NOK_per_kWh"),
    ("NO4", "NO", "Tromsø & the north", "hvakosterstrommen.no", "NOK_per_kWh"),
    ("NO5", "NO", "Bergen & the west", "hvakosterstrommen.no", "NOK_per_kWh"),
    ("SE1", "SE", "Luleå", "elprisetjustnu.se", "SEK_per_kWh"),
    ("SE2", "SE", "Sundsvall", "elprisetjustnu.se", "SEK_per_kWh"),
    ("SE3", "SE", "Stockholm", "elprisetjustnu.se", "SEK_per_kWh"),
    ("SE4", "SE", "Malmö", "elprisetjustnu.se", "SEK_per_kWh"),
]

# NVE's EL areas map one-to-one onto the Norwegian price zones.
RESERVOIR_AREAS = {1: "NO1", 2: "NO2", 3: "NO3", 4: "NO4", 5: "NO5"}

COMMODITIES = [
    ("BZ=F", "Brent crude", "$/bbl", "oil"),
    ("CL=F", "WTI crude", "$/bbl", "oil"),
    ("TTF=F", "TTF gas", "€/MWh", "gas"),
    ("NG=F", "US gas (Henry Hub)", "$/MMBtu", "gas"),
    ("HO=F", "Heating oil", "$/gal", "refined"),
    ("RB=F", "Petrol (RBOB)", "$/gal", "refined"),
    ("EURNOK=X", "EUR/NOK", "", "fx"),
    ("USDNOK=X", "USD/NOK", "", "fx"),
    ("KRBN", "Carbon allowances", "", "transition"),
    ("URA", "Uranium miners", "", "transition"),
    ("FAN", "Wind", "", "transition"),
    ("TAN", "Solar", "", "transition"),
    ("NLR", "Nuclear", "", "transition"),
    ("BDRY", "Dry bulk freight", "", "transition"),
]


def get(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def get_json(url: str, timeout: int = 25):
    return json.loads(get(url, timeout))


# ----------------------------------------------------------------- spot
def spot_day(zone: str, host: str, field: str, day: date) -> dict | None:
    """One zone, one day, normalised to 24 hourly values.

    Returns local currency and EUR side by side. A bill rises when either
    moves, and only one of those is an energy story.
    """
    url = (f"https://www.{host}/api/v1/prices/"
           f"{day.year}/{day.month:02d}-{day.day:02d}_{zone}.json")
    try:
        slots = get_json(url)
    except Exception:
        return None                      # tomorrow is simply not published yet
    if not slots:
        return None

    buckets: dict[int, list[tuple[float, float]]] = {}
    for s in slots:
        try:
            hour = datetime.fromisoformat(s["time_start"]).hour
            buckets.setdefault(hour, []).append(
                (float(s[field]), float(s.get("EUR_per_kWh") or 0))
            )
        except (KeyError, ValueError):
            continue
    if not buckets:
        return None

    hours = sorted(buckets)
    local = [round(statistics.mean(v[0] for v in buckets[h]), 4) for h in hours]
    eur = [round(statistics.mean(v[1] for v in buckets[h]), 5) for h in hours]
    rates = [float(s.get("EXR") or 0) for s in slots if s.get("EXR")]

    return {
        "date": day.isoformat(),
        "resolution": len(slots),
        "hours": hours,
        "local": local,
        "eur": eur,
        "rate": round(statistics.mean(rates), 4) if rates else None,
        "min": min(local),
        "max": max(local),
        "mean": round(statistics.mean(local), 4),
    }


def window(values: list[float], size: int) -> dict | None:
    """Cheapest run of `size` consecutive hours. The actionable number."""
    if len(values) < size:
        return None
    best_at, best = 0, sum(values[:size])
    for i in range(1, len(values) - size + 1):
        run = sum(values[i:i + size])
        if run < best:
            best_at, best = i, run
    return {"start": best_at, "end": best_at + size,
            "mean": round(best / size, 4)}


def collect_spot() -> list[dict]:
    today = date.today()
    tomorrow = today + timedelta(days=1)
    out = []
    for zone, country, label, host, field in ZONES:
        day = spot_day(zone, host, field, today)
        if not day:
            print(f"  ! {zone}: no prices for today")
            continue
        nxt = spot_day(zone, host, field, tomorrow)
        peak_at = day["local"].index(day["max"])
        out.append({
            "zone": zone, "country": country, "label": label,
            "currency": "NOK" if country == "NO" else "SEK",
            "today": day, "tomorrow": nxt,
            "cheapest1": window(day["local"], 1),
            "cheapest3": window(day["local"], 3),
            "peakHour": peak_at,
            "spread": round(day["max"] - day["min"], 4),
        })
        print(f"  {zone}  {day['min']:.3f}-{day['max']:.3f}  "
              f"{day['resolution']} slots"
              + ("  +tomorrow" if nxt else ""))
    return out


# ----------------------------------------------------------- reservoirs
def collect_reservoirs() -> dict:
    """Fill per zone, against the median for this week of the year.

    A reservoir at 52% is meaningless alone. Against thirty years of the same
    week it is either a normal autumn or the reason this winter will hurt.
    """
    try:
        rows = get_json("https://biapi.nve.no/magasinstatistikk/api/"
                        "Magasinstatistikk/HentOffentligData", timeout=40)
    except Exception as e:
        print(f"  ! NVE unavailable: {e}")
        return {}

    el = [r for r in rows if r.get("omrType") == "EL"]
    if not el:
        return {}
    year = max(r["iso_aar"] for r in el)
    week = max(r["iso_uke"] for r in el if r["iso_aar"] == year)

    zones = {}
    for area, zone in RESERVOIR_AREAS.items():
        now = next((r for r in el if r["iso_aar"] == year
                    and r["iso_uke"] == week and r["omrnr"] == area), None)
        if not now:
            continue
        # Same week, every earlier year: the seasonal normal.
        history = [r["fyllingsgrad"] for r in el
                   if r["omrnr"] == area and r["iso_uke"] == week
                   and r["iso_aar"] < year and r.get("fyllingsgrad") is not None]
        normal = statistics.median(history) if history else None
        zones[zone] = {
            "fill": round(now["fyllingsgrad"], 4),
            "twh": round(now["fylling_TWh"], 2),
            "capacityTwh": round(now.get("kapasitet_TWh") or 0, 2),
            "change": round(now.get("endring_fyllingsgrad") or 0, 5),
            "normal": round(normal, 4) if normal is not None else None,
            "vsNormal": round(now["fyllingsgrad"] - normal, 4) if normal else None,
            "years": len(history),
        }
        print(f"  {zone}  fill {now['fyllingsgrad']*100:.1f}%"
              + (f"  normal {normal*100:.1f}%  "
                 f"({(now['fyllingsgrad']-normal)*100:+.1f} pts, {len(history)}y)"
                 if normal else ""))

    national = next((r for r in rows if r.get("omrType") == "NO"
                     and r["iso_aar"] == year and r["iso_uke"] == week), None)
    return {
        "year": year, "week": week, "zones": zones,
        "national": {
            "fill": round(national["fyllingsgrad"], 4),
            "twh": round(national["fylling_TWh"], 2),
        } if national else None,
    }


# ---------------------------------------------------------- commodities
def collect_commodities() -> list[dict]:
    out = []
    for sym, name, unit, group in COMMODITIES:
        url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
               f"{urllib.parse.quote(sym)}?range=6mo&interval=1d")
        try:
            payload = get_json(url)
            block = (payload.get("chart") or {}).get("result")[0]
            closes = [c for c in block["indicators"]["quote"][0]["close"]
                      if c is not None]
        except Exception:
            print(f"  ! {sym}: no data")
            continue
        if len(closes) < 2:
            continue
        last, prev = closes[-1], closes[-2]
        first = closes[0]
        out.append({
            "symbol": sym, "name": name, "unit": unit, "group": group,
            "last": round(last, 4),
            "changePct": round((last / prev - 1) * 100, 2),
            "changeSixMonthPct": round((last / first - 1) * 100, 1),
            "low": round(min(closes), 4),
            "high": round(max(closes), 4),
            # Position in the six-month range: a price can be falling and
            # still be near the top of where it has been.
            "rangePos": round((last - min(closes)) /
                              (max(closes) - min(closes)) * 100, 1)
            if max(closes) > min(closes) else 50.0,
            "spark": [round(c, 4) for c in closes[-60:]],
        })
        print(f"  {sym:<10}{name:<22}{last:>10.3f}  {out[-1]['changePct']:+.2f}%")
    return out


def main() -> int:
    print("spot prices")
    zones = collect_spot()
    print("\nreservoirs")
    reservoirs = collect_reservoirs()
    print("\ncommodities")
    commodities = collect_commodities()
    print("\nnews")
    try:
        import news as news_module
        stories = news_module.collect(30)
    except Exception as e:                                   # noqa: BLE001
        # News is the least important part of the page and the most likely to
        # break: one bad RSS response must not cost the prices.
        print(f"  ! news unavailable: {e}")
        stories = []

    payload = {
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "zones": zones,
        "reservoirs": reservoirs,
        "commodities": commodities,
        "news": stories,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}  "
          f"{len(zones)} zones, {len(commodities)} instruments, "
          f"{len(stories)} stories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
