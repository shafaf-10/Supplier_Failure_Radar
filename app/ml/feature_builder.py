import os
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from app.infra.database import engine

from app.ml.feature_engineering.booking_features import build_booking_features
from app.ml.feature_engineering.process_features import build_process_features
from app.ml.feature_engineering.ticketing_features import build_ticketing_features
from app.ml.feature_engineering.session_features import build_session_features
from app.ml.feature_engineering.refund_features import build_refund_features
from app.ml.feature_engineering.credit_features import build_credit_features
from app.ml.feature_engineering.wallet_features import build_wallet_features
from app.ml.feature_engineering.build_master import build_master_supplier_table
from app.observability.logger import setup_logger
logger = setup_logger(__name__)


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_FILE = ROOT_DIR / "outputs" / "supplier_features.csv"


ALLOWED_TABLES = {
    "suppliers",
    "bookings",
    "booking_processes",
    "booking_flights",
    "booking_passengers",
    "search_sessions",
    "refund_requests",
    "credit_requests",
    "wallet_transactions",
}


def read_table(table_name):
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Table not allowed: {table_name}")

    query = text(f"SELECT * FROM `{table_name}`")
    return pd.read_sql(query, engine)
def get_risk_level(score):
    if score >= 28:
        return "HIGH_RISK"
    elif score >= 18:
        return "MEDIUM_RISK"
    return "LOW_RISK"


def calculate_risk_score(df):
    df = df.copy()

    required_cols = [
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
        "supplier_ticketing_risk_score_100",
        "rr_refund_risk_score_100",
        "cr_credit_risk_score_100",
        "supplier_session_risk_score_100",
        "wt_wallet_risk_score_100",
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = 0

    df["risk_score"] = (
        df["b_failure_rate"] * 20
        + df["b_pending_rate"] * 10
        + df["b_cancellation_rate"] * 10
        + df["b_deadline_miss_rate"] * 8
        + df["bp_error_rate"] * 12
        + df["bp_stuck_rate"] * 8
        + df["bp_high_retry_rate"] * 8
        + df["booking_not_issued_rate"] * 6
        + df["supplier_pnr_missing_rate"] * 5
        + df["ticket_number_missing_rate"] * 5
        + df["supplier_ticketing_risk_score_100"] * 0.08
        + df["rr_refund_risk_score_100"] * 0.08
        + df["cr_credit_risk_score_100"] * 0.08
        + df["supplier_session_risk_score_100"] * 0.08
        + df["wt_wallet_risk_score_100"] * 0.08
    ).round(2)

    df["risk_level"] = df["risk_score"].apply(get_risk_level)

    return df


def add_backward_compatible_columns(df):
    df = df.copy()

    b_total = df.get("b_total", pd.Series([0] * len(df))).replace(0, 1)

    extra_cols = pd.DataFrame(
        {
            "total_bookings": df.get("b_total", 0),
            "successful_bookings": df.get("b_issued", 0),
            "failed_bookings": df.get("b_failed", 0),
            "pending_bookings": df.get("b_pending", 0),
            "cancelled_bookings": df.get("b_cancelled", 0),
            "failure_rate": df.get("b_failure_rate", 0),
            "pending_rate": df.get("b_pending_rate", 0),
            "cancellation_rate": df.get("b_cancellation_rate", 0),
            "process_error_rate": df.get("bp_error_rate", 0),
            "avg_attempts": df.get("bp_attempts_mean", 0),
            "refund_rate": df.get("rr_total", 0) / b_total,
            "credit_rejection_rate": df.get("cr_rejection_rate", 0),
            "search_failure_rate": (
                df.get("ss_failure_rate", 0)
                + df.get("ss_partial_rate", 0)
                + df.get("ss_timeout_rate", 0)
            ),
            "wallet_risk_rate": df.get("wt_risk_rate", 0),
            "avg_booking_amount": df.get("b_amount_mean", 0),
        }
    )

    df = pd.concat(
        [
            df.reset_index(drop=True),
            extra_cols.reset_index(drop=True),
        ],
        axis=1,
    )

    return df.fillna(0).copy()


def save_features_to_db(features):
    db_columns = pd.read_sql(
        "SHOW COLUMNS FROM supplier_features",
        engine,
    )["Field"].tolist()

    insert_columns = [
        col for col in features.columns
        if col in db_columns and col != "id"
    ]

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM supplier_features"))

        for _, row in features.iterrows():
            columns_sql = ", ".join(insert_columns)
            values_sql = ", ".join([f":{col}" for col in insert_columns])

            conn.execute(
                text(
                    f"""
                    INSERT INTO supplier_features (
                        {columns_sql}
                    )
                    VALUES (
                        {values_sql}
                    )
                    """
                ),
                {col: row[col] for col in insert_columns},
            )


def build_supplier_features(days=None, persist=True):
    """
    days=None  -> all time
    days=1     -> last 24 hours
    days=7     -> last 7 days
    days=30    -> last 30 days
    days=365   -> last 1 year

    persist=True  -> save to supplier_features table + CSV
    persist=False -> return temporary period-based features only
    """

    logger.info("Loading source tables for supplier feature generation.")

    suppliers = read_table("suppliers")
    bookings = read_table("bookings")
    booking_processes = read_table("booking_processes")
    booking_flights = read_table("booking_flights")
    booking_passengers = read_table("booking_passengers")
    search_sessions = read_table("search_sessions")
    refund_requests = read_table("refund_requests")
    credit_requests = read_table("credit_requests")
    wallet_transactions = read_table("wallet_transactions")

    logger.info("Building supplier feature groups.")

    booking_features = build_booking_features(bookings, days=days)

    process_features = build_process_features(
        booking_processes,
        days=days,
    )

    ticketing_features = build_ticketing_features(
        bookings,
        booking_flights,
        booking_passengers,
        days=days,
    )

    session_features = build_session_features(
        search_sessions,
        days=days,
    )

    refund_features = build_refund_features(
        refund_requests,
        bookings,
        days=days,
    )

    credit_features = build_credit_features(
        credit_requests,
        days=days,
    )

    wallet_features = build_wallet_features(
        wallet_transactions,
        days=days,
    )

    logger.info("Merging supplier feature groups into master dataframe.")

    features = build_master_supplier_table(
        suppliers=suppliers,
        booking_features=booking_features,
        process_features=process_features,
        ticketing_features=ticketing_features,
        session_features=session_features,
        refund_features=refund_features,
        credit_features=credit_features,
        wallet_features=wallet_features,
    )

    features = features.fillna(0).copy()
    features = calculate_risk_score(features)
    features = add_backward_compatible_columns(features)

    if persist:
        logger.info(
        "Feature dataframe generated in memory. CSV writing is disabled in live pipeline."
    )

    logger.info("Supplier features created successfully.")

    display_cols = [
        "supplier_code",
        "b_failure_rate",
        "b_pending_rate",
        "bp_error_rate",
        "bp_high_retry_rate",
        "booking_not_issued_rate",
        "rr_refund_risk_score_100",
        "cr_credit_risk_score_100",
        "supplier_session_risk_score_100",
        "wt_wallet_risk_score_100",
        "risk_score",
        "risk_level",
    ]

    existing_display_cols = [
        col for col in display_cols
        if col in features.columns
    ]

    logger.info(
    "Supplier feature summary:\n%s",
    features[existing_display_cols].to_string(index=False),
)

    return features


if __name__ == "__main__":
    build_supplier_features()