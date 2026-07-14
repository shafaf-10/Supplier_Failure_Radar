from datetime import datetime

import joblib
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    IsolationForest,
    RandomForestClassifier,
)
from sklearn.metrics import (
    accuracy_score,
    classification_report,
)

from app.infra.paths import MODEL_DIR
from app.ml.anomaly_detector import ANOMALY_FEATURES
from app.ml.drift_detector import save_drift_baseline
from app.ml.holdout_manager import save_holdout_set
from app.ml.model_thresholds import (
    ANOMALY_CONFIG,
    CLASSIFIER_CONFIG,
    MODEL_VERSION_CONFIG,
)
from app.ml.temporal_dataset_builder import (
    build_temporal_training_dataset,
)
from app.observability.logger import setup_logger


logger = setup_logger(__name__)


RISK_MODEL_FILE = MODEL_DIR / "risk_model.pkl"
FUTURE_MODEL_FILE = MODEL_DIR / "future_failure_model.pkl"
ANOMALY_MODEL_FILE = MODEL_DIR / "anomaly_model.pkl"

MODEL_REGISTRY_DIR = MODEL_DIR / "registry"
MAX_MODEL_VERSIONS = MODEL_VERSION_CONFIG[
    "MAX_MODEL_VERSIONS"
]

HOLDOUT_DIR = MODEL_DIR / "holdout"
RISK_HOLDOUT_FILE = (
    HOLDOUT_DIR / "risk_holdout.pkl"
)
FUTURE_HOLDOUT_FILE = (
    HOLDOUT_DIR / "future_holdout.pkl"
)


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

    # Heuristic score is used as a feature only.
    "risk_score",
]


FUTURE_TARGETS = {
    "24h": {
        "column": (
            "observed_service_"
            "unavailability_next_24h"
        ),
        "display_name": "NEXT_24_HOURS",
        "class_names": [
            "AVAILABLE_NEXT_24_HOURS",
            "UNAVAILABLE_NEXT_24_HOURS",
        ],
    },
    "3d": {
        "column": (
            "observed_service_"
            "unavailability_next_3d"
        ),
        "display_name": "NEXT_3_DAYS",
        "class_names": [
            "AVAILABLE_NEXT_3_DAYS",
            "UNAVAILABLE_NEXT_3_DAYS",
        ],
    },
    "7d": {
        "column": (
            "observed_service_"
            "unavailability_next_7d"
        ),
        "display_name": "NEXT_7_DAYS",
        "class_names": [
            "AVAILABLE_NEXT_7_DAYS",
            "UNAVAILABLE_NEXT_7_DAYS",
        ],
    },
}


SEVERITY_TARGET_COLUMN = (
    "future_unavailability_severity_7d"
)

SEVERITY_CLASS_ORDER = [
    "LOW",
    "MEDIUM",
    "HIGH",
]


RISK_LABEL_MAP = {
    "CURRENTLY_STABLE": 0,
    "CURRENTLY_AT_RISK": 1,
}

RISK_REVERSE_LABEL_MAP = {
    0: "CURRENTLY_STABLE",
    1: "CURRENTLY_AT_RISK",
}


def validate_columns(
    df: pd.DataFrame,
    columns: list[str],
) -> None:
    missing = [
        column
        for column in columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns: {missing}"
        )


def get_current_operational_risk_target(
    df: pd.DataFrame,
) -> pd.Series:
    """
    Build the current-state operational risk target.

    This target uses only information available at the
    current snapshot. It does not use future labels.
    """

    required_columns = [
        "b_failure_rate",
        "bp_error_rate",
        "bp_stuck_rate",
        "bp_high_retry_rate",
        "ss_failure_rate",
        "ss_timeout_rate",
        "ss_completion_gap_rate",
    ]

    validate_columns(
        df,
        required_columns,
    )

    booking_problem = (
        pd.to_numeric(
            df["b_failure_rate"],
            errors="coerce",
        ).fillna(0)
        >= 0.20
    )

    process_problem = (
        (
            pd.to_numeric(
                df["bp_error_rate"],
                errors="coerce",
            ).fillna(0)
            >= 0.20
        )
        | (
            pd.to_numeric(
                df["bp_stuck_rate"],
                errors="coerce",
            ).fillna(0)
            >= 0.25
        )
        | (
            pd.to_numeric(
                df["bp_high_retry_rate"],
                errors="coerce",
            ).fillna(0)
            >= 0.25
        )
    )

    search_problem = (
        (
            pd.to_numeric(
                df["ss_failure_rate"],
                errors="coerce",
            ).fillna(0)
            >= 0.20
        )
        | (
            pd.to_numeric(
                df["ss_timeout_rate"],
                errors="coerce",
            ).fillna(0)
            >= 0.10
        )
        | (
            pd.to_numeric(
                df["ss_completion_gap_rate"],
                errors="coerce",
            ).fillna(0)
            >= 0.20
        )
    )

    signal_count = (
        booking_problem.astype(int)
        + process_problem.astype(int)
        + search_problem.astype(int)
    )

    return (
        signal_count >= 2
    ).astype(int)


