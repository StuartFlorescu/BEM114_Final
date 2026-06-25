"""PROJECT 2 (alpha scanner): pull historical multi-book moneyline (h2h) odds.

Captures EVERY book's price (US soft books + Pinnacle as the sharp anchor, which lives
in the `eu` region) at two snapshots per game day so we can:
  - compare soft-book prices to the sharp (Pinnacle) no-vig probability  -> +EV detection
  - compare an early price to a later price                              -> Closing Line Value

h2h is a featured market -> bulk endpoint (all games per call), available back to 2020.
Cost = 10 x markets x regions = 10 x 1 x 2 (us,eu) = 20 credits per snapshot.

Output: data/raw/alpha_h2h_multibook.csv
  date, game, home_team, away_team, snapshot_label, snapshot_time_utc,
  book, team, american_odds, event_id, commence_time
"""
from pathlib import Path
import argparse
import os
import time
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = RAW / "alpha_h2h_multibook.csv"

SPORT = "basketball_nba"
REGIONS = "us,eu"          # us = soft books; eu = Pinnacle (sharp)
MARKET = "h2h"
ODDS_FORMAT = "american"
BASE = "https://api.the-odds-api.com/v4/historical/sports"


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


def get_bulk(key, iso):
    r = requests.get(f"{BASE}/{SPORT}/odds", params={
        "apiKey": key, "regions": REGIONS, "markets": MARKET,
        "oddsFormat": ODDS_FORMAT, "date": iso})
    print(f"  [{iso}] status={r.status_code} remaining={r.headers.get('x-requests-remaining')} "
          f"cost={r.headers.get('x-requests-last')}")
    r.raise_for_status()
    return r.json()


def flatten(label, iso, event):
    home, away, ct = event.get("home_team"), event.get("away_team"), event.get("commence_time")
    out = []
    for bk in event.get("bookmakers", []):
        for mk in bk.get("markets", []):
            if mk.get("key") != MARKET:
                continue
            for o in mk.get("outcomes", []):
                out.append({
                    "date": et_date(ct), "game": f"{away} @ {home}",
                    "home_team": home, "away_team": away,
                    "snapshot_label": label, "snapshot_time_utc": iso,
                    "book": bk.get("key"), "team": o.get("name"),
                    "american_odds": o.get("price"),
                    "event_id": event.get("id"), "commence_time": ct,
                })
    return out


def daterange(s, e):
    cur = s
    while cur <= e:
        yield cur
        cur += pd.Timedelta(days=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--early-hour-utc", type=int, default=16, help="~noon ET pre-slate snapshot")
    ap.add_argument("--late-hour-utc", type=int, default=23, help="~6pm ET near-tip snapshot (CLV ref)")
    ap.add_argument("--max-credits", type=int, default=15000)
    args = ap.parse_args()

    key = get_key()
    start, end = pd.Timestamp(args.start), pd.Timestamp(args.end)
    sd, ed = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    snaps = [("early", args.early_hour_utc), ("close", args.late_hour_utc)]

    rows, credits = [], 0
    for day in daterange(start, end):
        for label, hh in snaps:
            if credits >= args.max_credits:
                print("Hit --max-credits; stopping."); break
            iso = f"{day.strftime('%Y-%m-%d')}T{hh:02d}:00:00Z"
            try:
                payload = get_bulk(key, iso)
            except requests.HTTPError as ex:
                print(f"  failed {iso}: {ex}"); continue
            credits += 20
            n = 0
            seen_day = set()
            for ev in (payload.get("data") or []):
                d = et_date(ev.get("commence_time"))
                if d is None or d < sd or d > ed:
                    continue
                key_g = ev.get("id")
                if key_g in seen_day:
                    continue
                seen_day.add(key_g)
                r = flatten(label, iso, ev)
                rows.extend(r); n += len(r)
            print(f"  {day.strftime('%Y-%m-%d')} {label}: {len(seen_day)} games, {n} book-rows")
            time.sleep(0.2)

    if rows:
        new = pd.DataFrame(rows)
        if OUT.exists():
            new = pd.concat([pd.read_csv(OUT), new], ignore_index=True)
        new = new.drop_duplicates(subset=["event_id", "snapshot_time_utc", "book", "team"])
        new.to_csv(OUT, index=False)
        print(f"\nSaved {len(new):,} rows to {OUT}")
        print(f"Books seen: {sorted(pd.DataFrame(rows)['book'].unique())}")
    print(f"Est credits this run: ~{credits}")


if __name__ == "__main__":
    main()
