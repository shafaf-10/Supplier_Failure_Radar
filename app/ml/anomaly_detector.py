import joblib
import pandas as pd
from app.infra.paths import MODEL_DIR
import joblib
import pandas as pd
from app.ml.future_risk_predictor import (
    add_future_risk_predictions,
    get_early_warning_status,
    get_future_prediction_confidence,
)

from app.ml.future_risk_predictor import add_future_risk_predictions
from app.ml.future_risk_predictor import (
    get_early_warning_status,
    get_future_prediction_confidence,
)
from app.ml.prediction_recommendations import get_recommendation
from app.observability.logger import setup_logger


logger = setup_logger(__name__)


MODEL_FILE = MODEL_DIR / "risk_model.pkl"
FUTURE_MODEL_FILE = MODEL_DIR / "future_failure_model.pkl"
ANOMALY_MODEL_FILE = MODEL_DIR / "anomaly_model.pkl"

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


def validate_columns(df, columns):
    missing = [col for col in columns if col not in df.columns]

    if missing:
        raise ValueError(
            f"Missing columns: {missing}. Run feature_builder.py again."
        )


def get_risk_prediction_probability(model, x_values):
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(x_values)
        return probabilities.max(axis=1)

    return [0.0] * len(x_values)


def build_ml_future_recommendation(row):
    probability_pct = round(
        float(row["future_instability_probability"]) * 100,
        1,
    )

    lead_signal = row.get("lead_signal", "Operational Risk")
    warning_status = row.get("early_warning_status", "STABLE")

    if warning_status == "CRITICAL_WARNING":
        return (
            f"ML model predicts high probability of supplier instability "
            f"in the next 7 days ({probability_pct}%). "
            f"Primary lead signal: {lead_signal}. "
            f"Prepare backup supplier, reduce dependency, and monitor closely."
        )

    if warning_status == "WARNING":
        return (
            f"ML model shows warning signs for possible instability "
            f"in the next 7 days ({probability_pct}%). "
            f"Primary lead signal: {lead_signal}. "
            f"Monitor closely and prepare fallback routing."
        )

    if warning_status == "WATCHLIST":
        return (
            f"Supplier is on watchlist based on ML future risk score "
            f"({probability_pct}%). Main signal: {lead_signal}."
        )

    return (
        f"ML model predicts low instability probability for the next 7 days "
        f"({probability_pct}%)."
    )

def get_positive_class_probability(
    model,
    input_values: pd.DataFrame,
) -> list[float]:
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(
            input_values
        )

        model_classes = list(model.classes_)

        if 1 in model_classes:
            positive_class_index = (
                model_classes.index(1)
            )

            return probabilities[
                :,
                positive_class_index,
            ].tolist()

        return [0.0] * len(input_values)

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
        ),
        "NEXT_3_DAYS": float(
            row.get(
                "future_probability_3d",
                0,
            )
        ),
        "NEXT_7_DAYS": float(
            row.get(
                "future_probability_7d",
                0,
            )
        ),
    }

    return max(
        horizon_probabilities,
        key=horizon_probabilities.get,
    )

