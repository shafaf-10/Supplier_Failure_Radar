import pandas as pd

from app.ml.feature_engineering.helpers import to_dt, safe_rate


def build_booking_features(bookings, days=None):
    if bookings is None or bookings.empty:
        return pd.DataFrame()

    bookings = bookings.copy()

    bookings = to_dt(
        bookings,
        [
            "booking_date",
            "issue_date",
            "created_at",
            "updated_at",
            "last_ticketing_date",
        ],
    )

    if days is not None and "booking_date" in bookings.columns:
        latest_date = bookings["booking_date"].max()

        bookings = bookings[
            bookings["booking_date"]
            >= latest_date - pd.Timedelta(days=days)
        ]

    if bookings.empty:
        return pd.DataFrame()

    status = bookings["status"].astype(str).str.upper()

    bookings["is_failed"] = status.isin(["FAILED", "EXPIRED"]).astype(int)
    bookings["is_pending"] = status.isin(["PENDING", "ON_HOLD", "HOLD"]).astype(int)
    bookings["is_issued"] = status.isin(["ISSUED", "TICKETED", "CONFIRMED"]).astype(int)
    bookings["is_cancelled"] = status.isin(["CANCELLED", "CANCELED"]).astype(int)

    bookings["issue_delay_hours"] = (
        bookings["issue_date"] - bookings["booking_date"]
    ).dt.total_seconds() / 3600

    bookings["deadline_missed"] = (
        bookings["last_ticketing_date"].notna()
        & bookings["issue_date"].isna()
    ).astype(int)

    booking_agg = bookings.groupby("provider").agg(
        b_total=("provider", "count"),
        b_failed=("is_failed", "sum"),
        b_pending=("is_pending", "sum"),
        b_issued=("is_issued", "sum"),
        b_cancelled=("is_cancelled", "sum"),
        b_amount_sum=("total_amount", "sum"),
        b_amount_mean=("total_amount", "mean"),
        b_issue_delay_mean=("issue_delay_hours", "mean"),
        b_deadline_missed=("deadline_missed", "sum"),
    ).reset_index()

    booking_agg = booking_agg.rename(
        columns={"provider": "supplier_code"}
    )

    total = booking_agg["b_total"]

    booking_agg["b_failure_rate"] = safe_rate(
        booking_agg["b_failed"],
        total,
    ).fillna(0)

    booking_agg["b_pending_rate"] = safe_rate(
        booking_agg["b_pending"],
        total,
    ).fillna(0)

    booking_agg["b_cancellation_rate"] = safe_rate(
        booking_agg["b_cancelled"],
        total,
    ).fillna(0)

    booking_agg["b_deadline_miss_rate"] = safe_rate(
        booking_agg["b_deadline_missed"],
        total,
    ).fillna(0)


    booking_agg["b_estimated_failure_loss"] = (
        booking_agg["b_failure_rate"]
        * booking_agg["b_amount_sum"]
    )

    return booking_agg.fillna(0)