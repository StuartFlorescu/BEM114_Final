from pathlib import Path
import os
import requests
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

CURRENT_OUT = RAW_DIR / "real_player_points_lines_current.csv"
HISTORY_OUT = RAW_DIR / "real_player_points_lines_history.csv"

SPORT = "basketball_nba"
REGIONS = "us"
MARKET = "player_points"
ODDS_FORMAT = "american"


def get_api_key():
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing ODDS_API_KEY. Run with: ODDS_API_KEY='your_key' python scripts/05_pull_real_points_lines.py"
        )
    return api_key


def get_events(api_key):
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events"
    response = requests.get(url, params={"apiKey": api_key})

    print("Events status:", response.status_code)
    print("Requests remaining:", response.headers.get("x-requests-remaining"))
    print("Requests used:", response.headers.get("x-requests-used"))

    response.raise_for_status()
    return response.json()


def get_event_odds(api_key, event_id):
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{event_id}/odds"

    params = {
        "apiKey": api_key,
        "regions": REGIONS,
        "markets": MARKET,
        "oddsFormat": ODDS_FORMAT,
    }

    response = requests.get(url, params=params)

    print("Odds status:", response.status_code)
    print("Requests remaining:", response.headers.get("x-requests-remaining"))
    print("Requests used:", response.headers.get("x-requests-used"))

    response.raise_for_status()
    return response.json()


def flatten_event(data):
    rows = []

    event_id = data.get("id")
    commence_time = data.get("commence_time")
    home_team = data.get("home_team")
    away_team = data.get("away_team")

    for book in data.get("bookmakers", []):
        bookmaker_key = book.get("key")
        bookmaker_title = book.get("title")
        bookmaker_update = book.get("last_update")

        for market in book.get("markets", []):
            if market.get("key") != MARKET:
                continue

            market_update = market.get("last_update")

            for outcome in market.get("outcomes", []):
                rows.append({
                    "snapshot_time_utc": pd.Timestamp.utcnow(),
                    "event_id": event_id,
                    "commence_time": commence_time,
                    "home_team": home_team,
                    "away_team": away_team,
                    "bookmaker_key": bookmaker_key,
                    "bookmaker_title": bookmaker_title,
                    "bookmaker_update": bookmaker_update,
                    "market_key": market.get("key"),
                    "market_update": market_update,
                    "player_name": outcome.get("description"),
                    "side": outcome.get("name"),
                    "line": outcome.get("point"),
                    "american_odds": outcome.get("price"),
                })

    return rows


def save_outputs(df):
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(CURRENT_OUT, index=False)
    print(f"Saved current snapshot to {CURRENT_OUT}")

    if HISTORY_OUT.exists():
        old = pd.read_csv(HISTORY_OUT)
        combined = pd.concat([old, df], ignore_index=True)
    else:
        combined = df.copy()

    combined = combined.drop_duplicates(
        subset=[
            "snapshot_time_utc",
            "event_id",
            "bookmaker_key",
            "market_key",
            "player_name",
            "side",
            "line",
            "american_odds",
        ]
    )

    combined.to_csv(HISTORY_OUT, index=False)
    print(f"Saved history file to {HISTORY_OUT}")


def main():
    api_key = get_api_key()
    events = get_events(api_key)

    print(f"\nFound {len(events)} NBA events")

    all_rows = []

    for event in events:
        print()
        print("=" * 80)
        print(f"{event.get('away_team')} at {event.get('home_team')}")
        print("event_id:", event.get("id"))
        print("commence_time:", event.get("commence_time"))

        data = get_event_odds(api_key, event["id"])
        rows = flatten_event(data)

        print(f"Player-points rows found: {len(rows)}")
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)

    print()
    print("=" * 80)
    print("Total rows found:", len(df))

    if df.empty:
        print("No player-points lines found.")
        return

    save_outputs(df)

    print()
    print("Preview:")
    print(df.head(40).to_string(index=False))


if __name__ == "__main__":
    main()
