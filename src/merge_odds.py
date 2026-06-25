"""Merge the backfilled historical DraftKings player-points odds with the
existing 2025-26 live-pulled odds into one market file for the pipeline.

- Existing file: data/raw/nba_2025_26_draftkings_props_with_odds.csv  (Dec'25-Apr'26)
- Historical backfill: data/raw/historical_player_points_odds.csv      (2023-24, 2024-25, Oct-Dec'25)

The historical file can carry >1 snapshot per prop (from tip-30/-180/-360 recovery
passes). We collapse to ONE row per (date, player, game, side) keeping the snapshot
closest to tip-off (latest snapshot_time_utc = the most closing-line-like price),
which also resolves the handful of intra-game line moves. No date overlap exists
between the two files, so the rest is a straight concatenation.

Output: data/raw/draftkings_props_with_odds_all.csv  (6-col schema, drop-in for build_features)
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

EXISTING = RAW / "nba_2025_26_draftkings_props_with_odds.csv"
HISTORICAL = RAW / "historical_player_points_odds.csv"
OUT = RAW / "draftkings_props_with_odds_all.csv"

CORE_COLS = ["date", "player", "game", "side", "line", "american_odds"]
KEY = ["date", "player", "game", "side"]


def dedup_to_closing(hist):
    """One row per prop, keeping the snapshot closest to tip-off."""
    before = len(hist)
    hist = hist.sort_values("snapshot_time_utc")
    hist = hist.drop_duplicates(subset=KEY, keep="last")
    print(f"  historical: {before:,} -> {len(hist):,} rows after collapsing to one snapshot/prop")
    return hist


def main():
    existing = pd.read_csv(EXISTING)
    historical = pd.read_csv(HISTORICAL)

    overlap = set(existing["date"]) & set(historical["date"])
    if overlap:
        raise SystemExit(f"Unexpected date overlap between files: {sorted(overlap)[:5]} ...")

    historical = dedup_to_closing(historical)[CORE_COLS]
    existing = existing[CORE_COLS]

    merged = pd.concat([historical, existing], ignore_index=True)
    merged = merged.sort_values(["date", "game", "player", "side"]).reset_index(drop=True)

    merged.to_csv(OUT, index=False)

    pg = merged.groupby(["date", "player", "game"]).ngroups
    print(f"\nWrote {OUT}")
    print(f"Rows: {len(merged):,} | player-games: {pg:,}")
    print(f"Date range: {merged['date'].min()} -> {merged['date'].max()}")
    print("Side balance:", merged["side"].value_counts().to_dict())


if __name__ == "__main__":
    main()
