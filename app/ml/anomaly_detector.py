import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import text

from app.infra.database import engine
from app.ml.future_risk_predictor import add_future_risk_predictions


ROOT_DIR = Path(__file__).resolve().parents[2]

FEATURE_FILE = ROOT_DIR / "outputs" / "supplier_features.csv"
MODEL_FILE = ROOT_DIR / "app" / "ml" / "models" / "risk_model.pkl"
FUTURE_MODEL_FILE = ROOT_DIR / "app" / "ml" / "models" / "future_failure_model.pkl"
ANOMALY_MODEL_FILE = ROOT_DIR / "app" / "ml" / "models" / "anomaly_model.pkl"
ANOMALY_FILE = ROOT_DIR / "outputs" / "supplier_anomalies.csv"


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


def ensure_prediction_table_columns():
    existing_cols = pd.read_sql(
        "SHOW COLUMNS FROM supplier_predictions",
        engine,
    )["Field"].tolist()

    required_cols = {
        "risk_score": "DECIMAL(10,2) DEFAULT 0",
        "risk_level": "VARCHAR(50)",
        "predicted_risk": "VARCHAR(50)",
        "anomaly_score": "DECIMAL(10,6) DEFAULT 0",
        "anomaly_status": "VARCHAR(50)",
        "recommendation": "TEXT",
        "future_instability_probability": "DECIMAL(8,4) DEFAULT 0",
        "future_risk_window": "VARCHAR(50)",
        "early_warning_status": "VARCHAR(50)",
        "lead_signal": "VARCHAR(100)",
        "prediction_confidence": "VARCHAR(50)",
        "future_recommendation": "TEXT",
    }

    with engine.begin() as conn:
        for col, col_type in required_cols.items():
            if col not in existing_cols:
                conn.execute(
                    text(
                        f"ALTER TABLE supplier_predictions "
                        f"ADD COLUMN {col} {col_type}"
                    )
                )


def validate_columns(df, columns):
    missing = [
        col for col in columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns: {missing}. Run feature_builder.py again."
        )


def get_recommendation(row):
    if row["anomaly_status"] == "ANOMALY":
        return (
            "Immediate investigation required. Check booking failure spikes, "
            "supplier API retries, ticketing SLA misses, refund delay, "
            "search timeout, credit exposure, and wallet failed payments."
        )

    if row["risk_level"] == "HIGH_RISK":
        return (
            "Supplier is high risk. Reduce dependency, monitor ticketing SLA, "
            "refund delays, high retries, and wallet exposure."
        )

    if row["risk_level"] == "MEDIUM_RISK":
        return (
            "Supplier needs monitoring. Watch booking pending rate, process retry, "
            "search completion gap, refund pending rate, and wallet holds."
        )

    return "Supplier is stable. Continue normal monitoring."


def get_risk_prediction_probability(model, x_values):
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(x_values)
        return probabilities.max(axis=1)

    return [0.0] * len(x_values)


def get_warning_status(probability):
    if probability >= 0.70:
        return "CRITICAL_WARNING"

    if probability >= 0.45:
        return "WARNING"

    if probability >= 0.25:
        return "WATCHLIST"

    return "STABLE"


def get_prediction_confidence(probability):
    if probability >= 0.70 or probability <= 0.20:
        return "HIGH"

    if probability >= 0.45:
        return "MEDIUM"

    return "LOW"


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


def apply_ml_future_failure_prediction(df):
    """
    Uses trained future_failure_model.pkl to generate ML-based
    next-7-days future instability probability.

    Falls back to weighted scoring if future model is not available.
    """

    df = add_future_risk_predictions(df)

    if not FUTURE_MODEL_FILE.exists():
        print("Future failure model not found. Using weighted future scoring fallback.")
        return df

    future_bundle = joblib.load(FUTURE_MODEL_FILE)
    future_model = future_bundle["model"]
    future_feature_columns = future_bundle["feature_columns"]

    validate_columns(df, future_feature_columns)

    future_input = df[future_feature_columns].fillna(0)

    if hasattr(future_model, "predict_proba"):
        future_probabilities = future_model.predict_proba(future_input)[:, 1]
    else:
        future_predictions = future_model.predict(future_input)
        future_probabilities = future_predictions

    df["future_instability_probability"] = [
        round(float(prob), 4)
        for prob in future_probabilities
    ]

    df["future_risk_window"] = "NEXT_7_DAYS"

    df["early_warning_status"] = df[
        "future_instability_probability"
    ].apply(get_warning_status)

    df["prediction_confidence"] = df[
        "future_instability_probability"
    ].apply(get_prediction_confidence)

    df["future_recommendation"] = df.apply(
        build_ml_future_recommendation,
        axis=1,
    )

    return df


def detect_anomalies():
    print(f"Loading features from: {FEATURE_FILE}")

    df = pd.read_csv(FEATURE_FILE)
    df = df.fillna(0).copy()

    if df.empty:
        raise Exception("supplier_features.csv is empty. Run feature_builder first.")

    validate_columns(df, ANOMALY_FEATURES)

    x_anomaly = df[ANOMALY_FEATURES].fillna(0)

    anomaly_model = IsolationForest(
        n_estimators=300,
        contamination=0.20,
        random_state=42,
    )

    df["anomaly_flag"] = anomaly_model.fit_predict(x_anomaly)
    df["anomaly_score"] = anomaly_model.decision_function(x_anomaly)

    df["anomaly_status"] = df["anomaly_flag"].map(
        {
            1: "NORMAL",
            -1: "ANOMALY",
        }
    )

    joblib.dump(anomaly_model, ANOMALY_MODEL_FILE)

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
        get_recommendation,
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
            "anomaly_score",
            "anomaly_status",
            "recommendation",
            "future_instability_probability",
            "future_risk_window",
            "early_warning_status",
            "lead_signal",
            "prediction_confidence",
            "future_recommendation",
        ]
    ].copy()

    os.makedirs(ROOT_DIR / "outputs", exist_ok=True)
    result.to_csv(ANOMALY_FILE, index=False)

    ensure_prediction_table_columns()

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM supplier_predictions"))

        for _, row in result.iterrows():
            conn.execute(
                text(
                    """
                    INSERT INTO supplier_predictions (
                        supplier_code,
                        predicted_risk_level,
                        prediction_probability,
                        model_name,
                        prediction_reason,
                        risk_score,
                        risk_level,
                        predicted_risk,
                        anomaly_score,
                        anomaly_status,
                        recommendation,
                        future_instability_probability,
                        future_risk_window,
                        early_warning_status,
                        lead_signal,
                        prediction_confidence,
                        future_recommendation
                    )
                    VALUES (
                        :supplier_code,
                        :predicted_risk,
                        :prediction_probability,
                        'RandomForest + IsolationForest + FutureFailureML',
                        :future_recommendation,
                        :risk_score,
                        :risk_level,
                        :predicted_risk,
                        :anomaly_score,
                        :anomaly_status,
                        :recommendation,
                        :future_instability_probability,
                        :future_risk_window,
                        :early_warning_status,
                        :lead_signal,
                        :prediction_confidence,
                        :future_recommendation
                    )
                    """
                ),
                row.to_dict(),
            )

    print("Production anomaly and ML future failure prediction completed successfully.")
    print(f"Anomaly model saved to: {ANOMALY_MODEL_FILE}")
    print(f"Prediction output saved to: {ANOMALY_FILE}")
    print(result)


if __name__ == "__main__":
    detect_anomalies()