def apply_ml_future_failure_prediction(
    df: pd.DataFrame,
) -> pd.DataFrame:
    df = add_future_risk_predictions(df)

    if not FUTURE_MODEL_FILE.exists():
        logger.warning(
            "Future model bundle not found. "
            "Using weighted future scoring fallback."
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

        return df

    future_bundle = joblib.load(
        FUTURE_MODEL_FILE
    )

    if not isinstance(future_bundle, dict):
        raise ValueError(
            "Invalid future model bundle."
        )

    if "models" not in future_bundle:
        raise ValueError(
            "Old future model format detected. "
            "Run python -m app.ml.train_model again."
        )

    future_models = future_bundle["models"]

    future_feature_columns = (
        future_bundle["feature_columns"]
    )

    validate_columns(
        df,
        future_feature_columns,
    )

    future_input = df[
        future_feature_columns
    ].fillna(0)

    horizon_column_map = {
        "24h": "future_probability_24h",
        "3d": "future_probability_3d",
        "7d": "future_probability_7d",
    }

    for horizon_key, output_column in (
        horizon_column_map.items()
    ):
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
            round(float(probability), 4)
            for probability in probabilities
        ]

    severity_model = future_bundle.get(
        "severity_model"
    )

    reverse_severity_map = future_bundle.get(
        "severity_reverse_label_map",
        {
            0: "LOW",
            1: "MEDIUM",
            2: "HIGH",
        },
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

    # Keep the old field for backward compatibility.
    df[
        "future_instability_probability"
    ] = df["future_probability_7d"]

    df["future_risk_window"] = df.apply(
        get_highest_risk_horizon,
        axis=1,
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

    df["future_recommendation"] = df.apply(
        build_ml_future_recommendation,
        axis=1,
    )

    return df


def load_features(features_df):
    if features_df is None:
        raise ValueError(
            "features_df is required. Live pipeline must pass in-memory supplier features."
        )

    logger.info("Using in-memory supplier features from pipeline.")
    return features_df.fillna(0).copy()


def load_anomaly_model():
    if not ANOMALY_MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Anomaly model not found: {ANOMALY_MODEL_FILE}. "
            "Train the model first using the offline "
            "training script."
        )

    anomaly_bundle = joblib.load(
        ANOMALY_MODEL_FILE
    )

    if not isinstance(anomaly_bundle, dict):
        raise ValueError(
            "Old anomaly model format detected. "
            "Run python -m app.ml.train_model again."
        )

    if "model" not in anomaly_bundle:
        raise ValueError(
            "Invalid anomaly model bundle: model missing."
        )

    logger.info(
        "Current-state anomaly model loaded from: %s",
        ANOMALY_MODEL_FILE,
    )

    return anomaly_bundle


def detect_anomalies(features_df=None):
    df = load_features(features_df)

    if df.empty:
        raise Exception("Supplier features are empty. Run feature_builder first.")

    anomaly_bundle = load_anomaly_model()

    anomaly_model = anomaly_bundle["model"]

    anomaly_feature_columns = anomaly_bundle[
        "feature_columns"
    ]

    validate_columns(
        df,
        anomaly_feature_columns,
    )

    x_anomaly = df[
        anomaly_feature_columns
    ].fillna(0)

    df["current_anomaly_flag"] = anomaly_model.predict(
    x_anomaly
)

    df["current_anomaly_score"] = (
    anomaly_model.decision_function(x_anomaly)
)

    df["current_anomaly_status"] = (
    df["current_anomaly_flag"].map(
        {
            1: "CURRENT_NORMAL",
            -1: "CURRENT_ANOMALY",
        }
    )
)

    risk_bundle = joblib.load(MODEL_FILE)
    risk_model = risk_bundle["model"]
    feature_columns = risk_bundle["feature_columns"]
    reverse_label_map = risk_bundle["reverse_label_map"]

    validate_columns(df, feature_columns)

    risk_input = df[feature_columns].fillna(0)

    risk_predictions = risk_model.predict(risk_input)
    risk_probabilities = get_risk_prediction_probability(
        risk_model,
        risk_input,
    )

    df["predicted_risk"] = [
        reverse_label_map[int(pred)]
        for pred in risk_predictions
    ]

    df["prediction_probability"] = [
        round(float(prob), 4)
        for prob in risk_probabilities
    ]

    df["recommendation"] = df.apply(
    lambda row: get_recommendation(
        row["risk_level"],
        row["current_anomaly_status"],
    ),
    axis=1,
)

    df = apply_ml_future_failure_prediction(df)

    result = df[
        [
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
            "lead_signal",
            "prediction_confidence",
            "future_recommendation",
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
    ].copy()

    logger.info(
    "Current anomaly detection and future unavailability "
    "prediction completed successfully."
)
    logger.info(
        "Prediction result generated in memory. CSV writing is disabled in live pipeline."
    )
    logger.info(
        "Prediction summary:\n%s",
        result.to_string(index=False),
    )

    return result