import joblib
import pandas as pd

from app.infra.paths import MODEL_DIR
from app.ml.future_risk_predictor import (
    add_future_risk_predictions,
    get_early_warning_status,
    get_future_prediction_confidence,
)
from app.ml.prediction_recommendations import (
    get_recommendation,
)
from app.observability.logger import setup_logger


logger = setup_logger(__name__)


MODEL_FILE = MODEL_DIR / "risk_model.pkl"
FUTURE_MODEL_FILE = (
    MODEL_DIR / "future_failure_model.pkl"
)
ANOMALY_MODEL_FILE = (
    MODEL_DIR / "anomaly_model.pkl"
)


ANOMALY_FEATURES = [
    "b_failure_rate",
    "b_pending_rate",
    "b_cancellation_rate",
    "b_deadline_miss_rate",
    "bp_error_rate",
    "bp_stuck_rate",
    "bp_high_retry_rate",
    "booking_not_issued_rate",
    "supplier_pnr_missing_rate",
    "ticket_number_missing_rate",
    "ss_failure_rate",
    "ss_partial_rate",
    "ss_timeout_rate",
    "ss_completion_gap_rate",
    "rr_pending_rate",
    "rr_rejected_rate",
    "rr_refund_risk_score_100",
    "cr_rejection_rate",
    "cr_overdue_rate",
    "cr_credit_risk_score_100",
    "wt_failed_payment_rate",
    "wt_hold_rate",
    "wt_wallet_risk_score_100",
]


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
            f"Missing columns: {missing}. "
            "Run feature_builder.py again."
        )


def get_risk_prediction_probability(
    model,
    input_values: pd.DataFrame,
) -> list[float]:
    if hasattr(
        model,
        "predict_proba",
    ):
        probabilities = model.predict_proba(
            input_values
        )

        return probabilities.max(
            axis=1
        ).tolist()

    return [
        0.0
        for _ in range(
            len(input_values)
        )
    ]


def get_positive_class_probability(
    model,
    input_values: pd.DataFrame,
) -> list[float]:
    if hasattr(
        model,
        "predict_proba",
    ):
        probabilities = model.predict_proba(
            input_values
        )

        model_classes = list(
            model.classes_
        )

        if 1 in model_classes:
            positive_class_index = (
                model_classes.index(1)
            )

            return probabilities[
                :,
                positive_class_index,
            ].tolist()

        return [
            0.0
            for _ in range(
                len(input_values)
            )
        ]

    predictions = model.predict(
        input_values
    )

    return [
        float(prediction)
        for prediction in predictions
    ]


def get_highest_risk_horizon(
    row: pd.Series,
) -> str:
    horizon_probabilities = {
        "NEXT_24_HOURS": float(
            row.get(
                "future_probability_24h",
                0,
            )
            or 0
        ),
        "NEXT_3_DAYS": float(
            row.get(
                "future_probability_3d",
                0,
            )
            or 0
        ),
        "NEXT_7_DAYS": float(
            row.get(
                "future_probability_7d",
                0,
            )
            or 0
        ),
    }

    return max(
        horizon_probabilities,
        key=horizon_probabilities.get,
    )


