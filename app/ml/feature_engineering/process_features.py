import pandas as pd

from app.ml.feature_engineering.helpers import to_dt, safe_rate


def build_process_features(booking_processes, days=None):
    if booking_processes is None or booking_processes.empty:
        return pd.DataFrame()

    booking_processes = booking_processes.copy()

    booking_processes = to_dt(
        booking_processes,
        [
            "created_at",
            "updated_at",
            "last_transition_at",
        ],
    )

    if days is not None and "created_at" in booking_processes.columns:
        latest_date = booking_processes["created_at"].max()

        booking_processes = booking_processes[
            booking_processes["created_at"]
            >= latest_date - pd.Timedelta(days=days)
        ]

    if booking_processes.empty:
        return pd.DataFrame()

    state = booking_processes["state"].astype(str).str.upper()

    booking_processes["bp_is_error"] = state.isin(
        ["FAILED", "ERROR", "CANCELLED"]
    ).astype(int)

    booking_processes["bp_is_completed"] = state.isin(
        ["COMPLETED", "ISSUED", "TICKETED"]
    ).astype(int)

    booking_processes["bp_is_stuck"] = state.isin(
        [
            "PENDING",
            "PROCESSING",
            "HOLDING",
            "ON_HOLD",
            "CONFIRMATION_PENDING",
            "STUCK",
            "RETRYING",
        ]
    ).astype(int)

    booking_processes["bp_high_retry"] = (
        booking_processes["attempts"].fillna(0) >= 3
    ).astype(int)

    process_agg = booking_processes.groupby("provider_code").agg(
        bp_total=("provider_code", "count"),
        bp_errors=("bp_is_error", "sum"),
        bp_completed=("bp_is_completed", "sum"),
        bp_stuck=("bp_is_stuck", "sum"),
        bp_attempts_mean=("attempts", "mean"),
        bp_high_retry=("bp_high_retry", "sum"),
    ).reset_index()

    process_agg = process_agg.rename(
        columns={"provider_code": "supplier_code"}
    )

    total = process_agg["bp_total"]

    process_agg["bp_error_rate"] = safe_rate(
        process_agg["bp_errors"],
        total,
    ).fillna(0)

    process_agg["bp_stuck_rate"] = safe_rate(
        process_agg["bp_stuck"],
        total,
    ).fillna(0)


    process_agg["bp_high_retry_rate"] = safe_rate(
        process_agg["bp_high_retry"],
        total,
    ).fillna(0)

    return process_agg.fillna(0)