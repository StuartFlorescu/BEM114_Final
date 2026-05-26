from pathlib import Path
import pandas as pd
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "settings.yaml"

def load_settings():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def scoring_role_bucket(x):
    if pd.isna(x):
        return "unknown"
    if x < 8:
        return "low_usage"
    if x < 14:
        return "rotation"
    if x < 21:
        return "starter"
    return "star"

def add_defense_matchup_features():
    settings = load_settings()
    paths = settings["paths"]

    modeling_path = ROOT / paths["modeling_table"]
    current_dataset_path = ROOT / paths["modeling_dataset"]
    output_path = ROOT / "data/processed/player_points_modeling_dataset_with_matchups.csv"

    modeling = pd.read_csv(modeling_path)
    dataset = pd.read_csv(current_dataset_path)

    modeling["date"] = pd.to_datetime(modeling["GAME_DATE"]).dt.date.astype(str)
    modeling["scoring_role"] = modeling["player_pts_l10"].apply(scoring_role_bucket)

    # OPP is the defense faced by this player.
    daily_role_allowed = (
        modeling
        .groupby(["date", "OPP", "scoring_role"], as_index=False)
        .agg(
            def_role_pts_allowed_daily=("PTS", "mean"),
            def_role_fta_allowed_daily=("FTA", "mean"),
            def_role_pfd_allowed_daily=("PFD", "mean"),
            def_role_players_faced_daily=("PLAYER_ID", "count"),
        )
        .sort_values(["OPP", "scoring_role", "date"])
    )

    # Rolling defensive allowance versus similar scorer roles.
    for col in [
        "def_role_pts_allowed_daily",
        "def_role_fta_allowed_daily",
        "def_role_pfd_allowed_daily",
        "def_role_players_faced_daily",
    ]:
        daily_role_allowed[f"{col.replace('_daily', '')}_l10"] = (
            daily_role_allowed
            .groupby(["OPP", "scoring_role"])[col]
            .transform(lambda s: s.shift(1).rolling(10, min_periods=3).mean())
        )

        daily_role_allowed[f"{col.replace('_daily', '')}_l20"] = (
            daily_role_allowed
            .groupby(["OPP", "scoring_role"])[col]
            .transform(lambda s: s.shift(1).rolling(20, min_periods=5).mean())
        )

    keep_cols = [
        "date",
        "OPP",
        "scoring_role",
        "def_role_pts_allowed_l10",
        "def_role_fta_allowed_l10",
        "def_role_pfd_allowed_l10",
        "def_role_players_faced_l10",
        "def_role_pts_allowed_l20",
        "def_role_fta_allowed_l20",
        "def_role_pfd_allowed_l20",
        "def_role_players_faced_l20",
    ]

    defense_features = daily_role_allowed[keep_cols].copy()

    # League fallback averages by role, used when a team-role combo has sparse history.
    fallback = (
        modeling
        .groupby("scoring_role", as_index=False)
        .agg(
            fallback_pts=("PTS", "mean"),
            fallback_fta=("FTA", "mean"),
            fallback_pfd=("PFD", "mean"),
        )
    )

    dataset["scoring_role"] = dataset["player_pts_l10"].apply(scoring_role_bucket)

    merged = dataset.merge(
        defense_features,
        on=["date", "OPP", "scoring_role"],
        how="left",
    )

    merged = merged.merge(fallback, on="scoring_role", how="left")

    for window in ["l10", "l20"]:
        merged[f"def_role_pts_allowed_{window}"] = merged[f"def_role_pts_allowed_{window}"].fillna(merged["fallback_pts"])
        merged[f"def_role_fta_allowed_{window}"] = merged[f"def_role_fta_allowed_{window}"].fillna(merged["fallback_fta"])
        merged[f"def_role_pfd_allowed_{window}"] = merged[f"def_role_pfd_allowed_{window}"].fillna(merged["fallback_pfd"])
        merged[f"def_role_players_faced_{window}"] = merged[f"def_role_players_faced_{window}"].fillna(0)

    # Matchup deltas: positive means this defense allows more than the player's own recent baseline.
    merged["matchup_pts_edge_l10"] = merged["def_role_pts_allowed_l10"] - merged["player_pts_l10"]
    merged["matchup_fta_edge_l10"] = merged["def_role_fta_allowed_l10"] - merged["player_fta_l10"]
    merged["matchup_pfd_edge_l10"] = merged["def_role_pfd_allowed_l10"] - merged["player_pfd_l10"]

    merged["matchup_pts_edge_l20"] = merged["def_role_pts_allowed_l20"] - merged["player_pts_l20"]
    merged["matchup_fta_edge_l20"] = merged["def_role_fta_allowed_l20"] - merged["player_fta_l20"]
    merged["matchup_pfd_edge_l20"] = merged["def_role_pfd_allowed_l20"] - merged["player_pfd_l20"]

    merged = merged.drop(columns=["fallback_pts", "fallback_fta", "fallback_pfd"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)

    print("================ DEFENSE MATCHUP FEATURES ADDED ================")
    print(f"Input dataset:  {current_dataset_path}")
    print(f"Output dataset: {output_path}")
    print(f"Rows: {len(merged):,}")
    print()
    print("New matchup columns:")
    new_cols = [c for c in merged.columns if c.startswith("def_role_") or c.startswith("matchup_") or c == "scoring_role"]
    print(new_cols)
    print()
    print("Scoring role counts:")
    print(merged["scoring_role"].value_counts().to_string())

if __name__ == "__main__":
    add_defense_matchup_features()
