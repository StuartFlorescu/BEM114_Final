from pathlib import Path
import numpy as np
import pandas as pd
import yaml
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/settings.yaml"

PRED_PATH = ROOT / "data/outputs/model_predictions.csv"
OUT_DIR = ROOT / "reports/tables"
FIG_DIR = ROOT / "reports/figures"
SUMMARY_PATH = ROOT / "reports/strategy_diagnostic_summary.txt"

OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

def load_settings():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def american_profit_per_1(odds):
    odds = float(odds)
    if odds > 0:
        return odds / 100.0
    return 100.0 / abs(odds)

def bet_return(row):
    if row["bet_side"] == "Over":
        if row["actual_points"] > row["points_line"]:
            return american_profit_per_1(row["over_odds"])
        if row["actual_points"] < row["points_line"]:
            return -1.0
        return 0.0

    if row["bet_side"] == "Under":
        if row["actual_points"] < row["points_line"]:
            return american_profit_per_1(row["under_odds"])
        if row["actual_points"] > row["points_line"]:
            return -1.0
        return 0.0

    return 0.0

def max_drawdown_from_returns(returns):
    returns = pd.Series(returns).fillna(0.0).astype(float)
    if len(returns) == 0:
        return np.nan
    equity = 1.0 + returns.cumsum()
    peak = equity.cummax()
    dd = equity - peak
    return dd.min()

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

def fixed_bucket(s, bins, labels):
    return pd.cut(s, bins=bins, labels=labels, include_lowest=True)

def quantile_bucket(s, q=4, prefix="Q"):
    try:
        b = pd.qcut(s, q=q, duplicates="drop")
        return b.astype(str)
    except Exception:
        return pd.Series(["unbucketed"] * len(s), index=s.index)

def summarize_group(df):
    if len(df) == 0:
        return pd.Series({
            "n_bets": 0,
            "hit_rate": np.nan,
            "avg_return_per_bet": np.nan,
            "total_units": 0.0,
            "return_vol": np.nan,
            "per_bet_sharpe": np.nan,
            "max_drawdown_units": np.nan,
            "avg_abs_edge": np.nan,
            "avg_model_prob_over": np.nan,
            "avg_market_prob_over": np.nan,
            "avg_points_line": np.nan,
        })

    r = df["return"].astype(float)
    return pd.Series({
        "n_bets": len(df),
        "hit_rate": (r > 0).mean(),
        "avg_return_per_bet": r.mean(),
        "total_units": r.sum(),
        "return_vol": r.std(ddof=1),
        "per_bet_sharpe": r.mean() / r.std(ddof=1) if r.std(ddof=1) and r.std(ddof=1) > 0 else np.nan,
        "max_drawdown_units": max_drawdown_from_returns(r),
        "avg_abs_edge": df["abs_edge"].mean(),
        "avg_model_prob_over": df["model_prob_over"].mean(),
        "avg_market_prob_over": df["market_prob_over_novig"].mean(),
        "avg_points_line": df["points_line"].mean(),
    })

def make_trades(pred, thresholds):
    test = pred[pred["split"] == "test"].copy()

    all_trades = []
    for tau in thresholds:
        df = test.copy()

        df["edge_over"] = df["model_prob_over"] - df["market_prob_over_novig"]
        df["edge_under"] = df["market_prob_over_novig"] - df["model_prob_over"]
        df["abs_edge"] = np.maximum(df["edge_over"], df["edge_under"])

        df["bet_side"] = np.where(
            df["edge_over"] > tau,
            "Over",
            np.where(df["edge_under"] > tau, "Under", "No Bet")
        )

        trades = df[df["bet_side"] != "No Bet"].copy()
        trades["threshold"] = tau
        trades["return"] = trades.apply(bet_return, axis=1)
        trades["win"] = trades["return"] > 0
        all_trades.append(trades)

    if not all_trades:
        return pd.DataFrame()

    return pd.concat(all_trades, ignore_index=True)

