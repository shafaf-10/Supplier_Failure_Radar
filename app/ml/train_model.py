from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    IsolationForest,
)
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from app.ml.feature_builder import build_supplier_features
from app.ml.anomaly_detector import ANOMALY_FEATURES


ROOT_DIR = Path(__file__).resolve().parents[2]

MODEL_DIR = ROOT_DIR / "app" / "ml" / "models"
RISK_MODEL_FILE = MODEL_DIR / "risk_model.pkl"
FUTURE_MODEL_FILE = MODEL_DIR / "future_failure_model.pkl"
ANOMALY_MODEL_FILE = MODEL_DIR / "anomaly_model.pkl"


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


def validate_columns(df, columns):
    missing = [col for col in columns if col not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")


def create_future_failure_target(df):
    future_failure = (
        (df["risk_score"] >= 30)
        | (
            (df["risk_score"] >= 18)
            & (
                (df["b_failure_rate"] >= 0.08)
                | (df["bp_error_rate"] >= 0.15)
                | (df["ss_failure_rate"] >= 0.25)
                | (df["ss_timeout_rate"] >= 0.18)
            )
        )
        | (
            (df["risk_score"] >= 15)
            & (
                (df["wt_wallet_risk_score_100"] >= 12)
                | (df["cr_rejection_rate"] >= 0.15)
            )
        )
    )

    return future_failure.astype(int)


def evaluate_model(model, X, y, class_names):
    if len(y) < 10 or y.nunique() < 2:
        model.fit(X, y)
        preds = model.predict(X)

        return (
            accuracy_score(y, preds),
            classification_report(
                y,
                preds,
                labels=list(range(len(class_names))),
                target_names=class_names,
                output_dict=True,
                zero_division=0,
            ),
        )

    stratify_value = y if y.value_counts().min() >= 2 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.30,
        random_state=42,
        stratify=stratify_value,
    )

    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    accuracy = accuracy_score(y_test, preds)

    report = classification_report(
        y_test,
        preds,
        labels=list(range(len(class_names))),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    model.fit(X, y)

    return accuracy, report


def train_best_classifier(X, y, class_names):
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

    best_model_name = None
    best_model = None
    best_accuracy = -1

    for model_name, model in models.items():
        accuracy, _ = evaluate_model(
            model,
            X,
            y,
            class_names,
        )

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model_name = model_name
            best_model = model

    return best_model_name, best_model, best_accuracy


def train_models():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("Building supplier features in memory...")
    df = build_supplier_features(persist=False)
    df = df.fillna(0).copy()

    validate_columns(df, FEATURE_COLUMNS)
    validate_columns(df, ANOMALY_FEATURES)

    if "risk_level" not in df.columns:
        raise ValueError("risk_level column missing.")

    df["risk_target"] = df["risk_level"].map(LABEL_MAP)

    if df["risk_target"].isna().any():
        raise ValueError("risk_level contains unknown values.")

    X_risk = df[FEATURE_COLUMNS].fillna(0)
    y_risk = df["risk_target"].astype(int)

    risk_model_name, risk_model, risk_accuracy = train_best_classifier(
        X_risk,
        y_risk,
        ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"],
    )

    risk_bundle = {
        "model": risk_model,
        "model_name": risk_model_name,
        "feature_columns": FEATURE_COLUMNS,
        "label_map": LABEL_MAP,
        "reverse_label_map": REVERSE_LABEL_MAP,
        "model_purpose": "Current supplier risk classification",
    }

    joblib.dump(risk_bundle, RISK_MODEL_FILE)

    df["future_failure_7d"] = create_future_failure_target(df)
    y_future = df["future_failure_7d"].astype(int)

    future_model_name, future_model, future_accuracy = train_best_classifier(
        X_risk,
        y_future,
        ["STABLE_NEXT_7D", "FAILURE_RISK_NEXT_7D"],
    )

    future_bundle = {
        "model": future_model,
        "model_name": future_model_name,
        "feature_columns": FEATURE_COLUMNS,
        "target": "future_failure_7d",
        "model_purpose": "Future supplier instability probability for next 7 days",
    }

    joblib.dump(future_bundle, FUTURE_MODEL_FILE)

    X_anomaly = df[ANOMALY_FEATURES].fillna(0)

    anomaly_model = IsolationForest(
        n_estimators=300,
        contamination=0.20,
        random_state=42,
    )

    anomaly_model.fit(X_anomaly)
    joblib.dump(anomaly_model, ANOMALY_MODEL_FILE)

    print("Production ML training completed successfully.")
    print(f"Risk model saved to: {RISK_MODEL_FILE}")
    print(f"Future model saved to: {FUTURE_MODEL_FILE}")
    print(f"Anomaly model saved to: {ANOMALY_MODEL_FILE}")
    print(f"Risk accuracy: {risk_accuracy:.4f}")
    print(f"Future accuracy: {future_accuracy:.4f}")

    print("\nCreated model files:")
    print("- risk_model.pkl")
    print("- future_failure_model.pkl")
    print("- anomaly_model.pkl")


if __name__ == "__main__":
    train_models()