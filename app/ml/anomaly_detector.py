import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import text

from app.infra.database import engine


ROOT_DIR = Path(__file__).resolve().parents[2]

FEATURE_FILE = ROOT_DIR / "outputs" / "supplier_features.csv"
MODEL_FILE = ROOT_DIR / "app" / "ml" / "models" / "risk_model.pkl"
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


def detect_anomalies():
    print(f"Loading features from: {FEATURE_FILE}")

    df = pd.read_csv(FEATURE_FILE)
    df = df.fillna(0).copy()

    if df.empty:
        raise Exception("supplier_features.csv is empty. Run feature_builder first.")

    validate_columns(df, ANOMALY_FEATURES)

    X = df[ANOMALY_FEATURES].fillna(0)

    anomaly_model = IsolationForest(
        n_estimators=300,
        contamination=0.20,
        random_state=42,
    )

    df["anomaly_flag"] = anomaly_model.fit_predict(X)
    df["anomaly_score"] = anomaly_model.decision_function(X)

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

    df["predicted_risk"] = [
        reverse_label_map[int(pred)]
        for pred in risk_predictions
    ]

    df["recommendation"] = df.apply(
        get_recommendation,
        axis=1,
    )

    result = df[
        [
            "supplier_code",
            "risk_score",
            "risk_level",
            "predicted_risk",
            "anomaly_score",
            "anomaly_status",
            "recommendation",
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
                        recommendation
                    )
                    VALUES (
                        :supplier_code,
                        :predicted_risk,
                        1.0000,
                        'RandomForest + IsolationForest',
                        :recommendation,
                        :risk_score,
                        :risk_level,
                        :predicted_risk,
                        :anomaly_score,
                        :anomaly_status,
                        :recommendation
                    )
                    """
                ),
                row.to_dict(),
            )

    print("Production anomaly detection completed successfully.")
    print(f"Anomaly model saved to: {ANOMALY_MODEL_FILE}")
    print(f"Anomaly output saved to: {ANOMALY_FILE}")
    print(result)


if __name__ == "__main__":
    detect_anomalies()