def get_future_target(
    df: pd.DataFrame,
    target_column: str,
) -> pd.Series:
    if target_column not in df.columns:
        raise ValueError(
            f"{target_column} column missing. "
            "Run the updated temporal dataset builder."
        )

    return (
        pd.to_numeric(
            df[target_column],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )


def get_future_severity_target(
    df: pd.DataFrame,
) -> tuple[
    pd.Series,
    dict[str, int],
    dict[int, str],
]:
    if SEVERITY_TARGET_COLUMN not in df.columns:
        raise ValueError(
            f"{SEVERITY_TARGET_COLUMN} column "
            "missing. Run the updated temporal "
            "dataset builder."
        )

    severity_values = (
        df[SEVERITY_TARGET_COLUMN]
        .fillna("LOW")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    invalid_values = (
        set(severity_values.unique())
        - set(SEVERITY_CLASS_ORDER)
    )

    if invalid_values:
        raise ValueError(
            "Invalid future severity values: "
            f"{sorted(invalid_values)}"
        )

    severity_label_map = {
        severity: index
        for index, severity in enumerate(
            SEVERITY_CLASS_ORDER
        )
    }

    severity_reverse_label_map = {
        index: severity
        for severity, index
        in severity_label_map.items()
    }

    encoded_target = (
        severity_values
        .map(severity_label_map)
        .astype(int)
    )

    return (
        encoded_target,
        severity_label_map,
        severity_reverse_label_map,
    )


def evaluate_model(
    model,
    X: pd.DataFrame,
    y: pd.Series,
    class_names: list[str],
    time_column: pd.Series | None = None,
    holdout_file=None,
) -> tuple[float, dict]:
    if len(y) == 0:
        raise ValueError(
            "Cannot train a model with an empty target."
        )

    if y.nunique() < 2:
        raise ValueError(
            "Target contains only one class. "
            f"Distribution: {y.value_counts().to_dict()}"
        )

    if len(y) < 10:
        model.fit(X, y)
        predictions = model.predict(X)

        if holdout_file is not None:
            save_holdout_set(
                X,
                y,
                holdout_file,
            )

        return (
            accuracy_score(
                y,
                predictions,
            ),
            classification_report(
                y,
                predictions,
                labels=list(
                    range(len(class_names))
                ),
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

    split_df["feature_snapshot_date"] = (
        pd.to_datetime(
            time_column.values,
            errors="coerce",
        )
    )

    split_df = (
        split_df
        .dropna(
            subset=["feature_snapshot_date"]
        )
        .sort_values(
            "feature_snapshot_date"
        )
        .reset_index(drop=True)
    )

    if split_df.empty:
        raise ValueError(
            "No valid feature snapshot dates "
            "were available for temporal splitting."
        )

    test_size = CLASSIFIER_CONFIG[
        "TEST_SIZE"
    ]

    test_count = max(
        1,
        int(len(split_df) * test_size),
    )

    if test_count >= len(split_df):
        test_count = max(
            1,
            len(split_df) - 1,
        )

    train_df = split_df.iloc[
        :-test_count
    ].copy()

    test_df = split_df.iloc[
        -test_count:
    ].copy()

    X_train = train_df[X.columns]

    y_train = (
        train_df["target"]
        .astype(int)
    )

    X_test = test_df[X.columns]

    y_test = (
        test_df["target"]
        .astype(int)
    )

    if y_train.nunique() < 2:
        logger.warning(
            "Temporal training split contains "
            "only one target class. Training and "
            "evaluating on the complete dataset."
        )

        model.fit(X, y)
        predictions = model.predict(X)

        if holdout_file is not None:
            save_holdout_set(
                X,
                y,
                holdout_file,
            )

        return (
            accuracy_score(
                y,
                predictions,
            ),
            classification_report(
                y,
                predictions,
                labels=list(
                    range(len(class_names))
                ),
                target_names=class_names,
                output_dict=True,
                zero_division=0,
            ),
        )

    if holdout_file is not None:
        save_holdout_set(
            X_test,
            y_test,
            holdout_file,
        )

    model.fit(
        X_train,
        y_train,
    )

    predictions = model.predict(
        X_test
    )

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    report = classification_report(
        y_test,
        predictions,
        labels=list(
            range(len(class_names))
        ),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    # Retrain the selected candidate on all data
    # after temporal evaluation.
    model.fit(
        X,
        y,
    )

    return accuracy, report


def train_best_classifier(
    X: pd.DataFrame,
    y: pd.Series,
    class_names: list[str],
    time_column: pd.Series | None = None,
    holdout_file=None,
) -> tuple[str, object, float]:
    models = {
        "RandomForest": (
            RandomForestClassifier(
                n_estimators=(
                    CLASSIFIER_CONFIG[
                        "N_ESTIMATORS"
                    ]
                ),
                random_state=(
                    CLASSIFIER_CONFIG[
                        "RANDOM_STATE"
                    ]
                ),
                class_weight="balanced",
            )
        ),
        "GradientBoosting": (
            GradientBoostingClassifier(
                random_state=(
                    CLASSIFIER_CONFIG[
                        "RANDOM_STATE"
                    ]
                ),
            )
        ),
    }

    best_model_name = ""
    best_model = None
    best_accuracy = -1.0

    for model_name, model in models.items():
        accuracy, _ = evaluate_model(
            model=model,
            X=X,
            y=y,
            class_names=class_names,
            time_column=time_column,
            holdout_file=holdout_file,
        )

        logger.info(
            "%s candidate accuracy: %.4f",
            model_name,
            accuracy,
        )

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model_name = model_name
            best_model = model

    if best_model is None:
        raise RuntimeError(
            "No classifier was successfully trained."
        )

    return (
        best_model_name,
        best_model,
        best_accuracy,
    )


def cleanup_old_model_versions(
    pattern: str,
) -> None:
    model_files = sorted(
        MODEL_REGISTRY_DIR.glob(pattern),
        key=lambda file: (
            file.stat().st_mtime
        ),
        reverse=True,
    )

    for old_file in model_files[
        MAX_MODEL_VERSIONS:
    ]:
        old_file.unlink()

        logger.info(
            "Deleted old model version: %s",
            old_file,
        )


def train_models(
    df: pd.DataFrame | None = None,
) -> None:
    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    MODEL_REGISTRY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    HOLDOUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    versioned_risk_model_file = (
        MODEL_REGISTRY_DIR
        / f"risk_model_{timestamp}.pkl"
    )

    versioned_future_model_file = (
        MODEL_REGISTRY_DIR
        / f"future_failure_model_{timestamp}.pkl"
    )

    versioned_anomaly_model_file = (
        MODEL_REGISTRY_DIR
        / f"anomaly_model_{timestamp}.pkl"
    )

    if df is None:
        logger.info(
            "Building temporal supplier "
            "training dataset in memory..."
        )

        df = (
            build_temporal_training_dataset()
        )

    df = df.copy()

    validate_columns(
        df,
        FEATURE_COLUMNS,
    )

    validate_columns(
        df,
        ANOMALY_FEATURES,
    )

    if "feature_snapshot_date" not in df.columns:
        raise ValueError(
            "feature_snapshot_date column missing."
        )

    required_future_columns = [
        config["column"]
        for config
        in FUTURE_TARGETS.values()
    ]

    required_future_columns.append(
        SEVERITY_TARGET_COLUMN
    )

    validate_columns(
        df,
        required_future_columns,
    )

    numeric_columns = list(
        dict.fromkeys(
            FEATURE_COLUMNS
            + ANOMALY_FEATURES
        )
    )

    for column in numeric_columns:
        df[column] = (
            pd.to_numeric(
                df[column],
                errors="coerce",
            )
            .fillna(0)
        )

    df["feature_snapshot_date"] = (
        pd.to_datetime(
            df["feature_snapshot_date"],
            errors="coerce",
        )
    )

    df = df.dropna(
        subset=["feature_snapshot_date"]
    ).copy()

    if df.empty:
        raise ValueError(
            "No valid temporal training rows "
            "remain after date conversion."
        )

    save_drift_baseline(
        df,
        FEATURE_COLUMNS,
    )

    time_column = df[
        "feature_snapshot_date"
    ]

    # -------------------------------------------------
    # Current operational risk model
    # -------------------------------------------------

    X_risk = df[
        FEATURE_COLUMNS
    ].fillna(0)

    y_risk = (
        get_current_operational_risk_target(
            df
        )
    )

    logger.info(
        "Current risk target distribution: %s",
        y_risk.value_counts().to_dict(),
    )

    (
        risk_model_name,
        risk_model,
        risk_accuracy,
    ) = train_best_classifier(
        X=X_risk,
        y=y_risk,
        class_names=[
            "CURRENTLY_STABLE",
            "CURRENTLY_AT_RISK",
        ],
        time_column=time_column,
        holdout_file=RISK_HOLDOUT_FILE,
    )

    risk_bundle = {
        "model": risk_model,
        "model_name": risk_model_name,
        "feature_columns": FEATURE_COLUMNS,
        "label_map": RISK_LABEL_MAP,
        "reverse_label_map": (
            RISK_REVERSE_LABEL_MAP
        ),
        "target": (
            "current_operational_risk"
        ),
        "prediction_horizon": (
            "CURRENT_STATE"
        ),
        "accuracy": risk_accuracy,
        "model_purpose": (
            "Classify the supplier's current "
            "operational risk using booking, "
            "process, search, ticketing, refund, "
            "credit, wallet and time-series "
            "conditions available at the current "
            "feature snapshot."
        ),
    }

    joblib.dump(
        risk_bundle,
        RISK_MODEL_FILE,
    )

    joblib.dump(
        risk_bundle,
        versioned_risk_model_file,
    )

    # -------------------------------------------------
    # Multi-horizon future models
    # -------------------------------------------------

    X_future = df[
        FEATURE_COLUMNS
    ].fillna(0)

    future_models = {}
    future_model_names = {}
    future_accuracies = {}
    future_target_distributions = {}

    for (
        horizon_key,
        horizon_config,
    ) in FUTURE_TARGETS.items():
        target_column = (
            horizon_config["column"]
        )

        class_names = (
            horizon_config["class_names"]
        )

        y_future = get_future_target(
            df,
            target_column,
        )

        target_distribution = (
            y_future
            .value_counts()
            .to_dict()
        )

        future_target_distributions[
            horizon_key
        ] = target_distribution

        logger.info(
            "Future %s target distribution: %s",
            horizon_config[
                "display_name"
            ],
            target_distribution,
        )

        holdout_file = (
            FUTURE_HOLDOUT_FILE
            if horizon_key == "7d"
            else None
        )

        (
            future_model_name,
            future_model,
            future_accuracy,
        ) = train_best_classifier(
            X=X_future,
            y=y_future,
            class_names=class_names,
            time_column=time_column,
            holdout_file=holdout_file,
        )

        future_models[
            horizon_key
        ] = future_model

        future_model_names[
            horizon_key
        ] = future_model_name

        future_accuracies[
            horizon_key
        ] = future_accuracy

    # -------------------------------------------------
    # Future severity model
    # -------------------------------------------------

    (
        y_severity,
        severity_label_map,
        severity_reverse_label_map,
    ) = get_future_severity_target(df)

    severity_distribution = (
        df[SEVERITY_TARGET_COLUMN]
        .fillna("LOW")
        .astype(str)
        .str.upper()
        .str.strip()
        .value_counts()
        .to_dict()
    )

    logger.info(
        "Future severity target distribution: %s",
        severity_distribution,
    )

    (
        severity_model_name,
        severity_model,
        severity_accuracy,
    ) = train_best_classifier(
        X=X_future,
        y=y_severity,
        class_names=SEVERITY_CLASS_ORDER,
        time_column=time_column,
        holdout_file=None,
    )

    future_bundle = {
        "models": future_models,
        "model_names": future_model_names,
        "feature_columns": FEATURE_COLUMNS,
        "targets": {
            horizon_key: config["column"]
            for horizon_key, config
            in FUTURE_TARGETS.items()
        },
        "horizon_display_names": {
            horizon_key: (
                config["display_name"]
            )
            for horizon_key, config
            in FUTURE_TARGETS.items()
        },
        "class_names": {
            horizon_key: (
                config["class_names"]
            )
            for horizon_key, config
            in FUTURE_TARGETS.items()
        },
        "target_distributions": (
            future_target_distributions
        ),
        "accuracies": future_accuracies,
        "severity_model": severity_model,
        "severity_model_name": (
            severity_model_name
        ),
        "severity_target": (
            SEVERITY_TARGET_COLUMN
        ),
        "severity_label_map": (
            severity_label_map
        ),
        "severity_reverse_label_map": (
            severity_reverse_label_map
        ),
        "severity_accuracy": (
            severity_accuracy
        ),
        "prediction_horizons": [
            "NEXT_24_HOURS",
            "NEXT_3_DAYS",
            "NEXT_7_DAYS",
        ],
        "model_purpose": (
            "Predict supplier service "
            "unavailability independently for "
            "the next 24 hours, next 3 days and "
            "next 7 days, and classify expected "
            "7-day service-unavailability "
            "severity as LOW, MEDIUM or HIGH."
        ),
    }

    joblib.dump(
        future_bundle,
        FUTURE_MODEL_FILE,
    )

    joblib.dump(
        future_bundle,
        versioned_future_model_file,
    )

    # -------------------------------------------------
    # Current-state anomaly model
    # -------------------------------------------------

    X_anomaly = df[
        ANOMALY_FEATURES
    ].fillna(0)

    anomaly_model = IsolationForest(
        n_estimators=(
            ANOMALY_CONFIG[
                "N_ESTIMATORS"
            ]
        ),
        contamination=(
            ANOMALY_CONFIG[
                "CONTAMINATION"
            ]
        ),
        random_state=(
            ANOMALY_CONFIG[
                "RANDOM_STATE"
            ]
        ),
    )

    anomaly_model.fit(
        X_anomaly
    )

    anomaly_bundle = {
        "model": anomaly_model,
        "feature_columns": (
            ANOMALY_FEATURES
        ),
        "detection_scope": (
            "CURRENT_STATE"
        ),
        "prediction_horizon": None,
        "model_purpose": (
            "Detect unusual supplier behaviour "
            "in the current feature snapshot. "
            "This Isolation Forest model does "
            "not predict future service "
            "unavailability."
        ),
    }

    joblib.dump(
        anomaly_bundle,
        ANOMALY_MODEL_FILE,
    )

    joblib.dump(
        anomaly_bundle,
        versioned_anomaly_model_file,
    )

    # -------------------------------------------------
    # Registry cleanup and final logs
    # -------------------------------------------------

    cleanup_old_model_versions(
        "risk_model_*.pkl"
    )

    cleanup_old_model_versions(
        "future_failure_model_*.pkl"
    )

    cleanup_old_model_versions(
        "anomaly_model_*.pkl"
    )

    logger.info(
        "Production ML training completed "
        "successfully."
    )

    logger.info(
        "Risk model saved to: %s",
        RISK_MODEL_FILE,
    )

    logger.info(
        "Future model bundle saved to: %s",
        FUTURE_MODEL_FILE,
    )

    logger.info(
        "Anomaly model saved to: %s",
        ANOMALY_MODEL_FILE,
    )

    logger.info(
        "Risk accuracy: %.4f",
        risk_accuracy,
    )

    logger.info(
        "Future 24h accuracy: %.4f",
        future_accuracies["24h"],
    )

    logger.info(
        "Future 3d accuracy: %.4f",
        future_accuracies["3d"],
    )

    logger.info(
        "Future 7d accuracy: %.4f",
        future_accuracies["7d"],
    )

    logger.info(
        "Future severity accuracy: %.4f",
        severity_accuracy,
    )

    logger.info(
        "Created model files: "
        "risk_model.pkl, "
        "future_failure_model.pkl, "
        "anomaly_model.pkl"
    )


if __name__ == "__main__":
    train_models()

