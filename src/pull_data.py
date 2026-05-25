from pathlib import Path
import time
import yaml
import pandas as pd
from nba_api.stats.endpoints import playergamelogs


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "settings.yaml"
RAW_DIR = ROOT / "data" / "raw"
OUTPUT_PATH = RAW_DIR / "player_games.csv"


def load_settings():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def pull_player_logs(season, season_type):
    print(f"Pulling {season} - {season_type}")

    logs = playergamelogs.PlayerGameLogs(
        season_nullable=season,
        season_type_nullable=season_type,
        league_id_nullable="00"
    )

    df = logs.get_data_frames()[0]
    df["SEASON"] = season
    df["SEASON_TYPE"] = season_type
    return df


def main():
    settings = load_settings()
    seasons = settings["seasons"]
    season_types = settings["season_types"]

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    frames = []

    for season in seasons:
        for season_type in season_types:
            try:
                df = pull_player_logs(season, season_type)
                frames.append(df)
                time.sleep(1.0)
            except Exception as e:
                print(f"Failed: {season} - {season_type}")
                print(e)

    if not frames:
        raise RuntimeError("No player-game data was pulled.")

    player_games = pd.concat(frames, ignore_index=True)
    player_games.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(player_games):,} rows to {OUTPUT_PATH}")
    print("Columns:")
    print(list(player_games.columns))


if __name__ == "__main__":
    main()
