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

FUTURE_HORIZONS_DAYS = {
    "24h": 1,
    "3d": 3,
    "7d": 7,
}

MAX_FUTURE_WINDOW_DAYS = max(
    FUTURE_HORIZONS_DAYS.values()
)

SNAPSHOT_STEP_DAYS = 1

HORIZON_MINIMUM_SERVICE_EVENTS = {
    "24h": 1,
    "3d": 3,
    "7d": 5,
}

FUTURE_TIMEOUT_RATE_THRESHOLD = 0.10
FUTURE_SEARCH_FAILURE_RATE_THRESHOLD = 0.20
FUTURE_PROCESS_ERROR_RATE_THRESHOLD = 0.20
FUTURE_STUCK_RATE_THRESHOLD = 0.25

FAILED_PROCESS_STATES = {
    "FAILED",
    "ERROR",
}

STUCK_PROCESS_STATES = {
    "PENDING",
    "PROCESSING",
    "HOLDING",
    "ON_HOLD",
    "CONFIRMATION_PENDING",
    "STUCK",
    "RETRYING",
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

    filtered = _convert_datetime(
        dataframe,
        date_column,
    )

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

    booking_ids = set(
        bookings["id"].dropna().tolist()
    )

    return booking_passengers[
        booking_passengers["booking_id"].isin(
            booking_ids
        )
    ].copy()


def _build_future_labels(
    suppliers: pd.DataFrame,
    future_search_sessions: pd.DataFrame,
    future_booking_processes: pd.DataFrame,
    target_column: str,
    minimum_service_events: int,
    include_severity: bool = False,
) -> pd.DataFrame:
    labels = suppliers[["code"]].copy().rename(
        columns={"code": "supplier_code"}
    )

    default_columns = {
        "future_search_count": 0,
        "future_timeout_count": 0,
        "future_search_failure_count": 0,
        "future_incomplete_response_count": 0,
        "future_process_count": 0,
        "future_process_error_count": 0,
        "future_stuck_process_count": 0,
        "future_high_retry_count": 0,
        "future_timeout_rate": 0.0,
        "future_search_failure_rate": 0.0,
        "future_incomplete_response_rate": 0.0,
        "future_process_error_rate": 0.0,
        "future_stuck_rate": 0.0,
        "future_high_retry_rate": 0.0,
        "future_service_event_count": 0,
        target_column: 0,
    }

    for column_name, default_value in default_columns.items():
        labels[column_name] = default_value

    if (
        future_search_sessions is not None
        and not future_search_sessions.empty
        and "supplier_code"
        in future_search_sessions.columns
    ):
        sessions = future_search_sessions.copy()

        if "status" in sessions.columns:
            session_status = (
                sessions["status"]
                .astype(str)
                .str.upper()
                .str.strip()
            )
        else:
            session_status = pd.Series(
                "",
                index=sessions.index,
            )

        sessions["is_timeout"] = (
            session_status.eq("TIMEOUT").astype(int)
        )

        sessions["is_search_failure"] = (
            session_status.eq("FAILED").astype(int)
        )

        if "expected_suppliers" in sessions.columns:
            expected_suppliers = pd.to_numeric(
                sessions["expected_suppliers"],
                errors="coerce",
            ).fillna(0)
        else:
            expected_suppliers = pd.Series(
                0,
                index=sessions.index,
                dtype=float,
            )

        if "completed_suppliers" in sessions.columns:
            completed_suppliers = pd.to_numeric(
                sessions["completed_suppliers"],
                errors="coerce",
            ).fillna(0)
        else:
            completed_suppliers = pd.Series(
                0,
                index=sessions.index,
                dtype=float,
            )

        sessions["is_incomplete_response"] = (
            completed_suppliers < expected_suppliers
        ).astype(int)

        session_labels = (
            sessions.groupby("supplier_code")
            .agg(
                future_search_count=(
                    "supplier_code",
                    "count",
                ),
                future_timeout_count=(
                    "is_timeout",
                    "sum",
                ),
                future_search_failure_count=(
                    "is_search_failure",
                    "sum",
                ),
                future_incomplete_response_count=(
                    "is_incomplete_response",
                    "sum",
                ),
            )
            .reset_index()
        )

        labels = labels.drop(
            columns=[
                "future_search_count",
                "future_timeout_count",
                "future_search_failure_count",
                "future_incomplete_response_count",
            ]
        ).merge(
            session_labels,
            on="supplier_code",
            how="left",
        )

    if (
        future_booking_processes is not None
        and not future_booking_processes.empty
        and "provider_code"
        in future_booking_processes.columns
    ):
        processes = future_booking_processes.copy()

        if "state" in processes.columns:
            process_state = (
                processes["state"]
                .astype(str)
                .str.upper()
                .str.strip()
            )
        else:
            process_state = pd.Series(
                "",
                index=processes.index,
            )

        processes["is_process_error"] = (
            process_state.isin(
                FAILED_PROCESS_STATES
            )
        ).astype(int)

        processes["is_stuck_process"] = (
            process_state.isin(
                STUCK_PROCESS_STATES
            )
        ).astype(int)

        if "attempts" in processes.columns:
            attempts = pd.to_numeric(
                processes["attempts"],
                errors="coerce",
            ).fillna(0)
        else:
            attempts = pd.Series(
                0,
                index=processes.index,
                dtype=float,
            )

        processes["is_high_retry"] = (
            attempts >= 3
        ).astype(int)

        process_labels = (
            processes.groupby("provider_code")
            .agg(
                future_process_count=(
                    "provider_code",
                    "count",
                ),
                future_process_error_count=(
                    "is_process_error",
                    "sum",
                ),
                future_stuck_process_count=(
                    "is_stuck_process",
                    "sum",
                ),
                future_high_retry_count=(
                    "is_high_retry",
                    "sum",
                ),
            )
            .reset_index()
            .rename(
                columns={
                    "provider_code": "supplier_code"
                }
            )
        )

        labels = labels.drop(
            columns=[
                "future_process_count",
                "future_process_error_count",
                "future_stuck_process_count",
                "future_high_retry_count",
            ]
        ).merge(
            process_labels,
            on="supplier_code",
            how="left",
        )

    labels = labels.fillna(0)

    search_count_denominator = labels[
        "future_search_count"
    ].replace(0, 1)

    process_count_denominator = labels[
        "future_process_count"
    ].replace(0, 1)

    labels["future_timeout_rate"] = (
        labels["future_timeout_count"]
        / search_count_denominator
    )

    labels["future_search_failure_rate"] = (
        labels["future_search_failure_count"]
        / search_count_denominator
    )

    labels["future_incomplete_response_rate"] = (
        labels["future_incomplete_response_count"]
        / search_count_denominator
    )

    labels["future_process_error_rate"] = (
        labels["future_process_error_count"]
        / process_count_denominator
    )

    labels["future_stuck_rate"] = (
        labels["future_stuck_process_count"]
        / process_count_denominator
    )

    labels["future_high_retry_rate"] = (
        labels["future_high_retry_count"]
        / process_count_denominator
    )

    labels["future_service_event_count"] = (
        labels["future_search_count"]
        + labels["future_process_count"]
    )

    enough_future_activity = (
        labels["future_service_event_count"]
        >= minimum_service_events
    )

    search_unavailability = (
        labels["future_timeout_rate"]
        >= FUTURE_TIMEOUT_RATE_THRESHOLD
    ) | (
        labels["future_search_failure_rate"]
        >= FUTURE_SEARCH_FAILURE_RATE_THRESHOLD
    ) | (
        labels["future_incomplete_response_rate"]
        >= FUTURE_SEARCH_FAILURE_RATE_THRESHOLD
    )

    process_unavailability = (
        labels["future_process_error_rate"]
        >= FUTURE_PROCESS_ERROR_RATE_THRESHOLD
    ) | (
        labels["future_stuck_rate"]
        >= FUTURE_STUCK_RATE_THRESHOLD
    ) | (
        labels["future_high_retry_rate"]
        >= FUTURE_STUCK_RATE_THRESHOLD
    )

    labels[target_column] = (
        enough_future_activity
        & search_unavailability
        & process_unavailability
    ).astype(int)

    selected_columns = [
        "supplier_code",
        target_column,
    ]

    if include_severity:
        severity_score = (
            labels["future_timeout_rate"]
            + labels["future_search_failure_rate"]
            + labels["future_incomplete_response_rate"]
            + labels["future_process_error_rate"]
            + labels["future_stuck_rate"]
            + labels["future_high_retry_rate"]
        ) / 6

        labels[
            "future_unavailability_severity_7d"
        ] = "LOW"

        labels.loc[
            severity_score >= 0.20,
            "future_unavailability_severity_7d",
        ] = "MEDIUM"

        labels.loc[
            severity_score >= 0.35,
            "future_unavailability_severity_7d",
        ] = "HIGH"

        labels[
            "future_unavailability_severity_score_7d"
        ] = severity_score.round(4)

        selected_columns.extend(
            [
                "future_unavailability_severity_7d",
                "future_unavailability_severity_score_7d",
            ]
        )

    return labels[selected_columns].copy()


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

    features = calculate_risk_score(
        features
    )

    features = add_backward_compatible_columns(
        features
    )

    features = add_time_series_features(
        features=features,
        bookings=bookings,
    )

    features["feature_snapshot_date"] = (
        snapshot_date
    )

    return features


def build_temporal_training_dataset() -> pd.DataFrame:
    logger.info(
        "Loading existing database tables "
        "for temporal training."
    )

    suppliers = read_table("suppliers")
    bookings = read_table("bookings")
    booking_processes = read_table(
        "booking_processes"
    )
    booking_flights = read_table(
        "booking_flights"
    )
    booking_passengers = read_table(
        "booking_passengers"
    )
    search_sessions = read_table(
        "search_sessions"
    )
    refund_requests = read_table(
        "refund_requests"
    )
    credit_requests = read_table(
        "credit_requests"
    )
    wallet_transactions = read_table(
        "wallet_transactions"
    )

    if suppliers.empty:
        raise ValueError(
            "Suppliers table is empty. "
            "Temporal training cannot continue."
        )

    if bookings.empty:
        raise ValueError(
            "Bookings table is empty. "
            "Temporal training cannot continue."
        )

    if "booking_date" not in bookings.columns:
        raise ValueError(
            "bookings.booking_date column is required "
            "for temporal training."
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

    minimum_booking_date = (
        bookings["booking_date"].min()
    )

    maximum_booking_date = (
        bookings["booking_date"].max()
    )

    first_snapshot_date = (
        minimum_booking_date
        + pd.Timedelta(
            days=FEATURE_WINDOW_DAYS
        )
    )

    last_snapshot_date = (
        maximum_booking_date
        - pd.Timedelta(
            days=MAX_FUTURE_WINDOW_DAYS
        )
    )

    if first_snapshot_date > last_snapshot_date:
        required_days = (
            FEATURE_WINDOW_DAYS
            + MAX_FUTURE_WINDOW_DAYS
        )

        raise ValueError(
            "Not enough booking history. "
            f"At least {required_days} days of data "
            "are required."
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
            - pd.Timedelta(
                days=FEATURE_WINDOW_DAYS
            )
        )

        future_end_date_24h = (
            snapshot_date
            + pd.Timedelta(
                days=FUTURE_HORIZONS_DAYS["24h"]
            )
        )

        future_end_date_3d = (
            snapshot_date
            + pd.Timedelta(
                days=FUTURE_HORIZONS_DAYS["3d"]
            )
        )

        future_end_date_7d = (
            snapshot_date
            + pd.Timedelta(
                days=FUTURE_HORIZONS_DAYS["7d"]
            )
        )

        past_bookings = _filter_date_window(
            bookings,
            "booking_date",
            feature_start_date,
            snapshot_date,
        )

        if past_bookings.empty:
            continue

        past_booking_processes = (
            _filter_date_window(
                booking_processes,
                "created_at",
                feature_start_date,
                snapshot_date,
            )
        )

        past_booking_flights = (
            _filter_date_window(
                booking_flights,
                "created_at",
                feature_start_date,
                snapshot_date,
            )
        )

        past_booking_passengers = (
            _filter_booking_passengers(
                booking_passengers,
                past_bookings,
            )
        )

        past_search_sessions = (
            _filter_date_window(
                search_sessions,
                "created_at",
                feature_start_date,
                snapshot_date,
            )
        )

        past_refund_requests = (
            _filter_date_window(
                refund_requests,
                "created_at",
                feature_start_date,
                snapshot_date,
            )
        )

        past_credit_requests = (
            _filter_date_window(
                credit_requests,
                "created_at",
                feature_start_date,
                snapshot_date,
            )
        )

        past_wallet_transactions = (
            _filter_date_window(
                wallet_transactions,
                "created_at",
                feature_start_date,
                snapshot_date,
            )
        )

        future_search_sessions_24h = (
            _filter_date_window(
                search_sessions,
                "created_at",
                snapshot_date,
                future_end_date_24h,
            )
        )

        future_booking_processes_24h = (
            _filter_date_window(
                booking_processes,
                "created_at",
                snapshot_date,
                future_end_date_24h,
            )
        )

        future_search_sessions_3d = (
            _filter_date_window(
                search_sessions,
                "created_at",
                snapshot_date,
                future_end_date_3d,
            )
        )

        future_booking_processes_3d = (
            _filter_date_window(
                booking_processes,
                "created_at",
                snapshot_date,
                future_end_date_3d,
            )
        )

        future_search_sessions_7d = (
            _filter_date_window(
                search_sessions,
                "created_at",
                snapshot_date,
                future_end_date_7d,
            )
        )

        future_booking_processes_7d = (
            _filter_date_window(
                booking_processes,
                "created_at",
                snapshot_date,
                future_end_date_7d,
            )
        )

        snapshot_features = (
            _build_snapshot_features(
                suppliers=suppliers,
                bookings=past_bookings,
                booking_processes=(
                    past_booking_processes
                ),
                booking_flights=(
                    past_booking_flights
                ),
                booking_passengers=(
                    past_booking_passengers
                ),
                search_sessions=(
                    past_search_sessions
                ),
                refund_requests=(
                    past_refund_requests
                ),
                credit_requests=(
                    past_credit_requests
                ),
                wallet_transactions=(
                    past_wallet_transactions
                ),
                snapshot_date=snapshot_date,
            )
        )

        future_labels_24h = (
            _build_future_labels(
                suppliers=suppliers,
                future_search_sessions=(
                    future_search_sessions_24h
                ),
                future_booking_processes=(
                    future_booking_processes_24h
                ),
                target_column=(
                    "observed_service_"
                    "unavailability_next_24h"
                ),
                minimum_service_events=(
                    HORIZON_MINIMUM_SERVICE_EVENTS[
                        "24h"
                    ]
                ),
            )
        )

        future_labels_3d = (
            _build_future_labels(
                suppliers=suppliers,
                future_search_sessions=(
                    future_search_sessions_3d
                ),
                future_booking_processes=(
                    future_booking_processes_3d
                ),
                target_column=(
                    "observed_service_"
                    "unavailability_next_3d"
                ),
                minimum_service_events=(
                    HORIZON_MINIMUM_SERVICE_EVENTS[
                        "3d"
                    ]
                ),
            )
        )

        future_labels_7d = (
            _build_future_labels(
                suppliers=suppliers,
                future_search_sessions=(
                    future_search_sessions_7d
                ),
                future_booking_processes=(
                    future_booking_processes_7d
                ),
                target_column=(
                    "observed_service_"
                    "unavailability_next_7d"
                ),
                minimum_service_events=(
                    HORIZON_MINIMUM_SERVICE_EVENTS[
                        "7d"
                    ]
                ),
                include_severity=True,
            )
        )

        snapshot_features = (
            snapshot_features.merge(
                future_labels_24h,
                on="supplier_code",
                how="left",
            )
        )

        snapshot_features = (
            snapshot_features.merge(
                future_labels_3d,
                on="supplier_code",
                how="left",
            )
        )

        snapshot_features = (
            snapshot_features.merge(
                future_labels_7d,
                on="supplier_code",
                how="left",
            )
        )

        future_label_columns = [
            (
                "observed_service_"
                "unavailability_next_24h"
            ),
            (
                "observed_service_"
                "unavailability_next_3d"
            ),
            (
                "observed_service_"
                "unavailability_next_7d"
            ),
        ]

        for label_column in future_label_columns:
            snapshot_features[label_column] = (
                snapshot_features[label_column]
                .fillna(0)
                .astype(int)
            )

        snapshot_features[
            "future_unavailability_severity_7d"
        ] = (
            snapshot_features[
                "future_unavailability_severity_7d"
            ]
            .fillna("LOW")
            .astype(str)
        )

        snapshot_features[
            "future_unavailability_severity_score_7d"
        ] = (
            snapshot_features[
                "future_unavailability_severity_score_7d"
            ]
            .fillna(0.0)
            .astype(float)
        )

        all_snapshots.append(
            snapshot_features
        )

    if not all_snapshots:
        raise ValueError(
            "No temporal training snapshots "
            "were created."
        )

    training_dataset = pd.concat(
        all_snapshots,
        ignore_index=True,
    )

    training_dataset = (
        training_dataset.sort_values(
            [
                "feature_snapshot_date",
                "supplier_code",
            ]
        )
        .reset_index(drop=True)
    )

    label_counts_24h = (
        training_dataset[
            "observed_service_unavailability_next_24h"
        ]
        .value_counts()
        .to_dict()
    )

    label_counts_3d = (
        training_dataset[
            "observed_service_unavailability_next_3d"
        ]
        .value_counts()
        .to_dict()
    )

    label_counts_7d = (
        training_dataset[
            "observed_service_unavailability_next_7d"
        ]
        .value_counts()
        .to_dict()
    )

    severity_counts_7d = (
        training_dataset[
            "future_unavailability_severity_7d"
        ]
        .value_counts()
        .to_dict()
    )

    logger.info(
        "Temporal training dataset created. "
        "Rows: %s, snapshots: %s, "
        "24h labels: %s, 3d labels: %s, "
        "7d labels: %s, 7d severity: %s",
        len(training_dataset),
        training_dataset[
            "feature_snapshot_date"
        ].nunique(),
        label_counts_24h,
        label_counts_3d,
        label_counts_7d,
        severity_counts_7d,
    )

    return training_dataset