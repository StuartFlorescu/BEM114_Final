from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "settings.yaml"

def load_settings():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def american_profit_per_1(odds):
    odds = float(odds)
    if odds > 0:
        return odds / 100.0
    return 100.0 / abs(odds)

def bet_return(row):
    side = row["bet_side"]

    if side == "Over":
        if row["actual_points"] > row["points_line"]:
            return american_profit_per_1(row["over_odds"])
        if row["actual_points"] < row["points_line"]:
            return -1.0
        return 0.0

    if side == "Under":
        if row["actual_points"] < row["points_line"]:
            return american_profit_per_1(row["under_odds"])
        if row["actual_points"] > row["points_line"]:
            return -1.0
        return 0.0

    return 0.0

def max_drawdown(returns):
    if len(returns) == 0:
        return 0.0
    equity = (1.0 + pd.Series(returns).fillna(0.0)).cumprod()
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())

def summarize_trades(trades, threshold):
    if len(trades) == 0:
        return {
            "threshold": threshold,
            "n_bets": 0,
            "hit_rate": np.nan,
            "avg_return_per_bet": np.nan,
            "total_return_sum": 0.0,
            "roi_per_dollar_staked": np.nan,
            "return_vol": np.nan,
            "per_bet_sharpe": np.nan,
            "max_drawdown": np.nan,
            "over_bets": 0,
            "under_bets": 0,
        }

    r = trades["return"].astype(float)
    wins = (r > 0).sum()

    return {
        "threshold": threshold,
        "n_bets": len(trades),
        "hit_rate": wins / len(trades),
        "avg_return_per_bet": r.mean(),
        "total_return_sum": r.sum(),
        "roi_per_dollar_staked": r.sum() / len(trades),
        "return_vol": r.std(ddof=1),
        "per_bet_sharpe": r.mean() / r.std(ddof=1) if r.std(ddof=1) > 0 else np.nan,
        "max_drawdown": max_drawdown(r),
        "over_bets": int((trades["bet_side"] == "Over").sum()),
        "under_bets": int((trades["bet_side"] == "Under").sum()),
    }

def run_backtest(predictions):
    settings = load_settings()
    thresholds = settings.get("edge_thresholds", [0.025, 0.05, 0.075, 0.10])

    test = predictions[predictions["split"] == "test"].copy()

    all_trades = []
    summary_rows = []

    for tau in thresholds:
        df = test.copy()

        df["edge_over"] = df["model_prob_over"] - df["market_prob_over_novig"]
        df["edge_under"] = df["market_prob_over_novig"] - df["model_prob_over"]

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
        summary_rows.append(summarize_trades(trades, tau))

    trades_out = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    summary = pd.DataFrame(summary_rows)

    out_dir = ROOT / "data" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    trades_path = out_dir / "trades.csv"
    summary_path = out_dir / "backtest_summary.csv"

    trades_out.to_csv(trades_path, index=False)
    summary.to_csv(summary_path, index=False)

    print("\n================ BACKTEST RESULTS ================")
    print(summary.to_string(index=False))
    print()
    print(f"Wrote trades to: {trades_path}")
    print(f"Wrote summary to: {summary_path}")

    return trades_out, summary

if __name__ == "__main__":
    predictions_path = ROOT / "data" / "outputs" / "model_predictions.csv"
    if not predictions_path.exists():
        raise FileNotFoundError(f"Missing predictions file: {predictions_path}")

    predictions = pd.read_csv(predictions_path)
    run_backtest(predictions)
