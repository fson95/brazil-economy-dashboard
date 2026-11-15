#!/usr/bin/env python3
"""Fetch US series from FRED and write data-us.js for the dashboard.

Needs FRED_API_KEY in the environment. The key is only ever sent to FRED and is
never printed. A series that fails keeps its previous data; the file is only
rewritten when some observation actually changed.
"""
import datetime, json, os, sys, urllib.error, urllib.parse, urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data-us.js")
PREFIX, SUFFIX = "window.SEED_US=", ";\n"
START = "2010-01-01"
# (series id, FRED units) - "pc1" asks FRED for percent change from a year ago. Keep in step with META_US in index.html.
SERIES = [
    ("DFEDTARU", "lin"), ("CPIAUCSL", "pc1"), ("CPILFESL", "pc1"), ("PCEPI", "pc1"),
    ("DGS2", "lin"), ("DGS10", "lin"), ("MORTGAGE30US", "lin"),
    ("DTWEXBGS", "lin"), ("BOPGSTB", "lin"),
    ("GDPC1", "lin"), ("INDPRO", "lin"), ("RSAFS", "lin"), ("UMCSENT", "lin"),
    ("UNRATE", "lin"), ("PAYEMS", "lin"), ("CES0500000003", "lin"), ("ICSA", "lin"),
    ("GFDEGDQ188S", "lin"),
    ("TOTALSL", "lin"), ("DRCCLACBS", "lin"),
    ("SP500", "lin"), ("VIXCLS", "lin"),
]


def parse(payload):
    """FRED observations -> [[date, value]], skipping the '.' placeholders FRED uses for missing days."""
    out = []
    for o in payload["observations"]:
        try:
            out.append([o["date"], float(o["value"])])
        except ValueError:
            pass
    return out


def fetch(sid, units, key):
    q = urllib.parse.urlencode({"series_id": sid, "units": units, "api_key": key, "file_type": "json", "observation_start": START})
    with urllib.request.urlopen("https://api.stlouisfed.org/fred/series/observations?" + q, timeout=60) as r:
        return parse(json.load(r))


def main():
    assert parse({"observations": [{"date": "2024-01-01", "value": "3.7"}, {"date": "2024-01-02", "value": "."}]}) == [["2024-01-01", 3.7]]
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        sys.exit("FRED_API_KEY is not set")
    try:
        old = json.loads(open(OUT).read()[len(PREFIX):-len(SUFFIX)])["series"]
    except (OSError, ValueError, KeyError):
        old = {}
    new, failed = dict(old), []
    for sid, units in SERIES:
        try:
            obs = fetch(sid, units, key)
            if not obs:
                raise ValueError("no observations")
            new[sid] = obs
            print(f"{sid}: {len(obs)} observations, latest {obs[-1][0]}")
        except urllib.error.HTTPError as e:      # never print the exception itself: its URL carries the key
            failed.append(sid); print(f"{sid}: FAILED (HTTP {e.code})")
        except Exception as e:
            failed.append(sid); print(f"{sid}: FAILED ({type(e).__name__})")
    if len(failed) == len(SERIES):
        sys.exit("every series failed - check the API key")
    if new == old:
        print("no changes"); return
    seed = {"fetchedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "series": new}
    with open(OUT, "w") as f:
        f.write(PREFIX + json.dumps(seed, separators=(",", ":")) + SUFFIX)
    print(f"wrote data-us.js ({len(new)} series, {len(failed)} failed)")


if __name__ == "__main__":
    main()
