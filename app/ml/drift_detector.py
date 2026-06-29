from pathlib import Path

import joblib
import numpy as np
import pandas as pd


BASELINE_DIR = Path(__file__).resolve().parent / "models" / "drift"
BASELINE_FILE = BASELINE_DIR / "feature_drift_baseline.pkl"


def calculate_psi(
    baseline_values: pd.Series,
    current_values: pd.Series,
    buckets: int = 10,
) -> float:
    baseline_values = baseline_values.dropna()
    current_values = current_values.dropna()

    if baseline_values.empty or current_values.empty:
        return 0.0

    breakpoints = np.percentile(
        baseline_values,
        np.linspace(0, 100, buckets + 1),
    )

    breakpoints = np.unique(breakpoints)

    if len(breakpoints) <= 2:
        return 0.0

    baseline_counts, _ = np.histogram(baseline_values, bins=breakpoints)
    current_counts, _ = np.histogram(current_values, bins=breakpoints)

    baseline_percents = baseline_counts / max(len(baseline_values), 1)
    current_percents = current_counts / max(len(current_values), 1)

    baseline_percents = np.where(baseline_percents == 0, 0.0001, baseline_percents)
    current_percents = np.where(current_percents == 0, 0.0001, current_percents)

    psi = np.sum(
        (current_percents - baseline_percents)
        * np.log(current_percents / baseline_percents)
    )

    return float(psi)


def save_drift_baseline(df: pd.DataFrame, feature_columns: list[str]) -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    baseline = {
        "feature_columns": feature_columns,
        "mean": df[feature_columns].mean().to_dict(),
        "std": df[feature_columns].std().replace(0, 1).to_dict(),
        "sample": df[feature_columns].copy(),
    }

    joblib.dump(baseline, BASELINE_FILE)


def detect_feature_drift(df: pd.DataFrame, feature_columns: list[str]) -> dict:
    if not BASELINE_FILE.exists():
        save_drift_baseline(df, feature_columns)
        return {
            "drift_status": "BASELINE_CREATED",
            "drifted_features": [],
            "max_drift_score": 0,
            "max_psi_score": 0,
        }

    baseline = joblib.load(BASELINE_FILE)

    drifted_features = []
    max_drift_score = 0
    max_psi_score = 0

    baseline_sample = baseline.get("sample")

    for col in feature_columns:
        current_mean = float(df[col].mean())
        baseline_mean = float(baseline["mean"].get(col, 0))
        baseline_std = float(baseline["std"].get(col, 1)) or 1

        drift_score = abs(current_mean - baseline_mean) / baseline_std
        max_drift_score = max(max_drift_score, drift_score)

        psi_score = 0.0
        if baseline_sample is not None and col in baseline_sample.columns:
            psi_score = calculate_psi(
                baseline_sample[col],
                df[col],
            )

        max_psi_score = max(max_psi_score, psi_score)

        if drift_score >= 2 or psi_score >= 0.25:
            drifted_features.append(col)

    return {
        "drift_status": "DRIFT_DETECTED" if drifted_features else "NO_DRIFT",
        "drifted_features": drifted_features,
        "max_drift_score": round(max_drift_score, 4),
        "max_psi_score": round(max_psi_score, 4),
    }