def write_group_report(trades, group_cols, filename, min_bets=20):
    report = (
        trades
        .groupby(group_cols, dropna=False)
        .apply(summarize_group)
        .reset_index()
        .sort_values(["threshold", "avg_return_per_bet"], ascending=[True, False])
    )

    report["meets_min_bets"] = report["n_bets"] >= min_bets
    path = OUT_DIR / filename
    report.to_csv(path, index=False)
    return report, path

def main():
    settings = load_settings()
    thresholds = settings.get("edge_thresholds", [0.025, 0.05, 0.075, 0.10])

    if not PRED_PATH.exists():
        raise FileNotFoundError(f"Missing {PRED_PATH}. Run scripts/03_train_and_backtest.py first.")

    pred = pd.read_csv(PRED_PATH)
    trades = make_trades(pred, thresholds)

    if trades.empty:
        raise RuntimeError("No trades generated. Check predictions/thresholds.")

    # Buckets for diagnostics.
    if "scoring_role" not in trades.columns:
        trades["scoring_role"] = trades["player_pts_l10"].apply(scoring_role_bucket)

    trades["line_bucket"] = fixed_bucket(
        trades["points_line"],
        bins=[-np.inf, 8.5, 14.5, 20.5, np.inf],
        labels=["low_line", "mid_line", "high_line", "star_line"],
    )

    trades["market_prob_bucket"] = fixed_bucket(
        trades["market_prob_over_novig"],
        bins=[-np.inf, 0.45, 0.50, 0.55, np.inf],
        labels=["market_low_over", "market_slight_under", "market_slight_over", "market_high_over"],
    )

    trades["abs_edge_bucket"] = fixed_bucket(
        trades["abs_edge"],
        bins=[-np.inf, 0.05, 0.075, 0.10, 0.15, np.inf],
        labels=["edge_0_5", "edge_5_7_5", "edge_7_5_10", "edge_10_15", "edge_15_plus"],
    )

    trades["minutes_bucket"] = fixed_bucket(
        trades["player_min_l10"],
        bins=[-np.inf, 18, 26, 32, np.inf],
        labels=["low_minutes", "rotation_minutes", "starter_minutes", "heavy_minutes"],
    )

    trades["contact_bucket"] = quantile_bucket(trades["player_pfd_per_min_l10"], q=4)

    if "matchup_pts_edge_l10" in trades.columns:
        trades["matchup_pts_bucket"] = quantile_bucket(trades["matchup_pts_edge_l10"], q=4)
    else:
        trades["matchup_pts_bucket"] = "missing"

    if "matchup_pfd_edge_l10" in trades.columns:
        trades["matchup_contact_bucket"] = quantile_bucket(trades["matchup_pfd_edge_l10"], q=4)
    else:
        trades["matchup_contact_bucket"] = "missing"

    # Write raw diagnostic trades too.
    trades_path = OUT_DIR / "diagnostic_trades_all_thresholds.csv"
    trades.to_csv(trades_path, index=False)

    reports = {}

    reports["overall"], p1 = write_group_report(
        trades, ["threshold"], "diagnostic_by_threshold.csv", min_bets=1
    )

    reports["side"], p2 = write_group_report(
        trades, ["threshold", "bet_side"], "diagnostic_by_threshold_and_side.csv"
    )

    reports["role"], p3 = write_group_report(
        trades, ["threshold", "scoring_role"], "diagnostic_by_threshold_and_scoring_role.csv"
    )

    reports["line"], p4 = write_group_report(
        trades, ["threshold", "line_bucket"], "diagnostic_by_threshold_and_line_bucket.csv"
    )

    reports["market_prob"], p5 = write_group_report(
        trades, ["threshold", "market_prob_bucket"], "diagnostic_by_threshold_and_market_prob_bucket.csv"
    )

    reports["edge"], p6 = write_group_report(
        trades, ["threshold", "abs_edge_bucket"], "diagnostic_by_threshold_and_abs_edge_bucket.csv"
    )

    reports["minutes"], p7 = write_group_report(
        trades, ["threshold", "minutes_bucket"], "diagnostic_by_threshold_and_minutes_bucket.csv"
    )

    reports["contact"], p8 = write_group_report(
        trades, ["threshold", "contact_bucket"], "diagnostic_by_threshold_and_contact_bucket.csv"
    )

    reports["matchup_pts"], p9 = write_group_report(
        trades, ["threshold", "matchup_pts_bucket"], "diagnostic_by_threshold_and_matchup_pts_bucket.csv"
    )

    reports["matchup_contact"], p10 = write_group_report(
        trades, ["threshold", "matchup_contact_bucket"], "diagnostic_by_threshold_and_matchup_contact_bucket.csv"
    )

    reports["player"], p11 = write_group_report(
        trades, ["threshold", "player"], "diagnostic_by_threshold_and_player.csv", min_bets=5
    )

    # Best slices with enough bets.
    combined = []
    for name, df in reports.items():
        if name in {"overall", "player"}:
            continue
        temp = df.copy()
        temp["diagnostic_type"] = name
        combined.append(temp)

    best_slices = pd.concat(combined, ignore_index=True)
    best_slices = best_slices[best_slices["n_bets"] >= 30].copy()
    best_slices = best_slices.sort_values("avg_return_per_bet", ascending=False)

    best_path = OUT_DIR / "diagnostic_best_slices_min30.csv"
    best_slices.to_csv(best_path, index=False)

    # Cumulative unit P/L charts by threshold.
    for tau in thresholds:
        d = trades[trades["threshold"] == tau].copy()
        if d.empty:
            continue
        d = d.sort_values("date")
        d["cum_units"] = d["return"].cumsum()

        plt.figure(figsize=(9, 5))
        plt.plot(range(len(d)), d["cum_units"])
        plt.title(f"Cumulative Units by Trade, Threshold {tau:.3f}")
        plt.xlabel("Trade number")
        plt.ylabel("Cumulative units")
        plt.tight_layout()
        fig_path = FIG_DIR / f"cum_units_threshold_{str(tau).replace('.', '_')}.png"
        plt.savefig(fig_path, dpi=160)
        plt.close()

    # Summary text.
    lines = []
    lines.append("STRATEGY DIAGNOSTIC SUMMARY")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Predictions file: {PRED_PATH}")
    lines.append(f"Total diagnostic trades across thresholds: {len(trades):,}")
    lines.append("")
    lines.append("OVERALL BY THRESHOLD")
    lines.append("-" * 80)
    lines.append(reports["overall"].to_string(index=False))
    lines.append("")
    lines.append("BY THRESHOLD AND SIDE")
    lines.append("-" * 80)
    lines.append(reports["side"].to_string(index=False))
    lines.append("")
    lines.append("BEST SLICES WITH AT LEAST 30 BETS")
    lines.append("-" * 80)
    if len(best_slices):
        show_cols = [
            "diagnostic_type",
            "threshold",
            "n_bets",
            "hit_rate",
            "avg_return_per_bet",
            "total_units",
            "avg_abs_edge",
        ]
        extra_cols = [c for c in best_slices.columns if c not in show_cols and c not in [
            "return_vol", "per_bet_sharpe", "max_drawdown_units",
            "avg_model_prob_over", "avg_market_prob_over", "avg_points_line", "meets_min_bets"
        ]]
        show = extra_cols + show_cols
        lines.append(best_slices[show].head(30).to_string(index=False))
    else:
        lines.append("No slices had at least 30 bets.")
    lines.append("")
    lines.append("FILES WRITTEN")
    lines.append("-" * 80)
    for p in [trades_path, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, best_path]:
        lines.append(str(p.relative_to(ROOT)))
    lines.append("")
    lines.append("Figures written to reports/figures/")

    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print()
    print("=" * 80)
    print(f"WROTE SUMMARY: {SUMMARY_PATH}")
    print(f"WROTE TABLES TO: {OUT_DIR}")
    print(f"WROTE FIGURES TO: {FIG_DIR}")
    print("=" * 80)

if __name__ == "__main__":
    main()
