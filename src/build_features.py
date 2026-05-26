from pathlib import Path
import re
import unicodedata
import pandas as pd
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "settings.yaml"

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

NAME_ALIASES = {
    "herb jones": "herbert jones",
    "moe wagner": "moritz wagner",
    "nicolas claxton": "nic claxton",
    "carlton carrington": "bub carrington",
}

def load_settings():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def normalize_name(name):
    if pd.isna(name):
        return ""

    s = str(name).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    s = s.replace("’", "'")
    s = re.sub(r"[.\-']", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    suffixes = {"jr", "sr", "ii", "iii", "iv"}
    parts = s.split()
    while parts and parts[-1] in suffixes:
        parts = parts[:-1]

    s = " ".join(parts)
    return NAME_ALIASES.get(s, s)

def parse_prop_game(game):
    if pd.isna(game) or " @ " not in str(game):
        return pd.Series({"away_team_name": None, "home_team_name": None, "away_abbr": None, "home_abbr": None})

    away, home = str(game).split(" @ ", 1)
    away = away.strip()
    home = home.strip()

    return pd.Series({
        "away_team_name": away,
        "home_team_name": home,
        "away_abbr": TEAM_NAME_TO_ABBR.get(away),
        "home_abbr": TEAM_NAME_TO_ABBR.get(home),
    })

def american_to_prob(odds):
    odds = float(odds)
    if odds < 0:
        return abs(odds) / (abs(odds) + 100.0)
    return 100.0 / (odds + 100.0)

def clean_market_table(props_path, output_path):
    print("\n================ CLEANING DRAFTKINGS MARKET TABLE ================")

    props = pd.read_csv(props_path)
    props["date"] = pd.to_datetime(props["date"]).dt.date.astype(str)
    props["side_clean"] = props["side"].astype(str).str.lower().str.strip()
    props["player_norm"] = props["player"].apply(normalize_name)

    game_parts = props["game"].apply(parse_prop_game)
    props = pd.concat([props, game_parts], axis=1)

    bad_teams = props[props["away_abbr"].isna() | props["home_abbr"].isna()]
    if len(bad_teams):
        print("WARNING: some prop games could not be mapped to team abbreviations")
        print(bad_teams[["date", "game"]].drop_duplicates().head(20).to_string(index=False))

    market = props.pivot_table(
        index=[
            "date",
            "player",
            "player_norm",
            "game",
            "away_team_name",
            "home_team_name",
            "away_abbr",
            "home_abbr",
            "line",
        ],
        columns="side_clean",
        values="american_odds",
        aggfunc="first",
    ).reset_index()

    market.columns.name = None
    market = market.rename(columns={
        "line": "points_line",
        "over": "over_odds",
        "under": "under_odds",
    })

    market["raw_prob_over"] = market["over_odds"].apply(american_to_prob)
    market["raw_prob_under"] = market["under_odds"].apply(american_to_prob)
    market["vig"] = market["raw_prob_over"] + market["raw_prob_under"] - 1.0
    market["market_prob_over_novig"] = market["raw_prob_over"] / (
        market["raw_prob_over"] + market["raw_prob_under"]
    )
    market["market_prob_under_novig"] = 1.0 - market["market_prob_over_novig"]

    market["sportsbook"] = "DraftKings"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    market.to_csv(output_path, index=False)

    print(f"Wrote {output_path}")
    print(f"Rows: {len(market):,}")
    print(f"Complete over/under rows: {market[['over_odds', 'under_odds']].notna().all(axis=1).sum():,}")
    print(f"Date range: {market['date'].min()} to {market['date'].max()}")

    return market

def prepare_modeling_table(modeling_path):
    modeling = pd.read_csv(modeling_path)
    modeling["date"] = pd.to_datetime(modeling["GAME_DATE"]).dt.date.astype(str)
    modeling["player_norm"] = modeling["PLAYER_NAME"].apply(normalize_name)

    modeling["home_abbr"] = np.where(
        modeling["HOME"].astype(int) == 1,
        modeling["TEAM_ABBREVIATION"],
        modeling["OPP"],
    )

    modeling["away_abbr"] = np.where(
        modeling["HOME"].astype(int) == 1,
        modeling["OPP"],
        modeling["TEAM_ABBREVIATION"],
    )

    key_cols = ["date", "player_norm", "away_abbr", "home_abbr"]

    dupes = modeling.duplicated(subset=key_cols).sum()
    if dupes:
        print(f"WARNING: modeling table has {dupes:,} duplicate rows on join key. Keeping first.")
        modeling = modeling.drop_duplicates(subset=key_cols, keep="first")

    return modeling

def join_props_to_features(market, modeling_path, results_output, dataset_output):
    print("\n================ JOINING PROPS TO NBA RESULTS + FEATURES ================")

    modeling = prepare_modeling_table(modeling_path)

    key_cols = ["date", "player_norm", "away_abbr", "home_abbr"]

    merged = market.merge(
        modeling,
        on=key_cols,
        how="left",
        indicator=True,
        suffixes=("", "_nba"),
    )

    merged["matched"] = merged["_merge"].eq("both")
    merged = merged.drop(columns=["_merge"])

    merged["actual_points"] = merged["PTS"]
    merged["went_over"] = (merged["actual_points"] > merged["points_line"]).astype("Int64")
    merged["went_under"] = (merged["actual_points"] < merged["points_line"]).astype("Int64")
    merged["push"] = (merged["actual_points"] == merged["points_line"]).astype("Int64")

    # If unmatched, keep outcome columns empty rather than fake 0s.
    for c in ["went_over", "went_under", "push"]:
        merged.loc[~merged["matched"], c] = pd.NA

    matched = merged[merged["matched"]].copy()

    results_output.parent.mkdir(parents=True, exist_ok=True)
    dataset_output.parent.mkdir(parents=True, exist_ok=True)

    merged.to_csv(results_output, index=False)
    matched.to_csv(dataset_output, index=False)

    print(f"Wrote full joined file: {results_output}")
    print(f"Wrote matched modeling dataset: {dataset_output}")
    print(f"Market rows: {len(market):,}")
    print(f"Matched rows: {len(matched):,}")
    print(f"Match rate: {len(matched) / len(market):.1%}")

    unmatched = merged[~merged["matched"]]
    if len(unmatched):
        print("\nSample unmatched rows:")
        print(
            unmatched[
                ["date", "player", "game", "points_line", "away_abbr", "home_abbr", "player_norm"]
            ].head(40).to_string(index=False)
        )

    print("\nOutcome counts on matched rows:")
    print(matched[["went_over", "went_under", "push"]].sum().to_string())

    return merged, matched

def main():
    settings = load_settings()
    paths = settings["paths"]

    props_path = ROOT / paths["historical_props_with_odds"]
    modeling_path = ROOT / paths["modeling_table"]
    clean_market_path = ROOT / paths["clean_market_table"]
    props_with_results_path = ROOT / paths["props_with_results"]
    modeling_dataset_path = ROOT / paths["modeling_dataset"]

    missing = [p for p in [props_path, modeling_path] if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required input files: {missing}")

    market = clean_market_table(props_path, clean_market_path)
    join_props_to_features(
        market=market,
        modeling_path=modeling_path,
        results_output=props_with_results_path,
        dataset_output=modeling_dataset_path,
    )

    print("\n================ DONE ================")
    print("Next step after this: train model + run backtest.")

if __name__ == "__main__":
    main()
