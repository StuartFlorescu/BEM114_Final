"""PROJECT 2 (alpha scanner): soft-vs-sharp +EV detection on NBA moneylines.

Thesis: Pinnacle's no-vig price is the best estimate of true win probability. When a US
soft book offers a price that is +EV against that sharp truth, betting it is +EV — an
arbitrage against a better-informed price, not a prediction.

For each game (early snapshot):
  p_true   = Pinnacle no-vig probability for a team
  best_odds = best price for that team across US soft books (line shopping)
  EV per $1 = p_true * profit_mult(best_odds) - (1 - p_true)
Bet when EV > threshold. Validate with realized ROI / win-rate, and (if available)
Closing Line Value vs the late-snapshot Pinnacle no-vig.
"""
from pathlib import Path
import numpy as np
import pandas as pd

from src.add_referee_features import build_game_stats, TEAM_NAME_TO_ABBR
from src.build_features import american_to_prob
from src.diagnose_strategy import american_profit_per_1

ROOT = Path(__file__).resolve().parents[1]
MULTIBOOK = ROOT / "data/raw/alpha_h2h_multibook.csv"
PLAYER_GAMES = ROOT / "data/processed/player_games_clean.csv"

SHARP = "pinnacle"
US_SOFT = ["draftkings", "fanduel", "betmgm", "betrivers", "pointsbetus", "wynnbet",
           "superbook", "williamhill_us", "unibet_us", "betus", "bovada", "mybookieag"]


def game_winners():
    pg = pd.read_csv(PLAYER_GAMES)
    if "date" not in pg.columns:
        pg["date"] = pd.to_datetime(pg["GAME_DATE"]).dt.date.astype(str)
    gs = build_game_stats(pg)
    gs["winner_abbr"] = np.where(gs["home_pts"] > gs["away_pts"], gs["home_abbr"], gs["away_abbr"])
    return gs[["date", "home_abbr", "away_abbr", "winner_abbr", "home_pts", "away_pts"]]


def novig_prob(odds_a, odds_b):
    pa, pb = american_to_prob(odds_a), american_to_prob(odds_b)
    return pa / (pa + pb)


def build():
    mb = pd.read_csv(MULTIBOOK)
    early = mb[mb["snapshot_label"] == "early"].copy()
    early["abbr"] = early["team"].map(TEAM_NAME_TO_ABBR)
    early["home_abbr"] = early["home_team"].map(TEAM_NAME_TO_ABBR)
    early["away_abbr"] = early["away_team"].map(TEAM_NAME_TO_ABBR)

    rows = []
    for eid, g in early.groupby("event_id"):
        teams = g["abbr"].dropna().unique()
        if len(teams) != 2:
            continue
        date = g["date"].iloc[0]
        # Pinnacle no-vig per team
        pinn = g[g["book"] == SHARP]
        if pinn["abbr"].nunique() != 2:
            continue
        po = {r["abbr"]: r["american_odds"] for _, r in pinn.iterrows()}
        for team in teams:
            other = [t for t in teams if t != team][0]
            p_true = novig_prob(po[team], po[other])
            soft = g[(g["book"].isin(US_SOFT)) & (g["abbr"] == team)]
            if soft.empty:
                continue
            best_odds = soft["american_odds"].max()        # best price for the bettor
            best_book = soft.loc[soft["american_odds"].idxmax(), "book"]
            b = american_profit_per_1(best_odds)
            ev = p_true * b - (1 - p_true)
            rows.append({
                "date": date, "event_id": eid, "team": team,
                "home_abbr": g["home_abbr"].iloc[0], "away_abbr": g["away_abbr"].iloc[0],
                "p_true": p_true, "best_odds": best_odds, "best_book": best_book,
                "profit_mult": b, "ev_per_dollar": ev,
            })
    bets = pd.DataFrame(rows)

    win = game_winners()
    bets = bets.merge(win, on=["date", "home_abbr", "away_abbr"], how="inner")
    bets["won"] = (bets["team"] == bets["winner_abbr"]).astype(int)
    bets["realized_ret"] = np.where(bets["won"] == 1, bets["profit_mult"], -1.0)
    return bets


def report(bets):
    print(f"Total candidate team-bets: {len(bets):,} | games: {bets['event_id'].nunique():,}")
    print(f"Date range: {bets['date'].min()} -> {bets['date'].max()}\n")
    print(f"{'EV threshold':>13}{'bets':>7}{'win%':>7}{'avg EV%':>9}{'realized ROI%':>15}{'units':>9}")
    for thr in [0.0, 0.01, 0.02, 0.03, 0.05]:
        s = bets[bets["ev_per_dollar"] > thr]
        if len(s) == 0:
            print(f"{thr:>13}{0:>7}"); continue
        print(f"{thr:>13}{len(s):>7}{s['won'].mean()*100:>6.1f}%{s['ev_per_dollar'].mean()*100:>8.2f}%"
              f"{s['realized_ret'].mean()*100:>14.2f}%{s['realized_ret'].sum():>9.1f}")
    # per-book at EV>1%
    print("\nBy soft book (EV>1%):")
    s = bets[bets["ev_per_dollar"] > 0.01]
    bb = s.groupby("best_book").agg(bets=("won", "size"), win=("won", "mean"),
                                    roi=("realized_ret", "mean"), units=("realized_ret", "sum"))
    print(bb.sort_values("units", ascending=False).round(3).to_string())


if __name__ == "__main__":
    b = build()
    report(b)
