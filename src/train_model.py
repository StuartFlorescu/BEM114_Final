from pathlib import Path
import numpy as np
import pandas as pd
import yaml

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss, accuracy_score

from src.run_backtest import run_backtest

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "settings.yaml"

FEATURE_CANDIDATES = [
    "points_line",
    "market_prob_over_novig",
    "player_pts_l5",
    "player_fta_l5",
    "player_pfd_l5",
    "player_min_l5",
    "player_fga_l5",
    "player_pf_l5",
    "player_pts_l10",
    "player_fta_l10",
    "player_pfd_l10",
    "player_min_l10",
    "player_fga_l10",
    "player_pf_l10",
    "player_pts_l20",
    "player_fta_l20",
    "player_pfd_l20",
    "player_min_l20",
    "player_fga_l20",
    "player_pf_l20",
    "player_pts_per_min_l10",
    "player_fta_per_min_l10",
    "player_pfd_per_min_l10",
    "player_fga_per_min_l10",
    "opp_pf_l10",
    "opp_fta_allowed_l10",
    "opp_pf_l20",
    "opp_fta_allowed_l20",
    "simple_matchup_risk",
]

def load_settings():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def time_split(df, date_col="date", train_frac=0.70):
    unique_dates = sorted(pd.to_datetime(df[date_col]).dt.date.unique())
    if len(unique_dates) < 3:
        raise ValueError("Not enough unique dates for a time split.")

    split_idx = max(1, int(len(unique_dates) * train_frac))
    split_date = unique_dates[split_idx]

    train_mask = pd.to_datetime(df[date_col]).dt.date < split_date
    test_mask = ~train_mask

    return train_mask, test_mask, split_date

def safe_metric(name, fn, y_true, pred):
    try:
        return fn(y_true, pred)
    except Exception:
        return np.nan

def main():
    settings = load_settings()
    dataset_path = ROOT / settings["paths"]["modeling_dataset"]

    if not dataset_path.exists():
        raise FileNotFoundError(f"Missing modeling dataset: {dataset_path}")

    df = pd.read_csv(dataset_path)

    print("\n================ TRAINING BASELINE MODEL ================")
    print(f"Loaded dataset: {dataset_path}")
    print(f"Rows: {len(df):,}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")

    df = df.copy()
    df["went_over"] = df["went_over"].astype(int)

    auto_matchup_features = [
        c for c in df.columns
        if c.startswith("def_role_") or c.startswith("matchup_")
    ]

    features = [c for c in FEATURE_CANDIDATES if c in df.columns]
    for c in auto_matchup_features:
        if c not in features:
            features.append(c)

    missing = [c for c in FEATURE_CANDIDATES if c not in df.columns]

    print(f"Using {len(features)} features:")
    print(features)

    if missing:
        print("\nMissing candidate features, skipping:")
        print(missing)

    model_df = df.dropna(subset=features + ["went_over", "market_prob_over_novig", "actual_points", "points_line"]).copy()

    train_mask, test_mask, split_date = time_split(model_df, date_col="date", train_frac=0.70)

    train = model_df[train_mask].copy()
    test = model_df[test_mask].copy()

    print(f"\nTime split date: {split_date}")
    print(f"Train rows: {len(train):,} | {train['date'].min()} to {train['date'].max()}")
    print(f"Test rows:  {len(test):,} | {test['date'].min()} to {test['date'].max()}")

    X_train = train[features]
    y_train = train["went_over"]

    X_test = test[features]
    y_test = test["went_over"]

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("logit", LogisticRegression(max_iter=2000, C=1.0)),
    ])

    model.fit(X_train, y_train)

    train_pred = model.predict_proba(X_train)[:, 1]
    test_pred = model.predict_proba(X_test)[:, 1]

    print("\n================ MODEL METRICS ================")
    metrics = {
        "train_auc": safe_metric("train_auc", roc_auc_score, y_train, train_pred),
        "test_auc": safe_metric("test_auc", roc_auc_score, y_test, test_pred),
        "train_log_loss": safe_metric("train_log_loss", log_loss, y_train, train_pred),
        "test_log_loss": safe_metric("test_log_loss", log_loss, y_test, test_pred),
        "train_brier": safe_metric("train_brier", brier_score_loss, y_train, train_pred),
        "test_brier": safe_metric("test_brier", brier_score_loss, y_test, test_pred),
        "train_accuracy_50pct": accuracy_score(y_train, train_pred >= 0.5),
        "test_accuracy_50pct": accuracy_score(y_test, test_pred >= 0.5),
        "market_test_auc": safe_metric("market_test_auc", roc_auc_score, y_test, test["market_prob_over_novig"]),
        "market_test_log_loss": safe_metric("market_test_log_loss", log_loss, y_test, test["market_prob_over_novig"]),
        "market_test_brier": safe_metric("market_test_brier", brier_score_loss, y_test, test["market_prob_over_novig"]),
    }

    for k, v in metrics.items():
        print(f"{k}: {v:.6f}" if pd.notna(v) else f"{k}: NaN")

    train_out = train.copy()
    train_out["model_prob_over"] = train_pred
    train_out["split"] = "train"

    test_out = test.copy()
    test_out["model_prob_over"] = test_pred
    test_out["split"] = "test"

    pred = pd.concat([train_out, test_out], ignore_index=True)
    pred["edge_over"] = pred["model_prob_over"] - pred["market_prob_over_novig"]
    pred["edge_under"] = pred["market_prob_over_novig"] - pred["model_prob_over"]

    out_dir = ROOT / "data" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    pred_path = out_dir / "model_predictions.csv"
    metrics_path = out_dir / "model_metrics.csv"

    pred.to_csv(pred_path, index=False)
    pd.DataFrame([metrics]).to_csv(metrics_path, index=False)

    print()
    print(f"Wrote predictions to: {pred_path}")
    print(f"Wrote model metrics to: {metrics_path}")

    # Coefficients
    logit = model.named_steps["logit"]
    coef = pd.DataFrame({
        "feature": features,
        "coefficient": logit.coef_[0],
    }).sort_values("coefficient", ascending=False)

    coef_path = out_dir / "model_coefficients.csv"
    coef.to_csv(coef_path, index=False)

    print(f"Wrote coefficients to: {coef_path}")
    print("\nTop positive coefficients:")
    print(coef.head(10).to_string(index=False))
    print("\nTop negative coefficients:")
    print(coef.tail(10).to_string(index=False))

    run_backtest(pred)

if __name__ == "__main__":
    main()
