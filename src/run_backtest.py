from pathlib import Path
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "outputs"
PREDICTIONS_PATH = OUTPUT_DIR / "model_predictions.csv"
TRADES_PATH = OUTPUT_DIR / "trades.csv"
SUMMARY_PATH = OUTPUT_DIR / "backtest_summary.csv"

OVER_THRESHOLD = 0.65
UNDER_THRESHOLD = 0.35


def max_drawdown(equity):
    running_max = equity.cummax()
    drawdown = equity - running_max
    return drawdown.min()


def run_backtest(preds):
    df = preds.copy()
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])

    df["side"] = 0
    df.loc[df["p_over"] > OVER_THRESHOLD, "side"] = 1
    df.loc[df["p_over"] < UNDER_THRESHOLD, "side"] = -1

    df["trade_return"] = 0.0

    over_mask = df["side"] == 1
    under_mask = df["side"] == -1

    df.loc[over_mask, "trade_return"] = np.where(
        df.loc[over_mask, "over_result"] == 1, 1.0, -1.0
    )
    df.loc[under_mask, "trade_return"] = np.where(
        df.loc[under_mask, "over_result"] == 0, 1.0, -1.0
    )

    trades = df[df["side"] != 0].copy()
    trades = trades.sort_values(["GAME_DATE", "GAME_ID", "PLAYER_NAME"])
    trades["equity"] = trades["trade_return"].cumsum()

    return trades


def summarize(trades, all_preds):
    if trades.empty:
        return pd.DataFrame(
            [
                {
                    "num_test_observations": len(all_preds),
                    "num_trades": 0,
                    "trade_rate": 0.0,
                    "hit_rate": np.nan,
                    "avg_return_per_trade": np.nan,
                    "return_std": np.nan,
                    "pseudo_sharpe_per_trade": np.nan,
                    "max_drawdown": np.nan,
                    "final_equity": 0.0,
                    "over_threshold": OVER_THRESHOLD,
                    "under_threshold": UNDER_THRESHOLD,
                }
            ]
        )

    hit_rate = (trades["trade_return"] > 0).mean()
    avg_return = trades["trade_return"].mean()
    ret_std = trades["trade_return"].std(ddof=1)
    sharpe = avg_return / ret_std if ret_std and ret_std > 0 else np.nan

    return pd.DataFrame(
        [
            {
                "num_test_observations": len(all_preds),
                "num_trades": len(trades),
                "trade_rate": len(trades) / len(all_preds),
                "hit_rate": hit_rate,
                "avg_return_per_trade": avg_return,
                "return_std": ret_std,
                "pseudo_sharpe_per_trade": sharpe,
                "max_drawdown": max_drawdown(trades["equity"]),
                "final_equity": trades["equity"].iloc[-1],
                "over_threshold": OVER_THRESHOLD,
                "under_threshold": UNDER_THRESHOLD,
            }
        ]
    )


def main():
    if not PREDICTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Missing {PREDICTIONS_PATH}. Run train_model.py first."
        )

    preds = pd.read_csv(PREDICTIONS_PATH)
    trades = run_backtest(preds)
    summary = summarize(trades, preds)

    trades.to_csv(TRADES_PATH, index=False)
    summary.to_csv(SUMMARY_PATH, index=False)

    print(f"Saved trades to {TRADES_PATH}")
    print(f"Saved summary to {SUMMARY_PATH}")
    print(summary.T)

    if not trades.empty:
        print("\nSample trades:")
        print(
            trades[
                [
                    "GAME_DATE",
                    "PLAYER_NAME",
                    "MATCHUP",
                    "FTA",
                    "synthetic_line",
                    "p_over",
                    "side",
                    "over_result",
                    "trade_return",
                    "equity",
                ]
            ].head(20)
        )


if __name__ == "__main__":
    main()