def build_ml_future_recommendation(
    row: pd.Series,
) -> str:
    probability = float(
        row.get(
            "future_instability_probability",
            0,
        )
        or 0
    )

    probability_pct = round(
        probability * 100,
        1,
    )

    lead_signal = row.get(
        "lead_signal",
        "Operational Risk",
    )

    warning_status = row.get(
        "early_warning_status",
        "STABLE",
    )

    future_risk_window = row.get(
        "future_risk_window",
        "NEXT_7_DAYS",
    )

    readable_horizon = {
        "NEXT_24_HOURS": (
            "the next 24 hours"
        ),
        "NEXT_3_DAYS": (
            "the next 3 days"
        ),
        "NEXT_7_DAYS": (
            "the next 7 days"
        ),
    }.get(
        future_risk_window,
        "the next 7 days",
    )

    if warning_status == "CRITICAL_WARNING":
        return (
            "ML model predicts a high probability "
            f"of supplier instability in "
            f"{readable_horizon} "
            f"({probability_pct}%). "
            f"Primary lead signal: {lead_signal}. "
            "Prepare a backup supplier, reduce "
            "dependency, and monitor closely."
        )

    if warning_status == "WARNING":
        return (
            "ML model shows warning signs for "
            f"possible supplier instability in "
            f"{readable_horizon} "
            f"({probability_pct}%). "
            f"Primary lead signal: {lead_signal}. "
            "Monitor closely and prepare "
            "fallback routing."
        )

    if warning_status == "WATCHLIST":
        return (
            "The supplier is on the watchlist "
            "based on the ML future-risk model "
            f"({probability_pct}%). "
            f"Main signal: {lead_signal}."
        )

    return (
        "ML model predicts a low instability "
        f"probability for {readable_horizon} "
        f"({probability_pct}%)."
    )


