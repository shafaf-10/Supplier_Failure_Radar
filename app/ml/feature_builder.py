import pandas as pd
from app.ml.model_thresholds import RISK_SCORE_THRESHOLDS, RISK_SCORE_WEIGHTS
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
from app.ml.model_thresholds import RISK_SCORE_THRESHOLDS
from app.ml.schema_validation import validate_table_schema
logger = setup_logger(__name__)

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


TABLE_DATE_COLUMNS = {
    "bookings": "booking_date",
    "booking_processes": "created_at",
    "booking_flights": "created_at",
    "booking_passengers": None,
    "search_sessions": "created_at",
    "refund_requests": "created_at",
    "credit_requests": "created_at",
    "wallet_transactions": "created_at",
    "suppliers": None,
}


def read_table(table_name: str, days: int | None = None) -> pd.DataFrame:
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Table not allowed: {table_name}")

    date_column = TABLE_DATE_COLUMNS.get(table_name)

    if days is not None and date_column is not None:
        query = text(
            f"""
            SELECT *
            FROM `{table_name}`
            WHERE `{date_column}` >= DATE_SUB(
                (SELECT MAX(`{date_column}`) FROM `{table_name}`),
                INTERVAL :days DAY
            )
            """
        )
        return pd.read_sql(query, engine, params={"days": days})

    query = text(f"SELECT * FROM `{table_name}`")
    return pd.read_sql(query, engine)
def get_risk_level(score: float) -> str:
    t = RISK_SCORE_THRESHOLDS

    if score >= t["HIGH_RISK"]:
        return "HIGH_RISK"

    if score >= t["MEDIUM_RISK"]:
        return "MEDIUM_RISK"

    return "LOW_RISK"


def calculate_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    w = RISK_SCORE_WEIGHTS

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
        df["b_failure_rate"] * w["B_FAILURE_RATE"]
        + df["b_pending_rate"] * w["B_PENDING_RATE"]
        + df["b_cancellation_rate"] * w["B_CANCELLATION_RATE"]
        + df["b_deadline_miss_rate"] * w["B_DEADLINE_MISS_RATE"]
        + df["bp_error_rate"] * w["BP_ERROR_RATE"]
        + df["bp_stuck_rate"] * w["BP_STUCK_RATE"]
        + df["bp_high_retry_rate"] * w["BP_HIGH_RETRY_RATE"]
        + df["booking_not_issued_rate"] * w["BOOKING_NOT_ISSUED_RATE"]
        + df["supplier_pnr_missing_rate"] * w["SUPPLIER_PNR_MISSING_RATE"]
        + df["ticket_number_missing_rate"] * w["TICKET_NUMBER_MISSING_RATE"]
        + df["supplier_ticketing_risk_score_100"] * w["SUPPLIER_TICKETING_RISK_SCORE"]
        + df["rr_refund_risk_score_100"] * w["REFUND_RISK_SCORE"]
        + df["cr_credit_risk_score_100"] * w["CREDIT_RISK_SCORE"]
        + df["supplier_session_risk_score_100"] * w["SESSION_RISK_SCORE"]
        + df["wt_wallet_risk_score_100"] * w["WALLET_RISK_SCORE"]
    ).round(2)

    df["risk_level"] = df["risk_score"].apply(get_risk_level)

    return df


def add_backward_compatible_columns(df: pd.DataFrame) -> pd.DataFrame:
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



def build_supplier_features(days=None):
    """
    days=None  -> all time
    days=1     -> last 24 hours
    days=7     -> last 7 days
    days=30    -> last 30 days
    days=365   -> last 1 year

    Returns in-memory supplier features for the selected period.
    """

    logger.info("Loading source tables for supplier feature generation.")

    suppliers = read_table("suppliers")
    bookings = read_table("bookings", days=days)
    booking_processes = read_table("booking_processes", days=days)
    booking_flights = read_table("booking_flights", days=days)
    if days is not None:
        booking_ids = bookings["id"].tolist()

        if booking_ids:
            booking_passengers = pd.read_sql(
                text("SELECT * FROM booking_passengers WHERE booking_id IN :booking_ids"),
                engine,
                params={"booking_ids": tuple(booking_ids)},
        )
        else:
            booking_passengers = pd.DataFrame()
    else:
        booking_passengers = read_table("booking_passengers")

    search_sessions = read_table("search_sessions", days=days)
    refund_requests = read_table("refund_requests", days=days)
    credit_requests = read_table("credit_requests", days=days)
    wallet_transactions = read_table("wallet_transactions", days=days)

    validate_table_schema("suppliers", suppliers)
    validate_table_schema("bookings", bookings)
    validate_table_schema("booking_processes", booking_processes)
    validate_table_schema("booking_flights", booking_flights)
    validate_table_schema("booking_passengers", booking_passengers)
    validate_table_schema("search_sessions", search_sessions)
    validate_table_schema("refund_requests", refund_requests)
    validate_table_schema("credit_requests", credit_requests)
    validate_table_schema("wallet_transactions", wallet_transactions)

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



