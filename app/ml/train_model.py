from datetime import datetime

import joblib
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    IsolationForest,
    RandomForestClassifier,
)
from sklearn.metrics import accuracy_score, classification_report

from app.infra.paths import MODEL_DIR
from app.ml.anomaly_detector import ANOMALY_FEATURES
from app.ml.drift_detector import save_drift_baseline
from app.ml.feature_builder import build_supplier_features
from app.ml.holdout_manager import save_holdout_set
from app.ml.model_thresholds import (
    ANOMALY_CONFIG,
    CLASSIFIER_CONFIG,
    MODEL_VERSION_CONFIG,
)
from app.observability.logger import setup_logger


logger = setup_logger(__name__)

RISK_MODEL_FILE = MODEL_DIR / "risk_model.pkl"
FUTURE_MODEL_FILE = MODEL_DIR / "future_failure_model.pkl"
ANOMALY_MODEL_FILE = MODEL_DIR / "anomaly_model.pkl"

MODEL_REGISTRY_DIR = MODEL_DIR / "registry"
MAX_MODEL_VERSIONS = MODEL_VERSION_CONFIG["MAX_MODEL_VERSIONS"]

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

    # Time-series features
    "failure_rate_7d",
    "failure_rate_30d",
    "failure_rate_change_7d",
    "failure_rate_change_30d",
    "booking_volume_7d",
    "booking_volume_30d",
    "booking_volume_momentum",

    # Heuristic score is now only a feature, not target
    "risk_score",
]


RISK_LABEL_MAP = {
    "STABLE_SUPPLIER": 0,
    "OBSERVED_FAILURE_SUPPLIER": 1,
}

RISK_REVERSE_LABEL_MAP = {
    0: "STABLE_SUPPLIER",
    1: "OBSERVED_FAILURE_SUPPLIER",
}


def validate_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")


def get_observed_future_failure_target(df: pd.DataFrame) -> pd.Series:
    label_column = "observed_failure_next_7d"

    if label_column not in df.columns:
        raise ValueError(
            "observed_failure_next_7d column missing. "
            "Future failure model must train on real observed failures."
        )

    return df[label_column].fillna(0).astype(int)


def evaluate_model(
    model,
    X: pd.DataFrame,
    y: pd.Series,
    class_names: list[str],
    time_column: pd.Series | None = None,
) -> tuple[float, dict]:
    if len(y) < 10 or y.nunique() < 2:
        model.fit(X, y)
        preds = model.predict(X)

        if class_names == ["STABLE_SUPPLIER", "OBSERVED_FAILURE_SUPPLIER"]:
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

    if time_column is None:
        raise ValueError(
            "feature_snapshot_date missing. "
            "Temporal split requires a time column."
        )

    split_df = X.copy()
    split_df["target"] = y.values
    split_df["feature_snapshot_date"] = pd.to_datetime(
        time_column.values,
        errors="coerce",
    )

    split_df = split_df.sort_values("feature_snapshot_date").reset_index(drop=True)

    test_size = CLASSIFIER_CONFIG["TEST_SIZE"]
    test_count = max(1, int(len(split_df) * test_size))

    train_df = split_df.iloc[:-test_count]
    test_df = split_df.iloc[-test_count:]

    X_train = train_df[X.columns]
    y_train = train_df["target"].astype(int)

    X_test = test_df[X.columns]
    y_test = test_df["target"].astype(int)

    if y_train.nunique() < 2:
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

    if class_names == ["STABLE_SUPPLIER", "OBSERVED_FAILURE_SUPPLIER"]:
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
    time_column: pd.Series | None = None,
) -> tuple[str, object, float]:
    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=CLASSIFIER_CONFIG["N_ESTIMATORS"],
            random_state=CLASSIFIER_CONFIG["RANDOM_STATE"],
            class_weight="balanced",
        ),
        "GradientBoosting": GradientBoostingClassifier(
            random_state=CLASSIFIER_CONFIG["RANDOM_STATE"],
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
            time_column=time_column,
        )

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model_name = model_name
            best_model = model

    return best_model_name, best_model, best_accuracy