def apply_ml_future_failure_prediction(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply the trained future model when available.

    When the model is missing, retain the weighted
    rule fallback, but explicitly mark it as a
    non-ML heuristic result.
    """

    df = add_future_risk_predictions(
        df
    )

    if not FUTURE_MODEL_FILE.exists():
        logger.warning(
            "Future model bundle not found. "
            "Using non-ML weighted-rules fallback."
        )

        fallback_probability = df[
            "future_instability_probability"
        ].fillna(0)

        df["future_probability_24h"] = (
            fallback_probability
        )

        df["future_probability_3d"] = (
            fallback_probability
        )

        df["future_probability_7d"] = (
            fallback_probability
        )

        df[
            "future_unavailability_severity"
        ] = fallback_probability.apply(
            lambda probability: (
                "HIGH"
                if probability >= 0.75
                else (
                    "MEDIUM"
                    if probability >= 0.45
                    else "LOW"
                )
            )
        )

        # These values are initially set by
        # add_future_risk_predictions(), but they
        # are assigned again here to guarantee that
        # the fallback can never be presented as ML.
        df["prediction_source"] = (
            "HEURISTIC"
        )

        df["prediction_method"] = (
            "WEIGHTED_RULES"
        )

        df["ml_prediction"] = False
        df["model_available"] = False

        df["prediction_disclaimer"] = (
            "The future ML model is unavailable. "
            "This result was generated using "
            "manually configured weighted rules "
            "and is not an ML forecast."
        )

        logger.warning(
            "Future output source: HEURISTIC. "
            "ML prediction: False."
        )

        return df

    future_bundle = joblib.load(
        FUTURE_MODEL_FILE
    )

    if not isinstance(
        future_bundle,
        dict,
    ):
        raise ValueError(
            "Invalid future model bundle."
        )

    if "models" not in future_bundle:
        raise ValueError(
            "Old future model format detected. "
            "Run python -m app.ml.train_model "
            "again."
        )

    future_models = future_bundle[
        "models"
    ]

    future_feature_columns = (
        future_bundle[
            "feature_columns"
        ]
    )

    validate_columns(
        df,
        future_feature_columns,
    )

    future_input = df[
        future_feature_columns
    ].fillna(0)

    horizon_column_map = {
        "24h": (
            "future_probability_24h"
        ),
        "3d": (
            "future_probability_3d"
        ),
        "7d": (
            "future_probability_7d"
        ),
    }

    for (
        horizon_key,
        output_column,
    ) in horizon_column_map.items():
        if horizon_key not in future_models:
            raise ValueError(
                "Future model bundle is missing "
                f"the {horizon_key} model."
            )

        horizon_model = future_models[
            horizon_key
        ]

        probabilities = (
            get_positive_class_probability(
                horizon_model,
                future_input,
            )
        )

        df[output_column] = [
            round(
                float(probability),
                4,
            )
            for probability in probabilities
        ]

    severity_model = future_bundle.get(
        "severity_model"
    )

    reverse_severity_map = (
        future_bundle.get(
            "severity_reverse_label_map",
            {
                0: "LOW",
                1: "MEDIUM",
                2: "HIGH",
            },
        )
    )

    if severity_model is not None:
        severity_predictions = (
            severity_model.predict(
                future_input
            )
        )

        df[
            "future_unavailability_severity"
        ] = [
            reverse_severity_map.get(
                int(prediction),
                "LOW",
            )
            for prediction
            in severity_predictions
        ]
    else:
        df[
            "future_unavailability_severity"
        ] = "LOW"

    # Keep the old seven-day field for backward
    # compatibility with existing frontend code.
    df[
        "future_instability_probability"
    ] = df[
        "future_probability_7d"
    ]

    df["future_risk_window"] = (
        df.apply(
            get_highest_risk_horizon,
            axis=1,
        )
    )

    df["early_warning_status"] = df[
        "future_probability_7d"
    ].apply(
        get_early_warning_status
    )

    df["prediction_confidence"] = df[
        "future_probability_7d"
    ].apply(
        get_future_prediction_confidence
    )

    df["future_recommendation"] = (
        df.apply(
            build_ml_future_recommendation,
            axis=1,
        )
    )

    # Explicit metadata for genuine ML output.
    df["prediction_source"] = (
        "ML_MODEL"
    )

    df["prediction_method"] = (
        "TRAINED_MULTI_HORIZON_MODEL"
    )

    df["ml_prediction"] = True
    df["model_available"] = True

    training_data_provenance = str(
        future_bundle.get(
            "training_data_provenance",
            "UNKNOWN",
        )
    ).strip().upper()

    production_validated = bool(
        future_bundle.get(
            "production_validated",
            False,
        )
    )

    df[
        "training_data_provenance"
    ] = training_data_provenance

    df[
        "production_validated"
    ] = production_validated

    if (
        training_data_provenance == "REAL"
        and production_validated
    ):
        df["prediction_disclaimer"] = (
            "Prediction generated by a trained "
            "future ML model validated using real "
            "supplier traffic."
        )
    elif (
        training_data_provenance
        == "SYNTHETIC"
    ):
        df["prediction_disclaimer"] = (
            "Prediction generated by a trained "
            "ML model using synthetic data. "
            "This model is not yet validated on "
            "real supplier traffic."
        )
    else:
        df["prediction_disclaimer"] = (
            "Prediction generated by a trained "
            "ML model, but its training-data "
            "provenance is not verified."
        )

    logger.info(
        "Future output source: ML_MODEL. "
        "Training provenance: %s. "
        "Production validated: %s.",
        training_data_provenance,
        production_validated,
    )

    return df


def load_features(
    features_df: pd.DataFrame,
) -> pd.DataFrame:
    if features_df is None:
        raise ValueError(
            "features_df is required. "
            "The live pipeline must pass "
            "in-memory supplier features."
        )

    logger.info(
        "Using in-memory supplier features "
        "from pipeline."
    )

    return (
        features_df.fillna(0).copy()
    )


def load_anomaly_model() -> dict:
    if not ANOMALY_MODEL_FILE.exists():
        raise FileNotFoundError(
            "Anomaly model not found: "
            f"{ANOMALY_MODEL_FILE}. "
            "Train the model first using the "
            "offline training script."
        )

    anomaly_bundle = joblib.load(
        ANOMALY_MODEL_FILE
    )

    if not isinstance(
        anomaly_bundle,
        dict,
    ):
        raise ValueError(
            "Old anomaly model format detected. "
            "Run python -m app.ml.train_model "
            "again."
        )

    if "model" not in anomaly_bundle:
        raise ValueError(
            "Invalid anomaly model bundle: "
            "model missing."
        )

    logger.info(
        "Current-state anomaly model loaded "
        "from: %s",
        ANOMALY_MODEL_FILE,
    )

    return anomaly_bundle


def detect_anomalies(
    features_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df = load_features(
        features_df
    )

    if df.empty:
        raise ValueError(
            "Supplier features are empty. "
            "Run feature_builder first."
        )

    anomaly_bundle = (
        load_anomaly_model()
    )

    anomaly_model = anomaly_bundle[
        "model"
    ]

    anomaly_feature_columns = (
        anomaly_bundle[
            "feature_columns"
        ]
    )

    validate_columns(
        df,
        anomaly_feature_columns,
    )

    anomaly_input = df[
        anomaly_feature_columns
    ].fillna(0)

    df["current_anomaly_flag"] = (
        anomaly_model.predict(
            anomaly_input
        )
    )

    df["current_anomaly_score"] = (
        anomaly_model.decision_function(
            anomaly_input
        )
    )

    df["current_anomaly_status"] = (
        df["current_anomaly_flag"].map(
            {
                1: "CURRENT_NORMAL",
                -1: "CURRENT_ANOMALY",
            }
        )
    )

    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            "Current-risk model not found: "
            f"{MODEL_FILE}. "
            "Run python -m app.ml.train_model "
            "first."
        )

    risk_bundle = joblib.load(
        MODEL_FILE
    )

    if not isinstance(
        risk_bundle,
        dict,
    ):
        raise ValueError(
            "Invalid current-risk model bundle."
        )

    risk_model = risk_bundle[
        "model"
    ]

    feature_columns = risk_bundle[
        "feature_columns"
    ]

    reverse_label_map = risk_bundle[
        "reverse_label_map"
    ]

    validate_columns(
        df,
        feature_columns,
    )

    risk_input = df[
        feature_columns
    ].fillna(0)

    risk_predictions = (
        risk_model.predict(
            risk_input
        )
    )

    risk_probabilities = (
        get_risk_prediction_probability(
            risk_model,
            risk_input,
        )
    )

    df["predicted_risk"] = [
        reverse_label_map[
            int(prediction)
        ]
        for prediction in risk_predictions
    ]

    df["prediction_probability"] = [
        round(
            float(probability),
            4,
        )
        for probability in risk_probabilities
    ]

    df["recommendation"] = df.apply(
        lambda row: get_recommendation(
            row["risk_level"],
            row[
                "current_anomaly_status"
            ],
        ),
        axis=1,
    )

    df = (
        apply_ml_future_failure_prediction(
            df
        )
    )

    result_columns = [
        "supplier_code",
        "risk_score",
        "risk_level",
        "predicted_risk",
        "prediction_probability",
        "current_anomaly_score",
        "current_anomaly_status",
        "recommendation",
        "future_probability_24h",
        "future_probability_3d",
        "future_probability_7d",
        "future_instability_probability",
        "future_unavailability_severity",
        "future_risk_window",
        "early_warning_status",
        "lead_signal",
        "prediction_confidence",
        "future_recommendation",

        # Prediction-source transparency.
        "prediction_source",
        "prediction_method",
        "ml_prediction",
        "model_available",
        "prediction_disclaimer",

        "supplier_name",
        "total_bookings",
        "failure_rate",
        "pending_rate",
        "cancellation_rate",
        "process_error_rate",
        "refund_rate",
        "credit_rejection_rate",
        "search_failure_rate",
        "wallet_risk_rate",
    ]

    optional_metadata_columns = [
        "training_data_provenance",
        "production_validated",
    ]

    for column in optional_metadata_columns:
        if column in df.columns:
            result_columns.append(
                column
            )

    result = df[
        result_columns
    ].copy()

    logger.info(
        "Current anomaly detection and future "
        "unavailability prediction completed "
        "successfully."
    )

    logger.info(
        "Prediction result generated in memory. "
        "CSV writing is disabled in the live "
        "pipeline."
    )

    logger.info(
        "Prediction summary:\n%s",
        result.to_string(
            index=False
        ),
    )

    return result