from pathlib import Path
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score, accuracy_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


ROOT = Path(__file__).resolve().parents[1]
MODELING_PATH = ROOT / "data" / "processed" / "modeling_table.csv"
OUTPUT_DIR = ROOT / "data" / "outputs"
PREDICTIONS_PATH = OUTPUT_DIR / "model_predictions.csv"
METRICS_PATH = OUTPUT_DIR / "model_metrics.csv"

TRAIN_END_DATE = "2024-10-01"

FEATURES = [
    "player_fta_l10",
    "player_pfd_l10",
    "player_min_l10",
    "player_fga_l10",
    "player_fta_per_min_l10",
    "player_pfd_per_min_l10",
    "opp_pf_l10",
    "opp_fta_allowed_l10",
    "simple_matchup_risk",
    "HOME",
]


def load_modeling_table():
    if not MODELING_PATH.exists():
        raise FileNotFoundError(
            f"Missing {MODELING_PATH}. Run python scripts/02_build_features.py first."
        )

    df = pd.read_csv(MODELING_PATH)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    return df


def train_model(train):
    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("logit", LogisticRegression(max_iter=1000)),
        ]
    )

    model.fit(train[FEATURES], train["over_result"])
    return model


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_modeling_table()
    df = df.dropna(subset=FEATURES + ["over_result"]).copy()
    df = df[df["player_min_l10"] >= 18].copy()

    train = df[df["GAME_DATE"] < TRAIN_END_DATE].copy()
    test = df[df["GAME_DATE"] >= TRAIN_END_DATE].copy()

    if train.empty or test.empty:
        raise RuntimeError("Train or test set is empty. Check TRAIN_END_DATE.")

    model = train_model(train)

    test["p_over"] = model.predict_proba(test[FEATURES])[:, 1]
    test["pred_over"] = (test["p_over"] >= 0.5).astype(int)

    brier = brier_score_loss(test["over_result"], test["p_over"])
    auc = roc_auc_score(test["over_result"], test["p_over"])
    acc = accuracy_score(test["over_result"], test["pred_over"])

    baseline_prob = train["over_result"].mean()
    test["baseline_p_over"] = baseline_prob
    baseline_brier = brier_score_loss(test["over_result"], test["baseline_p_over"])

    metrics = pd.DataFrame(
        [
            {
                "train_rows": len(train),
                "test_rows": len(test),
                "train_start": train["GAME_DATE"].min(),
                "train_end": train["GAME_DATE"].max(),
                "test_start": test["GAME_DATE"].min(),
                "test_end": test["GAME_DATE"].max(),
                "baseline_over_rate": baseline_prob,
                "model_brier": brier,
                "baseline_brier": baseline_brier,
                "model_auc": auc,
                "model_accuracy": acc,
            }
        ]
    )

    keep_cols = [
        "GAME_DATE",
        "GAME_ID",
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ABBREVIATION",
        "MATCHUP",
        "MIN",
        "FTA",
        "PFD",
        "synthetic_line",
        "over_result",
        "p_over",
        "pred_over",
        "baseline_p_over",
        "player_fta_l10",
        "player_pfd_l10",
        "player_min_l10",
        "opp_pf_l10",
        "opp_fta_allowed_l10",
        "simple_matchup_risk",
    ]

    test[keep_cols].to_csv(PREDICTIONS_PATH, index=False)
    metrics.to_csv(METRICS_PATH, index=False)

    print(f"Saved predictions to {PREDICTIONS_PATH}")
    print(f"Saved metrics to {METRICS_PATH}")
    print(metrics.T)


if __name__ == "__main__":
    main()
