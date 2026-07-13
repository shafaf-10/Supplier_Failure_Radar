import pandas as pd

from app.ml.feature_builder import (
    add_backward_compatible_columns,
    add_time_series_features,
    calculate_risk_score,
    read_table,
)
from app.ml.feature_engineering.booking_features import build_booking_features
from app.ml.feature_engineering.build_master import build_master_supplier_table
from app.ml.feature_engineering.credit_features import build_credit_features
from app.ml.feature_engineering.process_features import build_process_features
from app.ml.feature_engineering.refund_features import build_refund_features
from app.ml.feature_engineering.session_features import build_session_features
from app.ml.feature_engineering.ticketing_features import build_ticketing_features
from app.ml.feature_engineering.wallet_features import build_wallet_features
from app.observability.logger import setup_logger


logger = setup_logger(__name__)


FEATURE_WINDOW_DAYS = 30
FUTURE_WINDOW_DAYS = 7
SNAPSHOT_STEP_DAYS = 1
MIN_FUTURE_BOOKINGS = 5
FUTURE_FAILURE_RATE_THRESHOLD = 0.10

FAILED_BOOKING_STATUSES = {
    "FAILED",
    "EXPIRED",
}


def _convert_datetime(
    dataframe: pd.DataFrame,
    column_name: str,
) -> pd.DataFrame:
    dataframe = dataframe.copy()

    if column_name in dataframe.columns:
        dataframe[column_name] = pd.to_datetime(
            dataframe[column_name],
            errors="coerce",
        )

    return dataframe


