from pathlib import Path

import joblib
import pandas as pd


BASELINE_DIR = Path(__file__).resolve().parent / "models" / "drift"
BASELINE_FILE = BASELINE_DIR / "feature_drift_baseline.pkl"


def save_drift_baseline(df: pd.DataFrame, feature_columns: list[str]) -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    baseline = {
        "feature_columns": feature_columns,
        "mean": df[feature_columns].mean().to_dict(),
        "std": df[feature_columns].std().replace(0, 1).to_dict(),
    }

    joblib.dump(baseline, BASELINE_FILE)


def detect_feature_drift(df: pd.DataFrame, feature_columns: list[str]) -> dict:
    if not BASELINE_FILE.exists():
        save_drift_baseline(df, feature_columns)
        return {
            "drift_status": "BASELINE_CREATED",
            "drifted_features": [],
            "max_drift_score": 0,
        }

    baseline = joblib.load(BASELINE_FILE)

    drifted_features = []
    max_drift_score = 0

    for col in feature_columns:
        current_mean = float(df[col].mean())
        baseline_mean = float(baseline["mean"].get(col, 0))
        baseline_std = float(baseline["std"].get(col, 1)) or 1

        drift_score = abs(current_mean - baseline_mean) / baseline_std
        max_drift_score = max(max_drift_score, drift_score)

        if drift_score >= 2:
            drifted_features.append(col)

    return {
        "drift_status": "DRIFT_DETECTED" if drifted_features else "NO_DRIFT",
        "drifted_features": drifted_features,
        "max_drift_score": round(max_drift_score, 4),
    }