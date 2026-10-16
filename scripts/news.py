"""Energy technology news: what is being built, laid, discovered or switched on.

Topic queries rather than company queries. The interesting things in energy are
projects and machines - a cable between two countries, a reactor design getting
licensed, a factory for electrolysers - and those are reported by trade press
long before they reach a company's results.

Google News RSS is keyless and takes a search term, which is the whole reason
this is possible without an API account. The quality filter is the valuable
part: search any energy term and half the results are content farms recycling
a press release, so publishers are weighted and the worst are dropped.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

UA = "Mozilla/5.0 (compatible; nordl-energy/1.0; +https://nordl.dev)"

# Each topic is a search and a label. Phrases are quoted in the query so
# "subsea cable" does not match every story containing "cable".
TOPICS: list[tuple[str, str]] = [
    ("interconnector", "Grids & cables"),
    ("subsea power cable", "Grids & cables"),
    ("HVDC", "Grids & cables"),
    ("transmission grid upgrade", "Grids & cables"),
    ("grid connection queue", "Grids & cables"),
    ("small modular reactor", "Nuclear"),
    ("nuclear reactor construction", "Nuclear"),
    ("fusion energy", "Nuclear"),
    ("grid scale battery", "Storage"),
    ("pumped hydro storage", "Storage"),
    ("sodium ion battery", "Storage"),
    ("offshore wind farm", "Wind & solar"),
    ("floating offshore wind", "Wind & solar"),
    ("solar farm commissioned", "Wind & solar"),
    ("electrolyser factory", "Hydrogen & fuels"),
    ("green hydrogen project", "Hydrogen & fuels"),
    ("carbon capture project", "Hydrogen & fuels"),
    ("geothermal drilling", "Discovery & resources"),
    ("lithium discovery", "Discovery & resources"),
    ("gas field discovery", "Discovery & resources"),
]

# Publishers that break things, and publishers that recycle. A positive score
# earns a place; the strongly negative ones never appear.
WEIGHT = {
    "reuters": 3, "bloomberg": 3, "financial times": 3, "ft.com": 3,
    "the guardian": 2, "bbc": 2, "cnbc": 2, "associated press": 2,
    "e24": 2, "nrk": 2, "dn.no": 2, "di.se": 2, "yle": 2,
    "upstream": 2, "tradewinds": 2, "offshore energy": 2, "recharge": 2,
    "windpower monthly": 2, "pv magazine": 2, "world nuclear news": 2,
    "power engineering": 1, "utility dive": 2, "canary media": 1,
    "heatmap": 1, "the register": 1, "ieee spectrum": 2, "ars technica": 1,
    "mining.com": 1, "renewables now": 1, "montel": 2, "argus media": 2,
    "marketbeat": -4, "zacks": -4, "simply wall st": -4, "insider monkey": -4,
    "tipranks": -3, "stocktwits": -4, "investing.com": -2, "benzinga": -2,
    "gurufocus": -4, "motley fool": -4, "247 wall st": -4, "invezz": -3,
    "newsfilecorp": -3, "accesswire": -3, "globenewswire": -1, "prnewswire": -1,
    "einnews": -4, "openpr": -4, "digitaljournal": -3,
}

# Words that mark a story as a thing happening rather than a thing opined.
CONCRETE = ("commission", "begins", "began", "launch", "start", "started",
            "approve", "licence", "license", "award", "contract", "sign",
            "complete", "connect", "energis", "first power", "online",
            "discover", "found", "breakthrough", "record", "order",
            "break ground", "groundbreaking", "operational", "switch on",
            "lay", "laid", "install", "milestone", "open")

SPECULATIVE = ("could", "may ", "might", "plans to", "eyes ", "mulls",
               "considers", "report says", "rumou", "stock", "shares",
               "price target", "analyst", "buy or sell", "investors")

# Market commentary dressed as energy news. "FTSE 100 Utility National Grid
# (LSE:NG.) Earnings Upgrade" scored well on "upgrade" and a digit, and is
# about a share price rather than anything being built. An ETF launch is a
# financial product, not a machine.
FINANCIAL = ("earnings", "ftse", "lse:", "nyse:", "nasdaq:", "(asx", "tsx:",
             "dividend", "valuation", "rating", " etf", "etf ", "p/e",
             "market cap", "quarterly results", "q1 ", "q2 ", "q3 ", "q4 ")


def _get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _weight(publisher: str) -> int:
    p = (publisher or "").lower()
    for name, score in WEIGHT.items():
        if name in p:
            return score
    return 0


def _score(title: str, publisher: str) -> int:
    t = (title or "").lower()
    if any(w in t for w in FINANCIAL):
        return -9                      # a share price story, whatever it mentions
    s = _weight(publisher)
    s += 2 if any(w in t for w in CONCRETE) else 0
    s -= 2 if any(w in t for w in SPECULATIVE) else 0
    # A number in the headline usually means a size, a date or a capacity.
    s += 1 if re.search(r"\d", t) else 0
    return s


# Words too common in energy headlines to distinguish one story from another.
_STOP = {"the", "and", "for", "with", "from", "that", "this", "its", "has",
         "new", "energy", "power", "project", "projects", "plant", "says",
         "will", "first", "more", "over", "into", "after", "about", "year",
         "million", "billion", "company", "group", "announces", "announced"}


def _tokens(title: str) -> set[str]:
    # Trailing -s stripped so "cables" and "cable" are one token. Crude, but
    # the alternative is a stemmer dependency for a page that should stay a
    # single file and no installs.
    out = set()
    for w in re.findall(r"[a-z0-9]{4,}", title.lower()):
        if w in _STOP:
            continue
        out.add(w[:-1] if w.endswith("s") and not w.endswith("ss") else w)
    return out


def _same_story(a: str, b: str) -> bool:
    """Is this the same event, reported twice?

    One cable factory opening reached four outlets with four different
    headlines, so matching on the text itself finds nothing. What they share
    is the distinctive nouns - the company, the project, the voltage - so
    overlap of those is the signal.
    """
    ta, tb = _tokens(a), _tokens(b)
    if len(ta) < 3 or len(tb) < 3:
        return a.lower() == b.lower()
    shared = ta & tb
    # Both conditions: a high ratio alone merges two short headlines that
    # happen to share a word, and a raw count alone merges long ones that
    # share boilerplate. Together they want several distinctive nouns in
    # common - the company, the project, the voltage.
    return len(shared) >= 3 and len(shared) / min(len(ta), len(tb)) >= 0.5


def _age_hours(published: str) -> float | None:
    try:
        dt = parsedate_to_datetime(published)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except Exception:
        return None


def fetch_topic(topic: str, category: str, count: int = 12) -> list[dict]:
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(f'"{topic}"')
           + "&hl=en-GB&gl=GB&ceid=GB:en")
    try:
        root = ET.fromstring(_get(url))
    except Exception as e:
        print(f"  ! {topic}: {e}")
        return []

    out = []
    for item in root.findall(".//item")[:count]:
        title = (item.findtext("title") or "").strip()
        node = item.find("{*}source")
        publisher = node.text if node is not None else ""
        if publisher and title.endswith(f"- {publisher}"):
            title = title.rsplit(" - ", 1)[0]
        published = (item.findtext("pubDate") or "").strip()
        age = _age_hours(published)
        if age is None or age > 24 * 21:        # three weeks is not news
            continue
        score = _score(title, publisher)
        if score < 1:                            # farms and commentary
            continue
        out.append({
            "title": title,
            "publisher": publisher,
            "url": (item.findtext("link") or "").strip(),
            "topic": topic,
            "category": category,
            "ageHours": round(age, 1),
            "score": score,
        })
    return out


def collect(limit: int = 30) -> list[dict]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        batches = list(pool.map(lambda t: fetch_topic(*t), TOPICS))

    flat = [it for batch in batches for it in batch]
    # Rank before de-duplicating, so when the same story is carried by four
    # outlets the surviving copy is the best-sourced one rather than whichever
    # happened to be fetched first.
    flat.sort(key=lambda i: (-i["score"], i["ageHours"]))

    items: list[dict] = []
    for it in flat:
        if not any(_same_story(it["title"], k["title"]) for k in items):
            items.append(it)
    print(f"  {len(flat) - len(items)} duplicate reports merged")
    picked, per_cat = [], {}
    for it in items:
        c = it["category"]
        if per_cat.get(c, 0) >= 6:
            continue
        per_cat[c] = per_cat.get(c, 0) + 1
        picked.append(it)
        if len(picked) >= limit:
            break
    print(f"  {len(picked)} stories from {len(items)} unique, "
          f"{len(TOPICS)} topics")
    return picked


if __name__ == "__main__":
    for item in collect():
        print(f"  [{item['score']}] {item['category']:<22}"
              f"{item['title'][:62]:<64}{item['publisher']}")
