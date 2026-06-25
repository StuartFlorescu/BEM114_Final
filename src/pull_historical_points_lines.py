"""Backfill historical DraftKings player-points props from The Odds API.

The original puller (src/pull_real_points_lines.py) only hit the *live* endpoint,
so the dataset only covers days the team happened to run it (2025-12-12 .. 2026-04-10).

This script uses The Odds API HISTORICAL endpoints to backfill arbitrary past dates:

    /v4/historical/sports/{sport}/events?date=...
    /v4/historical/sports/{sport}/events/{eventId}/odds?date=...&markets=player_points

Historical access requires a PAID Odds API plan. Player-props are per-event, so
cost = (events on that day) credits per snapshot. We take ONE snapshot per game day
by default to keep credit burn bounded, and print remaining credits after every call.

Usage:
    ODDS_API_KEY=... python scripts/05b_pull_historical_points_lines.py \
        --start 2025-10-21 --end 2025-12-11 --snapshot-hour-utc 23

Output (appends, dedupes) -> data/raw/historical_player_points_odds.csv
with columns matching the existing pipeline: date, player, game, side, line, american_odds
plus provenance columns (bookmaker_key, snapshot_time_utc, event_id, commence_time).
"""

from pathlib import Path
import argparse
import os
import sys
import time

import requests
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT_PATH = RAW_DIR / "historical_player_points_odds.csv"

SPORT = "basketball_nba"
REGIONS = "us"
MARKET = "player_points"
ODDS_FORMAT = "american"
BASE = "https://api.the-odds-api.com/v4/historical/sports"

# Restrict to one book by default so the output matches the existing DraftKings dataset.
BOOKMAKER_FILTER = "draftkings"


def load_env_local():
    """Load KEY=VALUE pairs from .env.local without external deps."""
    env_file = ROOT / ".env.local"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_api_key():
    load_env_local()
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing ODDS_API_KEY. Put it in .env.local (ODDS_API_KEY=...) "
            "or export it before running."
        )
    return api_key


def _log_credits(resp, label):
    print(
        f"  [{label}] status={resp.status_code} "
        f"remaining={resp.headers.get('x-requests-remaining')} "
        f"used={resp.headers.get('x-requests-used')} "
        f"last_cost={resp.headers.get('x-requests-last')}"
    )


def get_historical_events(api_key, iso_date):
    url = f"{BASE}/{SPORT}/events"
    resp = requests.get(url, params={"apiKey": api_key, "date": iso_date})
    _log_credits(resp, "events")
    resp.raise_for_status()
    return resp.json()  # {timestamp, previous_timestamp, next_timestamp, data: [...]}


def get_historical_event_odds(api_key, event_id, iso_date):
    url = f"{BASE}/{SPORT}/events/{event_id}/odds"
    params = {
        "apiKey": api_key,
        "regions": REGIONS,
        "markets": MARKET,
        "oddsFormat": ODDS_FORMAT,
        "date": iso_date,
    }
    resp = requests.get(url, params=params)
    _log_credits(resp, "odds")
    resp.raise_for_status()
    return resp.json()  # {timestamp, ..., data: {event...}}


def et_date(commence_time):
    """NBA game date in US/Eastern (matches player_games.csv & existing odds file)."""
    if not commence_time:
        return None
    return pd.Timestamp(commence_time).tz_convert("America/New_York").strftime("%Y-%m-%d")


def odds_snapshot_iso(commence_time, pre_tip_minutes):
    """UTC ISO timestamp `pre_tip_minutes` before tip-off, for the historical odds query."""
    ts = pd.Timestamp(commence_time) - pd.Timedelta(minutes=pre_tip_minutes)
    return ts.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def flatten_event(snapshot_iso, event):
    rows = []
    event_id = event.get("id")
    commence_time = event.get("commence_time")
    home_team = event.get("home_team")
    away_team = event.get("away_team")
    game = f"{away_team} @ {home_team}"

    for book in event.get("bookmakers", []):
        bookmaker_key = book.get("key")
        if BOOKMAKER_FILTER and bookmaker_key != BOOKMAKER_FILTER:
            continue
        for market in book.get("markets", []):
            if market.get("key") != MARKET:
                continue
            for outcome in market.get("outcomes", []):
                rows.append({
                    "date": et_date(commence_time),
                    "player": outcome.get("description"),
                    "game": game,
                    "side": outcome.get("name"),
                    "line": outcome.get("point"),
                    "american_odds": outcome.get("price"),
                    "bookmaker_key": bookmaker_key,
                    "snapshot_time_utc": snapshot_iso,
                    "event_id": event_id,
                    "commence_time": commence_time,
                })
    return rows