def cleanup_old_model_versions(pattern: str) -> None:
    model_files = sorted(
        MODEL_REGISTRY_DIR.glob(pattern),
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )

    for old_file in model_files[MAX_MODEL_VERSIONS:]:
        old_file.unlink()
        logger.info("Deleted old model version: %s", old_file)


def train_models(df: pd.DataFrame | None = None) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    versioned_risk_model_file = MODEL_REGISTRY_DIR / f"risk_model_{timestamp}.pkl"
    versioned_future_model_file = MODEL_REGISTRY_DIR / f"future_failure_model_{timestamp}.pkl"
    versioned_anomaly_model_file = MODEL_REGISTRY_DIR / f"anomaly_model_{timestamp}.pkl"

    if df is None:
        logger.info("Building supplier features in memory...")
        df = build_supplier_features(days=None)

    df = df.fillna(0).copy()

    validate_columns(df, FEATURE_COLUMNS)
    validate_columns(df, ANOMALY_FEATURES)

    if "feature_snapshot_date" not in df.columns:
        raise ValueError("feature_snapshot_date column missing.")

    if "observed_failure_next_7d" not in df.columns:
        raise ValueError("observed_failure_next_7d column missing.")

    save_drift_baseline(df, FEATURE_COLUMNS)

    X_risk = df[FEATURE_COLUMNS].fillna(0)

    # Risk model now trains on observed outcomes, not risk_level heuristic.
    y_risk = df["observed_failure_next_7d"].astype(int)

    risk_model_name, risk_model, risk_accuracy = train_best_classifier(
        X_risk,
        y_risk,
        ["STABLE_SUPPLIER", "OBSERVED_FAILURE_SUPPLIER"],
        time_column=df["feature_snapshot_date"],
    )

    risk_bundle = {
        "model": risk_model,
        "model_name": risk_model_name,
        "feature_columns": FEATURE_COLUMNS,
        "label_map": RISK_LABEL_MAP,
        "reverse_label_map": RISK_REVERSE_LABEL_MAP,
        "model_purpose": "Observed supplier failure classification",
    }

    joblib.dump(risk_bundle, RISK_MODEL_FILE)
    joblib.dump(risk_bundle, versioned_risk_model_file)

    df["future_failure_7d"] = get_observed_future_failure_target(df)
    y_future = df["future_failure_7d"].astype(int)

    future_model_name, future_model, future_accuracy = train_best_classifier(
        X_risk,
        y_future,
        ["STABLE_NEXT_7D", "FAILURE_RISK_NEXT_7D"],
        time_column=df["feature_snapshot_date"],
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
        n_estimators=ANOMALY_CONFIG["N_ESTIMATORS"],
        contamination=ANOMALY_CONFIG["CONTAMINATION"],
        random_state=ANOMALY_CONFIG["RANDOM_STATE"],
    )

    anomaly_model.fit(X_anomaly)
    joblib.dump(anomaly_model, ANOMALY_MODEL_FILE)
    joblib.dump(anomaly_model, versioned_anomaly_model_file)

    cleanup_old_model_versions("risk_model_*.pkl")
    cleanup_old_model_versions("future_failure_model_*.pkl")
    cleanup_old_model_versions("anomaly_model_*.pkl")

    logger.info("Production ML training completed successfully.")
    logger.info("Risk model saved to: %s", RISK_MODEL_FILE)
    logger.info("Future model saved to: %s", FUTURE_MODEL_FILE)
    logger.info("Anomaly model saved to: %s", ANOMALY_MODEL_FILE)
    logger.info("Risk accuracy: %.4f", risk_accuracy)
    logger.info("Future accuracy: %.4f", future_accuracy)
    logger.info(
        "Created model files: risk_model.pkl, future_failure_model.pkl, anomaly_model.pkl"
    )


if __name__ == "__main__":
    train_models()