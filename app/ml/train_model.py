from app.ml.drift_detector import save_drift_baseline
from datetime import datetime
from pathlib import Path
from app.ml.model_thresholds import FUTURE_FAILURE_THRESHOLDS

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
MODEL_REGISTRY_DIR = MODEL_DIR / "registry"
HOLDOUT_DIR = MODEL_DIR / "holdout"
RISK_HOLDOUT_FILE = HOLDOUT_DIR / "risk_holdout.pkl"
FUTURE_HOLDOUT_FILE = HOLDOUT_DIR / "future_holdout.pkl"


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


def validate_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")


def create_future_failure_target(df: pd.DataFrame) -> pd.Series:
    t = FUTURE_FAILURE_THRESHOLDS

    future_failure = (
        (df["risk_score"] >= t["HIGH_RISK_SCORE"])
        | (
            (df["risk_score"] >= t["MEDIUM_RISK_SCORE"])
            & (
                (df["b_failure_rate"] >= t["BOOKING_FAILURE_RATE"])
                | (df["bp_error_rate"] >= t["PROCESS_ERROR_RATE"])
                | (df["ss_failure_rate"] >= t["SEARCH_FAILURE_RATE"])
                | (df["ss_timeout_rate"] >= t["SEARCH_TIMEOUT_RATE"])
            )
        )
        | (
            (df["risk_score"] >= t["LOW_SIGNAL_RISK_SCORE"])
            & (
                (df["wt_wallet_risk_score_100"] >= t["WALLET_RISK_SCORE"])
                | (df["cr_rejection_rate"] >= t["CREDIT_REJECTION_RATE"])
            )
        )
    )

    return future_failure.astype(int)

def save_holdout_set(
    X_test: pd.DataFrame,
    y_test: pd.Series,
    file_path: Path,
) -> None:
    HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)

    holdout_data = {
        "X_test": X_test,
        "y_test": y_test,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    joblib.dump(holdout_data, file_path)
def evaluate_model(
    model,
    X: pd.DataFrame,
    y: pd.Series,
    class_names: list[str],
) -> tuple[float, dict]:
    if len(y) < 10 or y.nunique() < 2:
        model.fit(X, y)
        preds = model.predict(X)
        if class_names == ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"]:
            save_holdout_set(X, y, RISK_HOLDOUT_FILE)

        if class_names == ["STABLE_NEXT_7D", "FAILURE_RISK_NEXT_7D"]:
            save_holdout_set(X, y, FUTURE_HOLDOUT_FILE)

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
    if class_names == ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"]:
        save_holdout_set(X_test, y_test, RISK_HOLDOUT_FILE)

    if class_names == ["STABLE_NEXT_7D", "FAILURE_RISK_NEXT_7D"]:
        save_holdout_set(X_test, y_test, FUTURE_HOLDOUT_FILE)

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


def train_best_classifier(
    X: pd.DataFrame,
    y: pd.Series,
    class_names: list[str],
) -> tuple[str, object, float]:
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


def train_models() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    versioned_risk_model_file = MODEL_REGISTRY_DIR / f"risk_model_{timestamp}.pkl"
    versioned_future_model_file = MODEL_REGISTRY_DIR / f"future_failure_model_{timestamp}.pkl"
    versioned_anomaly_model_file = MODEL_REGISTRY_DIR / f"anomaly_model_{timestamp}.pkl"

    print("Building supplier features in memory...")
    df = build_supplier_features(days=None)
    df = df.fillna(0).copy()

    validate_columns(df, FEATURE_COLUMNS)
    validate_columns(df, ANOMALY_FEATURES)
    save_drift_baseline(df, FEATURE_COLUMNS)

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
    joblib.dump(risk_bundle, versioned_risk_model_file)
    joblib.dump(risk_bundle, versioned_risk_model_file)

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
    joblib.dump(future_bundle, versioned_future_model_file)

    X_anomaly = df[ANOMALY_FEATURES].fillna(0)

    anomaly_model = IsolationForest(
        n_estimators=300,
        contamination=0.20,
        random_state=42,
    )

    anomaly_model.fit(X_anomaly)
    joblib.dump(anomaly_model, ANOMALY_MODEL_FILE)
    joblib.dump(anomaly_model, versioned_anomaly_model_file)

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