"""Backfill historical NBA game-TOTALS (over/under) odds from The Odds API.

Totals are a FEATURED market, so:
  - available back to June 2020 (vs May 2023 for player props)
  - fetched in BULK: one /historical/.../odds call returns every game at a snapshot
    -> cost = 10 credits per snapshot (10 x 1 market x 1 region), NOT per game.

We take one bulk snapshot per game day (default 16:00 UTC = noon ET, before the slate,
so the whole day is 'upcoming') and keep DraftKings' total line + over/under prices.

Output: data/raw/historical_game_totals_odds.csv
  date, game, home_team, away_team, total_line, over_odds, under_odds,
  bookmaker_key, snapshot_time_utc, event_id, commence_time
"""

from pathlib import Path
import argparse
import os
import time
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = RAW / "historical_game_totals_odds.csv"

SPORT = "basketball_nba"
REGIONS = "us"
MARKET = "totals"
ODDS_FORMAT = "american"
BASE = "https://api.the-odds-api.com/v4/historical/sports"
BOOK = "draftkings"


def load_env_local():
    f = ROOT / ".env.local"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_key():
    load_env_local()
    k = os.environ.get("ODDS_API_KEY")
    if not k:
        raise RuntimeError("Missing ODDS_API_KEY (.env.local).")
    return k


def et_date(ts):
    return pd.Timestamp(ts).tz_convert("America/New_York").strftime("%Y-%m-%d") if ts else None


def get_bulk_odds(key, iso):
    url = f"{BASE}/{SPORT}/odds"
    r = requests.get(url, params={"apiKey": key, "regions": REGIONS, "markets": MARKET,
                                  "oddsFormat": ODDS_FORMAT, "date": iso})
    print(f"  [{iso}] status={r.status_code} remaining={r.headers.get('x-requests-remaining')} "
          f"used={r.headers.get('x-requests-used')} cost={r.headers.get('x-requests-last')}")
    r.raise_for_status()
    return r.json()


def flatten(snapshot_iso, event):
    home, away = event.get("home_team"), event.get("away_team")
    ct = event.get("commence_time")
    base = {"date": et_date(ct), "game": f"{away} @ {home}", "home_team": home,
            "away_team": away, "event_id": event.get("id"),
            "commence_time": ct, "snapshot_time_utc": snapshot_iso}
    for bk in event.get("bookmakers", []):
        if bk.get("key") != BOOK:
            continue
        for mk in bk.get("markets", []):
            if mk.get("key") != MARKET:
                continue
            over = under = line = None
            for o in mk.get("outcomes", []):
                if o.get("name") == "Over":
                    over, line = o.get("price"), o.get("point")
                elif o.get("name") == "Under":
                    under = o.get("price")
            if over is not None and under is not None:
                return [{**base, "total_line": line, "over_odds": over,
                         "under_odds": under, "bookmaker_key": BOOK}]
    return []


def daterange(s, e):
    cur = s
    while cur <= e:
        yield cur
        cur += pd.Timedelta(days=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--hour-utc", type=int, default=16)
    ap.add_argument("--max-credits", type=int, default=12000)
    args = ap.parse_args()

    key = get_key()
    start, end = pd.Timestamp(args.start), pd.Timestamp(args.end)
    sd, ed = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    rows, seen, calls = [], set(), 0
    for day in daterange(start, end):
        iso = f"{day.strftime('%Y-%m-%d')}T{args.hour_utc:02d}:00:00Z"
        if calls * 10 >= args.max_credits:
            print(f"Hit --max-credits; stopping."); break
        try:
            payload = get_bulk_odds(key, iso)
        except requests.HTTPError as ex:
            print(f"  failed {iso}: {ex}"); continue
        calls += 1
        n = 0
        for ev in (payload.get("data") or []):
            eid = ev.get("id")
            d = et_date(ev.get("commence_time"))
            if not eid or eid in seen or d is None or d < sd or d > ed:
                continue
            seen.add(eid)
            r = flatten(iso, ev)
            rows.extend(r)
            n += len(r)
        print(f"  {day.strftime('%Y-%m-%d')}: {n} new games (cumulative {len(seen)})")
        time.sleep(0.2)

    if rows:
        new = pd.DataFrame(rows)
        if OUT.exists():
            new = pd.concat([pd.read_csv(OUT), new], ignore_index=True)
        new = new.drop_duplicates(subset=["event_id", "snapshot_time_utc", "total_line",
                                          "over_odds", "under_odds"])
        new.to_csv(OUT, index=False)
        print(f"\nSaved {len(new):,} rows to {OUT}")
    print(f"Snapshots: {calls} | est credits this run: ~{calls*10}")


if __name__ == "__main__":
    main()
