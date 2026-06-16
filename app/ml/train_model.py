import json
import os

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split


from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

FEATURE_FILE = ROOT_DIR / "outputs" / "supplier_features.csv"

MODEL_DIR = ROOT_DIR / "app" / "ml" / "models"
MODEL_FILE = MODEL_DIR / "risk_model.pkl"

METRICS_FILE = ROOT_DIR / "outputs" / "model_metrics.json"


FEATURE_COLUMNS = [
    "b_failure_rate",
    "b_pending_rate",
    "b_cancellation_rate",
    "b_deadline_miss_rate",
    "b_estimated_failure_loss",

    "bp_error_rate",
    "bp_stuck_rate",
    "bp_high_retry_rate",
    "bp_attempts_mean",

    "booking_not_issued_rate",
    "supplier_pnr_missing_rate",
    "ticket_number_missing_rate",
    "supplier_ticketing_risk_score_100",

    "ss_failure_rate",
    "ss_partial_rate",
    "ss_timeout_rate",
    "ss_completion_gap_rate",
    "supplier_session_risk_score_100",

    "rr_pending_rate",
    "rr_rejected_rate",
    "rr_avg_refund_delay_days",
    "rr_refund_risk_score_100",

    "cr_rejection_rate",
    "cr_overdue_rate",
    "cr_pending_rate",
    "cr_credit_risk_score_100",

    "wt_failed_payment_rate",
    "wt_hold_rate",
    "wt_negative_balance_rate",
    "wt_wallet_risk_score_100",
]


LABEL_MAP = {
    "LOW_RISK": 0,
    "MEDIUM_RISK": 1,
    "HIGH_RISK": 2,
}

REVERSE_LABEL_MAP = {
    0: "LOW_RISK",
    1: "MEDIUM_RISK",
    2: "HIGH_RISK",
}


def validate_features(df):
    missing_cols = [
        col for col in FEATURE_COLUMNS
        if col not in df.columns
    ]

    if missing_cols:
        raise ValueError(
            f"Missing feature columns: {missing_cols}. "
            "Run feature_builder.py again."
        )

    if "risk_level" not in df.columns:
        raise ValueError("risk_level column missing.")

    return True


def train_models():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading features from: {FEATURE_FILE}")
    df = pd.read_csv(FEATURE_FILE)
    df = df.fillna(0)

    validate_features(df)

    df = df.copy()
    df["target"] = df["risk_level"].map(LABEL_MAP)

    X = df[FEATURE_COLUMNS]
    y = df["target"]

    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            class_weight="balanced",
        ),
        "GradientBoosting": GradientBoostingClassifier(
            random_state=42,
        ),
    }

    results = {}

    best_model_name = None
    best_model = None
    best_accuracy = -1

    for model_name, model in models.items():
        model.fit(X, y)

        preds = model.predict(X)

        accuracy = accuracy_score(y, preds)

        report = classification_report(
            y,
            preds,
            target_names=[
                "LOW_RISK",
                "MEDIUM_RISK",
                "HIGH_RISK",
            ],
            output_dict=True,
            zero_division=0,
        )

        results[model_name] = {
            "accuracy": accuracy,
            "classification_report": report,
        }

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model_name = model_name
            best_model = model

    model_bundle = {
        "model": best_model,
        "model_name": best_model_name,
        "feature_columns": FEATURE_COLUMNS,
        "label_map": LABEL_MAP,
        "reverse_label_map": REVERSE_LABEL_MAP,
    }

    joblib.dump(model_bundle, MODEL_FILE)

    with open(METRICS_FILE, "w") as file:
        json.dump(
            {
                "best_model": best_model_name,
                "best_accuracy": best_accuracy,
                "results": results,
            },
            file,
            indent=4,
        )

    final_preds = best_model.predict(X)

    output = df[
        [
            "supplier_code",
            "risk_score",
            "risk_level",
        ]
    ].copy()

    output["predicted_risk"] = [
        REVERSE_LABEL_MAP[int(pred)]
        for pred in final_preds
    ]

    print("Production ML training completed successfully.")
    print(f"Best model: {best_model_name}")
    print(f"Best accuracy: {best_accuracy:.4f}")
    print(f"Model saved to: {MODEL_FILE}")
    print(f"Metrics saved to: {METRICS_FILE}")

    print("\nPredictions:")
    print(output)


if __name__ == "__main__":
    train_models()