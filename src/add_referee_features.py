from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/settings.yaml"

TEAM_NAME_TO_ABBR = {
    "Atlanta Hawks": "ATL",
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL",
    "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW",
    "Houston Rockets": "HOU",
    "Indiana Pacers": "IND",
    "LA Clippers": "LAC",
    "Los Angeles Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}

def load_settings():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def build_game_stats(player_games):
    games = player_games.copy()
    games["date"] = pd.to_datetime(games["GAME_DATE"]).dt.date.astype(str)
    games["HOME"] = games["HOME"].astype(int)

    game_keys = ["GAME_ID", "date"]

    totals = (
        games
        .groupby(game_keys, as_index=False)
        .agg(
            total_pts=("PTS", "sum"),
            total_fta=("FTA", "sum"),
            total_pf=("PF", "sum"),
            total_pfd=("PFD", "sum"),
            n_players=("PLAYER_ID", "count"),
        )
    )

    home = (
        games[games["HOME"] == 1]
        .groupby(game_keys, as_index=False)
        .agg(
            home_abbr=("TEAM_ABBREVIATION", "first"),
            home_pts=("PTS", "sum"),
            home_fta=("FTA", "sum"),
            home_pf=("PF", "sum"),
            home_pfd=("PFD", "sum"),
        )
    )

    away = (
        games[games["HOME"] == 0]
        .groupby(game_keys, as_index=False)
        .agg(
            away_abbr=("TEAM_ABBREVIATION", "first"),
            away_pts=("PTS", "sum"),
            away_fta=("FTA", "sum"),
            away_pf=("PF", "sum"),
            away_pfd=("PFD", "sum"),
        )
    )

    stats = totals.merge(home, on=game_keys, how="inner").merge(away, on=game_keys, how="inner")

    stats["home_fta_edge"] = stats["home_fta"] - stats["away_fta"]
    stats["home_pf_edge"] = stats["home_pf"] - stats["away_pf"]
    stats["home_pts_edge"] = stats["home_pts"] - stats["away_pts"]

    return stats

def build_crew_features(referees, game_stats):
    refs = referees.copy()
    refs["date"] = pd.to_datetime(refs["game_date"]).dt.date.astype(str)
    refs["away_abbr"] = refs["visitor"].map(TEAM_NAME_TO_ABBR)
    refs["home_abbr"] = refs["home"].map(TEAM_NAME_TO_ABBR)

    bad = refs[refs["away_abbr"].isna() | refs["home_abbr"].isna()]
    if len(bad):
        print("WARNING: unmapped referee team names:")
        print(bad[["game_date", "visitor", "home"]].drop_duplicates().head(20).to_string(index=False))

    ref_games = refs.merge(
        game_stats,
        on=["date", "away_abbr", "home_abbr"],
        how="left",
        indicator=True,
    )

    matched_games = ref_games["_merge"].eq("both").sum()
    print(f"Referee games: {len(ref_games):,}")
    print(f"Referee games matched to NBA stats by date/away/home: {matched_games:,} ({matched_games / len(ref_games):.1%})")

    ref_games = ref_games[ref_games["_merge"].eq("both")].drop(columns=["_merge"]).copy()

    official_cols = [c for c in ["official_1", "official_2", "official_3", "official_4"] if c in ref_games.columns]

    long_frames = []
    for c in official_cols:
        temp = ref_games.copy()
        temp["official"] = temp[c]
        temp = temp.dropna(subset=["official"])
        temp = temp[temp["official"].astype(str).str.strip() != ""]
        long_frames.append(temp)

    official_games = pd.concat(long_frames, ignore_index=True)
    official_games["official"] = official_games["official"].astype(str).str.strip()

    official_games = official_games.sort_values(["official", "date", "GAME_ID"])

    stat_cols = [
        "total_pts",
        "total_fta",
        "total_pf",
        "total_pfd",
        "home_fta_edge",
        "home_pf_edge",
        "home_pts_edge",
    ]

    for w in [20, 50]:
        for col in stat_cols:
            official_games[f"official_{col}_l{w}"] = (
                official_games
                .groupby("official")[col]
                .transform(lambda s: s.shift(1).rolling(w, min_periods=max(5, w // 4)).mean())
            )

    roll_cols = [c for c in official_games.columns if c.startswith("official_") and ("_l20" in c or "_l50" in c)]

    crew = (
        official_games
        .groupby(["date", "away_abbr", "home_abbr"], as_index=False)
        .agg(
            crew_n_officials=("official", "nunique"),
            **{c.replace("official_", "crew_"): (c, "mean") for c in roll_cols}
        )
    )

    # League baselines for z-scores and fallback.
    baselines = {
        "total_pts": game_stats["total_pts"].mean(),
        "total_fta": game_stats["total_fta"].mean(),
        "total_pf": game_stats["total_pf"].mean(),
        "total_pfd": game_stats["total_pfd"].mean(),
        "home_fta_edge": 0.0,
        "home_pf_edge": 0.0,
        "home_pts_edge": 0.0,
    }

    stds = {
        "total_pts": game_stats["total_pts"].std(ddof=1),
        "total_fta": game_stats["total_fta"].std(ddof=1),
        "total_pf": game_stats["total_pf"].std(ddof=1),
        "total_pfd": game_stats["total_pfd"].std(ddof=1),
        "home_fta_edge": game_stats["home_fta_edge"].std(ddof=1),
        "home_pf_edge": game_stats["home_pf_edge"].std(ddof=1),
        "home_pts_edge": game_stats["home_pts_edge"].std(ddof=1),
    }

    for w in [20, 50]:
        for stat in stat_cols:
            raw_col = f"crew_{stat}_l{w}"
            if raw_col not in crew.columns:
                continue

            crew[raw_col] = crew[raw_col].fillna(baselines[stat])
            z_col = f"crew_{stat}_z_l{w}"
            denom = stds[stat] if stds[stat] and stds[stat] > 0 else 1.0
            crew[z_col] = (crew[raw_col] - baselines[stat]) / denom

    crew["ref_contact_strictness_l20"] = (
        crew["crew_total_fta_z_l20"]
        + crew["crew_total_pf_z_l20"]
        + crew["crew_total_pfd_z_l20"]
    ) / 3.0

    crew["ref_scoring_environment_l20"] = crew["crew_total_pts_z_l20"]

    return crew

def add_referee_features():
    settings = load_settings()
    paths = settings["paths"]

    referee_path = ROOT / "data/raw/referee_games.csv"
    player_games_path = ROOT / paths.get("clean_player_games", "data/processed/player_games_clean.csv")
    dataset_path = ROOT / paths["modeling_dataset"]
    output_path = ROOT / "data/processed/player_points_modeling_dataset_with_referees.csv"

    if not referee_path.exists():
        raise FileNotFoundError("Missing data/raw/referee_games.csv")
    if not player_games_path.exists():
        raise FileNotFoundError(f"Missing {player_games_path}")
    if not dataset_path.exists():
        raise FileNotFoundError(f"Missing {dataset_path}")

    refs = pd.read_csv(referee_path)
    player_games = pd.read_csv(player_games_path)
    dataset = pd.read_csv(dataset_path)

    print("================ BUILDING REFEREE FEATURES ================")

    game_stats = build_game_stats(player_games)
    crew = build_crew_features(refs, game_stats)

    df = dataset.copy()
    if "date" not in df.columns:
        df["date"] = pd.to_datetime(df["GAME_DATE"]).dt.date.astype(str)
    else:
        df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)

    merged = df.merge(
        crew,
        on=["date", "away_abbr", "home_abbr"],
        how="left",
        indicator="ref_merge",
    )

    match_rate = merged["ref_merge"].eq("both").mean()
    print(f"Prop rows matched to referee features: {merged['ref_merge'].eq('both').sum():,} / {len(merged):,} ({match_rate:.1%})")
    merged = merged.drop(columns=["ref_merge"])

    # Fill missing ref features conservatively.
    ref_cols = [
        c for c in merged.columns
        if c.startswith("crew_") or c.startswith("ref_")
    ]

    for c in ref_cols:
        if c.endswith("_z_l20") or c.endswith("_z_l50") or c.startswith("ref_"):
            merged[c] = merged[c].fillna(0.0)
        elif c == "crew_n_officials":
            merged[c] = merged[c].fillna(0)
        else:
            merged[c] = merged[c].fillna(merged[c].median())

    # Player-side home/away ref bias.
    if "HOME" in merged.columns:
        home_flag = merged["HOME"].astype(int)
        merged["player_side_ref_fta_edge_l20"] = np.where(
            home_flag == 1,
            merged["crew_home_fta_edge_z_l20"],
            -merged["crew_home_fta_edge_z_l20"],
        )
        merged["player_side_ref_pf_edge_l20"] = np.where(
            home_flag == 1,
            merged["crew_home_pf_edge_z_l20"],
            -merged["crew_home_pf_edge_z_l20"],
        )
    else:
        merged["player_side_ref_fta_edge_l20"] = 0.0
        merged["player_side_ref_pf_edge_l20"] = 0.0

    # Referee x player contact interactions.
    if "player_pfd_per_min_l10" in merged.columns:
        merged["ref_contact_x_player_pfd_per_min_l10"] = (
            merged["ref_contact_strictness_l20"] * merged["player_pfd_per_min_l10"]
        )

    if "player_fta_per_min_l10" in merged.columns:
        merged["ref_contact_x_player_fta_per_min_l10"] = (
            merged["ref_contact_strictness_l20"] * merged["player_fta_per_min_l10"]
        )

    if "matchup_pfd_edge_l10" in merged.columns:
        merged["ref_contact_x_matchup_pfd_edge_l10"] = (
            merged["ref_contact_strictness_l20"] * merged["matchup_pfd_edge_l10"]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)

    print()
    print("================ REFEREE FEATURES ADDED ================")
    print(f"Input dataset:  {dataset_path}")
    print(f"Output dataset: {output_path}")
    print(f"Rows: {len(merged):,}")
    print()
    print("New referee columns:")
    new_cols = [
        c for c in merged.columns
        if c.startswith("crew_") or c.startswith("ref_") or c.startswith("player_side_ref_")
    ]
    print(new_cols)

if __name__ == "__main__":
    add_referee_features()