def _filter_date_window(
    dataframe: pd.DataFrame,
    date_column: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return pd.DataFrame()

    if date_column not in dataframe.columns:
        return dataframe.copy()

    filtered = _convert_datetime(dataframe, date_column)

    return filtered[
        (filtered[date_column] >= start_date)
        & (filtered[date_column] < end_date)
    ].copy()


def _filter_booking_passengers(
    booking_passengers: pd.DataFrame,
    bookings: pd.DataFrame,
) -> pd.DataFrame:
    if (
        booking_passengers is None
        or booking_passengers.empty
        or bookings is None
        or bookings.empty
        or "booking_id" not in booking_passengers.columns
        or "id" not in bookings.columns
    ):
        return pd.DataFrame()

    booking_ids = set(bookings["id"].dropna().tolist())

    return booking_passengers[
        booking_passengers["booking_id"].isin(booking_ids)
    ].copy()


def _build_future_labels(
    suppliers: pd.DataFrame,
    future_bookings: pd.DataFrame,
) -> pd.DataFrame:
    supplier_codes = suppliers[["code"]].copy()
    supplier_codes = supplier_codes.rename(
        columns={"code": "supplier_code"}
    )

    if future_bookings is None or future_bookings.empty:
        supplier_codes["future_booking_count"] = 0
        supplier_codes["future_failed_booking_count"] = 0
        supplier_codes["observed_future_failure_rate"] = 0.0
        supplier_codes["observed_failure_next_7d"] = 0
        return supplier_codes

    future = future_bookings.copy()

    future["status_upper"] = (
        future["status"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    future["is_failed"] = (
        future["status_upper"]
        .isin(FAILED_BOOKING_STATUSES)
        .astype(int)
    )

    labels = (
        future.groupby("provider")
        .agg(
            future_booking_count=("provider", "count"),
            future_failed_booking_count=("is_failed", "sum"),
        )
        .reset_index()
        .rename(columns={"provider": "supplier_code"})
    )

    labels["observed_future_failure_rate"] = (
        labels["future_failed_booking_count"]
        / labels["future_booking_count"].replace(0, 1)
    )

    labels["observed_failure_next_7d"] = (
        (
            labels["future_booking_count"] >= MIN_FUTURE_BOOKINGS
        )
        & (
            labels["observed_future_failure_rate"]
            >= FUTURE_FAILURE_RATE_THRESHOLD
        )
    ).astype(int)

    result = supplier_codes.merge(
        labels,
        on="supplier_code",
        how="left",
    )

    numeric_columns = [
        "future_booking_count",
        "future_failed_booking_count",
        "observed_future_failure_rate",
        "observed_failure_next_7d",
    ]

    result[numeric_columns] = (
        result[numeric_columns]
        .fillna(0)
    )

    result["observed_failure_next_7d"] = (
        result["observed_failure_next_7d"]
        .astype(int)
    )

    return result


def _build_snapshot_features(
    suppliers: pd.DataFrame,
    bookings: pd.DataFrame,
    booking_processes: pd.DataFrame,
    booking_flights: pd.DataFrame,
    booking_passengers: pd.DataFrame,
    search_sessions: pd.DataFrame,
    refund_requests: pd.DataFrame,
    credit_requests: pd.DataFrame,
    wallet_transactions: pd.DataFrame,
    snapshot_date: pd.Timestamp,
) -> pd.DataFrame:
    booking_features = build_booking_features(
        bookings,
        days=None,
    )

    process_features = build_process_features(
        booking_processes,
        days=None,
    )

    ticketing_features = build_ticketing_features(
        bookings,
        booking_flights,
        booking_passengers,
        days=None,
    )

    session_features = build_session_features(
        search_sessions,
        days=None,
    )

    refund_features = build_refund_features(
        refund_requests,
        bookings,
        days=None,
    )

    credit_features = build_credit_features(
        credit_requests,
        days=None,
    )

    wallet_features = build_wallet_features(
        wallet_transactions,
        days=None,
    )

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

    features = add_time_series_features(
        features=features,
        bookings=bookings,
    )

    features["feature_snapshot_date"] = snapshot_date

    return features


def build_temporal_training_dataset() -> pd.DataFrame:
    logger.info("Loading existing database tables for temporal training.")

    suppliers = read_table("suppliers")
    bookings = read_table("bookings")
    booking_processes = read_table("booking_processes")
    booking_flights = read_table("booking_flights")
    booking_passengers = read_table("booking_passengers")
    search_sessions = read_table("search_sessions")
    refund_requests = read_table("refund_requests")
    credit_requests = read_table("credit_requests")
    wallet_transactions = read_table("wallet_transactions")

    if bookings.empty:
        raise ValueError(
            "Bookings table is empty. Temporal training cannot continue."
        )

    if "booking_date" not in bookings.columns:
        raise ValueError(
            "bookings.booking_date column is required for temporal training."
        )

    bookings = _convert_datetime(
        bookings,
        "booking_date",
    )

    bookings = bookings.dropna(
        subset=["booking_date"]
    ).copy()

    if bookings.empty:
        raise ValueError(
            "No valid booking_date values found."
        )

    minimum_booking_date = bookings["booking_date"].min()
    maximum_booking_date = bookings["booking_date"].max()

    first_snapshot_date = (
        minimum_booking_date
        + pd.Timedelta(days=FEATURE_WINDOW_DAYS)
    )

    last_snapshot_date = (
        maximum_booking_date
        - pd.Timedelta(days=FUTURE_WINDOW_DAYS)
    )

    if first_snapshot_date > last_snapshot_date:
        raise ValueError(
            "Not enough booking history. "
            f"At least {FEATURE_WINDOW_DAYS + FUTURE_WINDOW_DAYS} "
            "days of data are required."
        )

    snapshot_dates = pd.date_range(
        start=first_snapshot_date.normalize(),
        end=last_snapshot_date.normalize(),
        freq=f"{SNAPSHOT_STEP_DAYS}D",
    )

    all_snapshots: list[pd.DataFrame] = []

    for snapshot_date in snapshot_dates:
        feature_start_date = (
            snapshot_date
            - pd.Timedelta(days=FEATURE_WINDOW_DAYS)
        )

        future_end_date = (
            snapshot_date
            + pd.Timedelta(days=FUTURE_WINDOW_DAYS)
        )

        past_bookings = _filter_date_window(
            bookings,
            "booking_date",
            feature_start_date,
            snapshot_date,
        )

        future_bookings = _filter_date_window(
            bookings,
            "booking_date",
            snapshot_date,
            future_end_date,
        )

        if past_bookings.empty:
            continue

        past_booking_processes = _filter_date_window(
            booking_processes,
            "created_at",
            feature_start_date,
            snapshot_date,
        )

        past_booking_flights = _filter_date_window(
            booking_flights,
            "created_at",
            feature_start_date,
            snapshot_date,
        )

        past_booking_passengers = _filter_booking_passengers(
            booking_passengers,
            past_bookings,
        )

        past_search_sessions = _filter_date_window(
            search_sessions,
            "created_at",
            feature_start_date,
            snapshot_date,
        )

        past_refund_requests = _filter_date_window(
            refund_requests,
            "created_at",
            feature_start_date,
            snapshot_date,
        )

        past_credit_requests = _filter_date_window(
            credit_requests,
            "created_at",
            feature_start_date,
            snapshot_date,
        )

        past_wallet_transactions = _filter_date_window(
            wallet_transactions,
            "created_at",
            feature_start_date,
            snapshot_date,
        )

        snapshot_features = _build_snapshot_features(
            suppliers=suppliers,
            bookings=past_bookings,
            booking_processes=past_booking_processes,
            booking_flights=past_booking_flights,
            booking_passengers=past_booking_passengers,
            search_sessions=past_search_sessions,
            refund_requests=past_refund_requests,
            credit_requests=past_credit_requests,
            wallet_transactions=past_wallet_transactions,
            snapshot_date=snapshot_date,
        )

        future_labels = _build_future_labels(
            suppliers=suppliers,
            future_bookings=future_bookings,
        )

        snapshot_features = snapshot_features.merge(
            future_labels,
            on="supplier_code",
            how="left",
        )

        snapshot_features[
            "observed_failure_next_7d"
        ] = (
            snapshot_features[
                "observed_failure_next_7d"
            ]
            .fillna(0)
            .astype(int)
        )

        all_snapshots.append(snapshot_features)

    if not all_snapshots:
        raise ValueError(
            "No temporal training snapshots were created."
        )

    training_dataset = pd.concat(
        all_snapshots,
        ignore_index=True,
    )

    training_dataset = training_dataset.sort_values(
        ["feature_snapshot_date", "supplier_code"]
    ).reset_index(drop=True)

    label_counts = (
        training_dataset[
            "observed_failure_next_7d"
        ]
        .value_counts()
        .to_dict()
    )

    logger.info(
        "Temporal training dataset created. Rows: %s, snapshots: %s, labels: %s",
        len(training_dataset),
        training_dataset["feature_snapshot_date"].nunique(),
        label_counts,
    )

    return training_dataset