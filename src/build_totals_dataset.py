"""Build the game-totals test dataset: market total line/odds + actual total + crew features.

Joins:
  - actual game totals (sum of both teams' PTS)            <- player_games_clean.csv
  - referee crew rolling features (per game)              <- referee_games.csv via build_crew_features
  - DraftKings game-total line + over/under odds          <- historical_game_totals_odds.csv

Output: data/processed/game_totals_dataset.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd

from src.add_referee_features import build_game_stats, build_crew_features, TEAM_NAME_TO_ABBR
from src.build_features import american_to_prob

ROOT = Path(__file__).resolve().parents[1]
PLAYER_GAMES = ROOT / "data/processed/player_games_clean.csv"
REFEREES = ROOT / "data/raw/referee_games.csv"
TOTALS_ODDS = ROOT / "data/raw/historical_game_totals_odds.csv"
OUT = ROOT / "data/processed/game_totals_dataset.csv"


def main():
    pg = pd.read_csv(PLAYER_GAMES)
    if "date" not in pg.columns:
        pg["date"] = pd.to_datetime(pg["GAME_DATE"]).dt.date.astype(str)
    refs = pd.read_csv(REFEREES)

    game_stats = build_game_stats(pg)                 # per-game totals + home/away abbr
    crew = build_crew_features(refs, game_stats)      # per-game crew rolling features + z-scores

    # actual outcomes per game (date, away_abbr, home_abbr, total_pts, ...)
    outcomes = game_stats[["date", "away_abbr", "home_abbr", "total_pts",
                           "total_fta", "total_pf"]].copy()

    # crew features merged onto outcomes
    g = outcomes.merge(crew, on=["date", "away_abbr", "home_abbr"], how="inner")

    # market totals odds
    odds = pd.read_csv(TOTALS_ODDS)
    odds["away_abbr"] = odds["away_team"].map(TEAM_NAME_TO_ABBR)
    odds["home_abbr"] = odds["home_team"].map(TEAM_NAME_TO_ABBR)
    odds = odds.dropna(subset=["away_abbr", "home_abbr", "total_line"])
    # one row per game (closest-to-tip snapshot = latest)
    odds = odds.sort_values("snapshot_time_utc").drop_duplicates(
        subset=["date", "away_abbr", "home_abbr"], keep="last")
    odds = odds[["date", "away_abbr", "home_abbr", "total_line", "over_odds", "under_odds"]]

    df = g.merge(odds, on=["date", "away_abbr", "home_abbr"], how="inner")

    # outcome + no-vig market prob of OVER
    df["went_over"] = (df["total_pts"] > df["total_line"]).astype("Int64")
    df["push"] = (df["total_pts"] == df["total_line"]).astype("Int64")
    df["raw_p_over"] = df["over_odds"].apply(american_to_prob)
    df["raw_p_under"] = df["under_odds"].apply(american_to_prob)
    df["market_prob_over_novig"] = df["raw_p_over"] / (df["raw_p_over"] + df["raw_p_under"])

    df = df.sort_values("date").reset_index(drop=True)
    df.to_csv(OUT, index=False)

    print(f"Wrote {OUT}")
    print(f"Games: {len(df):,} | dates {df['date'].min()} -> {df['date'].max()}")
    print(f"Over rate (actual): {df['went_over'].mean():.3f} | push rate: {df['push'].mean():.3f}")
    print(f"Avg market line: {df['total_line'].mean():.1f} | avg actual total: {df['total_pts'].mean():.1f}")
    print(f"crew_total_pts_l20 present: {df['crew_total_pts_l20'].notna().mean():.1%}")


if __name__ == "__main__":
    main()
