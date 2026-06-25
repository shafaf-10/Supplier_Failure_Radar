import pandas as pd

from app.ml.feature_engineering.helpers import safe_rate, to_dt


def build_refund_features(refund_requests, bookings, days=None):
    if refund_requests is None or refund_requests.empty:
        return pd.DataFrame()

    if bookings is None or bookings.empty:
        return pd.DataFrame()

    refunds = refund_requests.copy()
    booking_df = bookings.copy()

    refunds = to_dt(
        refunds,
        ["created_at", "updated_at", "refunded_at"],
    )

    booking_df = to_dt(
        booking_df,
        ["created_at", "booking_date", "issue_date"],
    )

    if days is not None and "created_at" in refunds.columns:
        latest_date = refunds["created_at"].max()
        cutoff = latest_date - pd.Timedelta(days=days)
        refunds = refunds[refunds["created_at"] >= cutoff]

    booking_map = booking_df[
        ["id", "provider"]
    ].rename(
        columns={
            "id": "booking_id",
            "provider": "supplier_code",
        }
    )

    refunds = refunds.merge(
        booking_map,
        on="booking_id",
        how="left",
    )

    refunds = refunds.dropna(subset=["supplier_code"])

    if refunds.empty:
        return pd.DataFrame()

    status = refunds["status"].astype(str).str.upper()

    refunds["rr_pending_flag"] = status.eq("PENDING").astype(int)
    refunds["rr_rejected_flag"] = status.eq("REJECTED").astype(int)
    refunds["rr_refunded_flag"] = status.eq("REFUNDED").astype(int)

    refunds["refund_delay_days"] = (
        refunds["refunded_at"] - refunds["created_at"]
    ).dt.total_seconds() / 86400

    refund_features = refunds.groupby("supplier_code").agg(
        rr_total=("supplier_code", "count"),
        rr_pending=("rr_pending_flag", "sum"),
        rr_rejected=("rr_rejected_flag", "sum"),
        rr_refunded=("rr_refunded_flag", "sum"),
        rr_requested_amount_sum=("requested_amount", "sum"),
        rr_refunded_amount_sum=("refunded_amount", "sum"),
        rr_avg_refund_delay_days=("refund_delay_days", "mean"),
    ).reset_index()

    total = refund_features["rr_total"]

    refund_features["rr_pending_rate"] = safe_rate(
        refund_features["rr_pending"],
        total,
    ).fillna(0)

    refund_features["rr_rejected_rate"] = safe_rate(
        refund_features["rr_rejected"],
        total,
    ).fillna(0)


    refund_features["rr_amount_recovery_rate"] = safe_rate(
        refund_features["rr_refunded_amount_sum"],
        refund_features["rr_requested_amount_sum"],
    ).fillna(0)

    refund_features["rr_refund_risk_score_100"] = (
        refund_features["rr_pending_rate"] * 35
        + refund_features["rr_rejected_rate"] * 35
        + (1 - refund_features["rr_amount_recovery_rate"]).clip(0, 1) * 20
        + (refund_features["rr_avg_refund_delay_days"].fillna(0).clip(0, 30) / 30) * 10
    ).clip(0, 100)

    return refund_features.fillna(0)