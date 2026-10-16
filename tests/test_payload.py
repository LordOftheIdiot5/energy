"""Refuse to publish a payload that would render a broken or lying page.

The fetch runs unattended every hour. Without this, a source that starts
returning empty arrays, or prices in the wrong units, would be committed and
published with nothing to stop it - and a page that is confidently wrong is
worse than one that is obviously down.
"""
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "energy.json"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def main() -> int:
    if not DATA.exists():
        print(f"no payload at {DATA}")
        return 1
    d = json.loads(DATA.read_text(encoding="utf-8"))

    zones = d.get("zones") or []
    check("has zones", len(zones) >= 4, f"{len(zones)} zones")

    for z in zones:
        today = z.get("today") or {}
        local = today.get("local") or []
        eur = today.get("eur") or []
        check(f"{z.get('zone')} has 24 hours", len(local) == 24, f"{len(local)}")
        check(f"{z.get('zone')} has EUR alongside", len(eur) == len(local))
        # Nordic power has been negative and has been absurd, but never both
        # at once. These bounds catch a unit change, not a market event.
        if local:
            check(f"{z.get('zone')} prices plausible",
                  all(-5 < v < 50 for v in local),
                  f"{min(local):.3f}..{max(local):.3f} per kWh")

    eu = d.get("europe") or []
    check("has European zones", len(eu) >= 6, f"{len(eu)} zones")
    for z in eu:
        c = z.get("cents") or []
        check(f"{z.get('zone')} has prices", len(c) >= 20, f"{len(c)} points")
        # Euro cents per kWh. Europe has seen negative prices and has seen
        # 70c in a crisis; outside that range the unit has changed, not the
        # market. A series that is half zeros is the Elexon two-provider bug.
        if c:
            zeros = sum(1 for v in c if v == 0)
            check(f"{z.get('zone')} range plausible",
                  all(-20 < v < 120 for v in c), f"{min(c)}..{max(c)}")
            check(f"{z.get('zone')} not half zeros", zeros < len(c) * 0.4,
                  f"{zeros}/{len(c)} zero")

    res = (d.get("reservoirs") or {}).get("zones") or {}
    check("has reservoirs", len(res) >= 4, f"{len(res)} areas")
    for k, v in res.items():
        check(f"{k} fill is a fraction", 0 <= (v.get("fill") or -1) <= 1,
              str(v.get("fill")))

    g = d.get("grid") or {}
    check("has a generation mix", bool(g.get("mix")), str((g.get("mix") or {}).get("hydro")))
    flows = g.get("flows") or []
    check("flows carry a direction, not a minus sign",
          all(f.get("mw", 0) > 0 for f in flows), f"{len(flows)} links")

    wx = d.get("weather") or {}
    check("has weather", len(wx) >= 6, f"{len(wx)} zones")

    com = d.get("commodities") or []
    check("has commodities", len(com) >= 8, f"{len(com)} instruments")
    check("every commodity has a sparkline",
          all(len(c.get("spark") or []) >= 2 for c in com))

    # Gas storage is optional - it needs a GIE key - but must be coherent
    # when present. A silently empty panel would read as "storage is zero".
    gas = (d.get("gasStorage") or {}).get("countries") or []
    if gas:
        check("gas storage percentages are percentages",
              all(0 <= (c.get("fullPct") or 0) <= 100 for c in gas),
              f"{len(gas)} countries")

    fuel = d.get("fuel") or {}
    fuels = fuel.get("fuels") or []
    check("has fuel breakdown", len(fuels) >= 1, f"{len(fuels)} fuels")
    for f in fuels:
        total = f.get("modelledTotal") or 0
        parts = sum(f.get(k) or 0 for k in
                    ("productNok", "roadTax", "co2Tax", "vat"))
        # The whole point of the panel is that the parts add up. If they
        # drift apart, the model is lying about its own arithmetic.
        check(f"{f.get('key')} parts sum to the total",
              abs(parts - total) < 0.02, f"{parts:.2f} vs {total:.2f}")
        check(f"{f.get('key')} is a plausible pump price",
              5 < total < 60, f"{total} NOK/l")

    fr = d.get("france") or {}
    if fr:
        check("French availability is a percentage",
              0 < (fr.get("availabilityPct") or 0) <= 100,
              f"{fr.get('availabilityPct')}%")

    mk = d.get("market") or {}
    margins = mk.get("margins") or []
    check("has margins", len(margins) >= 2, f"{len(margins)} spreads")
    for sp in margins:
        # A margin is a difference of two real prices; if it has exploded, a
        # unit has changed somewhere rather than the market having moved.
        check(f"{sp.get('key')} is sane", abs(sp.get("value") or 0) < 100000,
              f"{sp.get('value')} {sp.get('unit')}")
        check(f"{sp.get('key')} shows its working", len(sp.get("parts") or []) >= 2)
    coh = mk.get("cohorts") or []
    check("has cohorts", len(coh) >= 2, f"{len(coh)} groups")
    # The guard is the point of the correlation section; without the counts
    # it is just a list of suggestive numbers.
    check("correlations state what was tested",
          mk.get("tested") is not None and mk.get("expectedByChance") is not None,
          f"{mk.get('tested')} tested, ~{mk.get('expectedByChance')} by chance")
    check("survived count is not the truncated one",
          (mk.get("survived") or 0) >= len(mk.get("correlations") or []),
          f"{mk.get('survived')} survived, {len(mk.get('correlations') or [])} shown")

    # News is allowed to be empty - it is the least important part and the
    # most fragile - but it must not be malformed when present.
    news = d.get("news") or []
    check("news entries are well formed",
          all(n.get("title") and n.get("url") for n in news),
          f"{len(news)} stories")

    print()
    if failures:
        print(f"FAILED: {len(failures)}")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("payload OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
