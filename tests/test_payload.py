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