def daterange(start, end):
    cur = start
    while cur <= end:
        yield cur
        cur += pd.Timedelta(days=1)


def save(df):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if OUT_PATH.exists():
        old = pd.read_csv(OUT_PATH)
        df = pd.concat([old, df], ignore_index=True)
    df = df.drop_duplicates(
        subset=["snapshot_time_utc", "event_id", "bookmaker_key",
                "player", "side", "line", "american_odds"]
    )
    df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved {len(df):,} total rows to {OUT_PATH}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", required=True, help="first game date YYYY-MM-DD (ET)")
    ap.add_argument("--end", required=True, help="last game date YYYY-MM-DD (ET)")
    ap.add_argument("--events-hour-utc", type=int, default=12,
                    help="UTC hour to query each day's events list (default 12 = 7am ET, "
                         "before any tip so the whole slate is still 'upcoming')")
    ap.add_argument("--pre-tip-minutes", type=int, default=30,
                    help="snapshot each game this many minutes before its tip-off")
    ap.add_argument("--max-credits", type=int, default=400,
                    help="abort once estimated credits used reaches this (safety ceiling)")
    ap.add_argument("--dry-run", action="store_true",
                    help="only discover/list games (events-list calls); do not fetch odds")
    args = ap.parse_args()

    api_key = get_api_key()
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)
    start_d, end_d = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    all_rows = []
    seen = set()
    events_calls = 0
    odds_calls = 0

    def est_credits():
        return events_calls + odds_calls * 10

    for day in daterange(start, end):
        iso = f"{day.strftime('%Y-%m-%d')}T{args.events_hour_utc:02d}:00:00Z"
        try:
            payload = get_historical_events(api_key, iso)
        except requests.HTTPError as e:
            print(f"  events list failed for {iso}: {e}")
            continue
        events_calls += 1

        # keep only NEW, in-range games (dedup across overlapping daily windows)
        new_events = []
        for e in (payload.get("data") or []):
            eid, ct = e.get("id"), e.get("commence_time")
            if not eid or eid in seen:
                continue
            d = et_date(ct)
            if d is None or d < start_d or d > end_d:
                continue
            seen.add(eid)
            new_events.append(e)
        print(f"=== {day.strftime('%Y-%m-%d')}: {len(new_events)} new games (cumulative {len(seen)}) ===")

        if args.dry_run:
            continue

        for ev in new_events:
            if est_credits() >= args.max_credits:
                print(f"\nHit --max-credits={args.max_credits}; stopping early.")
                if all_rows:
                    save(pd.DataFrame(all_rows))
                print(f"Estimated credits used: ~{est_credits()}")
                return
            odds_iso = odds_snapshot_iso(ev["commence_time"], args.pre_tip_minutes)
            try:
                odds = get_historical_event_odds(api_key, ev["id"], odds_iso)
            except requests.HTTPError as e:
                print(f"  odds failed for {ev.get('id')}: {e}")
                continue
            odds_calls += 1
            rows = flatten_event(odds_iso, odds.get("data") or {})
            print(f"    {et_date(ev.get('commence_time'))} "
                  f"{ev.get('away_team')} @ {ev.get('home_team')}: "
                  f"{len(rows)} DK rows (tip {ev.get('commence_time')}, snap {odds_iso})")
            all_rows.extend(rows)
            time.sleep(0.25)

    if all_rows:
        save(pd.DataFrame(all_rows))
    else:
        print("\nNo rows collected.")
    print(f"\nGames pulled: {odds_calls} | events-list calls: {events_calls}")
    print(f"Estimated credits used this run: ~{est_credits()} "
          f"(events {events_calls} + odds {odds_calls}x10)")


if __name__ == "__main__":
    main()
