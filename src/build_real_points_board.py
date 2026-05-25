from pathlib import Path
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "real_player_points_lines_current.csv"
PROCESSED_DIR = ROOT / "data" / "processed"

BOOK_BOARD_PATH = PROCESSED_DIR / "real_points_book_board_current.csv"
CONSENSUS_PATH = PROCESSED_DIR / "real_points_consensus_board_current.csv"


def american_to_implied_prob(odds):
    odds = float(odds)
    if odds < 0:
        return (-odds) / ((-odds) + 100)
    return 100 / (odds + 100)


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Missing {RAW_PATH}. Run scripts/05_pull_real_points_lines.py first.")

    raw = pd.read_csv(RAW_PATH)

    needed = [
        "event_id",
        "commence_time",
        "home_team",
        "away_team",
        "bookmaker_key",
        "bookmaker_title",
        "market_key",
        "player_name",
        "side",
        "line",
        "american_odds",
    ]

    df = raw[needed].copy()
    df = df[df["market_key"] == "player_points"].copy()
    df = df[df["side"].isin(["Over", "Under"])].copy()
    df = df.dropna(subset=["player_name", "line", "american_odds"])

    df["implied_prob"] = df["american_odds"].apply(american_to_implied_prob)

    # One row per event/book/player/line, with over and under odds side by side.
    book_board = (
        df.pivot_table(
            index=[
                "event_id",
                "commence_time",
                "home_team",
                "away_team",
                "bookmaker_key",
                "bookmaker_title",
                "player_name",
                "line",
            ],
            columns="side",
            values=["american_odds", "implied_prob"],
            aggfunc="first",
        )
        .reset_index()
    )

    book_board.columns = [
        "_".join([str(x) for x in col if str(x) != ""]).strip("_")
        for col in book_board.columns
    ]

    book_board = book_board.rename(
        columns={
            "american_odds_Over": "over_odds",
            "american_odds_Under": "under_odds",
            "implied_prob_Over": "over_implied_prob",
            "implied_prob_Under": "under_implied_prob",
        }
    )

    book_board = book_board.dropna(subset=["over_odds", "under_odds"]).copy()

    book_board["vig_sum"] = book_board["over_implied_prob"] + book_board["under_implied_prob"]
    book_board["no_vig_over_prob"] = book_board["over_implied_prob"] / book_board["vig_sum"]
    book_board["no_vig_under_prob"] = book_board["under_implied_prob"] / book_board["vig_sum"]

    book_board = book_board.sort_values(
        ["commence_time", "event_id", "player_name", "bookmaker_key", "line"]
    )

    book_board.to_csv(BOOK_BOARD_PATH, index=False)

    # Consensus board: one row per event/player/line across books.
    consensus = (
        book_board.groupby(
            [
                "event_id",
                "commence_time",
                "home_team",
                "away_team",
                "player_name",
                "line",
            ],
            as_index=False,
        )
        .agg(
            books_count=("bookmaker_key", "nunique"),
            avg_no_vig_over_prob=("no_vig_over_prob", "mean"),
            best_over_odds=("over_odds", "max"),
            best_under_odds=("under_odds", "max"),
            avg_over_odds=("over_odds", "mean"),
            avg_under_odds=("under_odds", "mean"),
        )
    )

    consensus = consensus.sort_values(
        ["commence_time", "event_id", "player_name", "line"]
    )

    consensus.to_csv(CONSENSUS_PATH, index=False)

    print(f"Saved book-level board to {BOOK_BOARD_PATH}")
    print(f"Saved consensus board to {CONSENSUS_PATH}")
    print()
    print("Raw rows:", len(raw))
    print("Book-board rows:", len(book_board))
    print("Consensus rows:", len(consensus))
    print()
    print("Book-board preview:")
    print(book_board.head(20).to_string(index=False))
    print()
    print("Consensus preview:")
    print(consensus.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
