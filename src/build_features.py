from pathlib import Path
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "player_games.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
CLEAN_PATH = PROCESSED_DIR / "player_games_clean.csv"
MODELING_PATH = PROCESSED_DIR / "modeling_table.csv"


KEEP_COLS = [
    "SEASON_YEAR", "SEASON", "SEASON_TYPE",
    "GAME_ID", "GAME_DATE",
    "PLAYER_ID", "PLAYER_NAME",
    "TEAM_ID", "TEAM_ABBREVIATION", "TEAM_NAME",
    "MATCHUP", "WL", "MIN",
    "FGA", "FTA", "FTM", "PFD", "PF", "TOV", "PTS"
]


def shifted_rolling_mean(series, window, min_periods=3):
    return series.shift(1).rolling(window=window, min_periods=min_periods).mean()


def clean_player_games(df):
    df = df[KEEP_COLS].copy()

    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    df["HOME"] = df["MATCHUP"].str.contains(" vs. ").astype(int)
    df["OPP"] = df["MATCHUP"].str.extract(r"(?:vs\.|@) ([A-Z]{3})")

    numeric_cols = ["MIN", "FGA", "FTA", "FTM", "PFD", "PF", "TOV", "PTS"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["GAME_ID", "GAME_DATE", "PLAYER_ID", "TEAM_ABBREVIATION", "OPP"])
    df = df[df["MIN"] > 0].copy()

    return df.sort_values(["GAME_DATE", "GAME_ID", "TEAM_ABBREVIATION", "PLAYER_ID"])


def build_player_features(df):
    df = df.sort_values(["PLAYER_ID", "GAME_DATE", "GAME_ID"]).copy()
    g = df.groupby("PLAYER_ID", group_keys=False)

    for window in [5, 10, 20]:
        df[f"player_fta_l{window}"] = g["FTA"].transform(lambda s: shifted_rolling_mean(s, window))
        df[f"player_pfd_l{window}"] = g["PFD"].transform(lambda s: shifted_rolling_mean(s, window))
        df[f"player_min_l{window}"] = g["MIN"].transform(lambda s: shifted_rolling_mean(s, window))
        df[f"player_fga_l{window}"] = g["FGA"].transform(lambda s: shifted_rolling_mean(s, window))
        df[f"player_pf_l{window}"] = g["PF"].transform(lambda s: shifted_rolling_mean(s, window))

    df["player_fta_per_min_l10"] = df["player_fta_l10"] / df["player_min_l10"]
    df["player_pfd_per_min_l10"] = df["player_pfd_l10"] / df["player_min_l10"]
    df["player_fga_per_min_l10"] = df["player_fga_l10"] / df["player_min_l10"]

    return df


def build_opponent_features(df):
    team_games = (
        df.groupby(["GAME_ID", "GAME_DATE", "TEAM_ABBREVIATION", "OPP"], as_index=False)
        .agg(
            team_fta=("FTA", "sum"),
            team_pf=("PF", "sum"),
            team_fga=("FGA", "sum"),
            team_pts=("PTS", "sum"),
        )
    )

    # Convert team rows into opponent rows inside the same game.
    opp_allowed = team_games[["GAME_ID", "TEAM_ABBREVIATION", "team_fta", "team_pf"]].copy()
    opp_allowed = opp_allowed.rename(
        columns={
            "TEAM_ABBREVIATION": "OPP",
            "team_fta": "opp_fta_allowed_game",
            "team_pf": "opp_pf_committed_game",
        }
    )

    team_games = team_games.merge(opp_allowed, on=["GAME_ID", "OPP"], how="left")
    team_games = team_games.sort_values(["TEAM_ABBREVIATION", "GAME_DATE", "GAME_ID"])

    g = team_games.groupby("TEAM_ABBREVIATION", group_keys=False)

    for window in [10, 20]:
        team_games[f"team_pf_l{window}"] = g["team_pf"].transform(lambda s: shifted_rolling_mean(s, window))
        team_games[f"team_fta_allowed_l{window}"] = g["opp_fta_allowed_game"].transform(lambda s: shifted_rolling_mean(s, window))

    opponent_features = team_games[
        [
            "GAME_ID",
            "TEAM_ABBREVIATION",
            "team_pf_l10",
            "team_fta_allowed_l10",
            "team_pf_l20",
            "team_fta_allowed_l20",
        ]
    ].copy()

    opponent_features = opponent_features.rename(
        columns={
            "TEAM_ABBREVIATION": "OPP",
            "team_pf_l10": "opp_pf_l10",
            "team_fta_allowed_l10": "opp_fta_allowed_l10",
            "team_pf_l20": "opp_pf_l20",
            "team_fta_allowed_l20": "opp_fta_allowed_l20",
        }
    )

    return opponent_features


def add_synthetic_lines(df):
    df = df.copy()

    df["synthetic_line"] = np.floor(df["player_fta_l20"]) + 0.5
    df["over_result"] = (df["FTA"] > df["synthetic_line"]).astype(int)
    df["fta_vs_line"] = df["FTA"] - df["synthetic_line"]
    df["baseline_edge"] = df["player_fta_l10"] - df["synthetic_line"]

    return df


def add_matchup_score(df):
    df = df.copy()

    components = [
        "player_pfd_per_min_l10",
        "player_min_l10",
        "opp_pf_l10",
        "opp_fta_allowed_l10",
    ]

    for col in components:
        df[f"z_{col}"] = (df[col] - df[col].mean()) / df[col].std()

    df["simple_matchup_risk"] = df[[f"z_{col}" for col in components]].mean(axis=1)
    return df


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Missing {RAW_PATH}. Run scripts/01_pull_data.py first.")

    raw = pd.read_csv(RAW_PATH)
    clean = clean_player_games(raw)
    clean.to_csv(CLEAN_PATH, index=False)

    player_features = build_player_features(clean)
    opponent_features = build_opponent_features(clean)

    modeling = player_features.merge(opponent_features, on=["GAME_ID", "OPP"], how="left")
    modeling = add_synthetic_lines(modeling)
    modeling = add_matchup_score(modeling)

    required = [
        "FTA",
        "synthetic_line",
        "over_result",
        "player_fta_l10",
        "player_fta_l20",
        "player_pfd_l10",
        "player_min_l10",
        "player_fga_l10",
        "player_fta_per_min_l10",
        "player_pfd_per_min_l10",
        "opp_pf_l10",
        "opp_fta_allowed_l10",
        "simple_matchup_risk",
    ]

    modeling = modeling.dropna(subset=required).copy()
    modeling = modeling.sort_values(["GAME_DATE", "GAME_ID", "PLAYER_NAME"])

    modeling.to_csv(MODELING_PATH, index=False)

    print(f"Saved clean player games to {CLEAN_PATH}")
    print(f"Saved modeling table to {MODELING_PATH}")
    print(f"Modeling table shape: {modeling.shape}")
    print(modeling[[
        "GAME_DATE", "PLAYER_NAME", "MATCHUP", "MIN", "FTA", "PFD",
        "synthetic_line", "over_result",
        "player_fta_l10", "player_pfd_l10",
        "player_min_l10", "opp_pf_l10",
        "opp_fta_allowed_l10", "simple_matchup_risk"
    ]].head(20))


if __name__ == "__main__":
    main()
