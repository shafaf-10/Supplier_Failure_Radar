import pandas as pd

from app.ml.feature_engineering.helpers import safe_rate, to_dt


def build_credit_features(credit_requests, days=None):
    if credit_requests is None or credit_requests.empty:
        return pd.DataFrame()

    credits = credit_requests.copy()

    credits = to_dt(
        credits,
        [
            "created_at",
            "updated_at",
            "settlement_due_date",
            "approved_at",
            "rejected_at",
        ],
    )

    if days is not None and "created_at" in credits.columns:
        latest_date = credits["created_at"].max()
        cutoff = latest_date - pd.Timedelta(days=days)
        credits = credits[credits["created_at"] >= cutoff]

    credits = credits.dropna(subset=["supplier_code"])

    if credits.empty:
        return pd.DataFrame()

    status = credits["status"].astype(str).str.upper()

    credits["cr_rejected_flag"] = status.eq("REJECTED").astype(int)
    credits["cr_overdue_flag"] = status.eq("OVERDUE").astype(int)
    credits["cr_approved_flag"] = status.eq("APPROVED").astype(int)
    credits["cr_pending_flag"] = status.eq("PENDING").astype(int)

    credit_features = credits.groupby("supplier_code").agg(
        cr_total=("supplier_code", "count"),
        cr_rejected=("cr_rejected_flag", "sum"),
        cr_overdue=("cr_overdue_flag", "sum"),
        cr_approved=("cr_approved_flag", "sum"),
        cr_pending=("cr_pending_flag", "sum"),
        cr_amount_sum=("amount", "sum"),
        cr_avg_amount=("amount", "mean"),
        cr_avg_requested_days=("requested_credit_days", "mean"),
    ).reset_index()

    total = credit_features["cr_total"]

    credit_features["cr_rejection_rate"] = safe_rate(
        credit_features["cr_rejected"],
        total,
    ).fillna(0)

    credit_features["cr_overdue_rate"] = safe_rate(
        credit_features["cr_overdue"],
        total,
    ).fillna(0)

    credit_features["cr_pending_rate"] = safe_rate(
        credit_features["cr_pending"],
        total,
    ).fillna(0)

    credit_features["cr_credit_risk_score_100"] = (
        credit_features["cr_rejection_rate"] * 35
        + credit_features["cr_overdue_rate"] * 35
        + credit_features["cr_pending_rate"] * 20
        + (credit_features["cr_avg_requested_days"].fillna(0).clip(0, 7) / 7) * 10
    ).clip(0, 100)

    return credit_features.fillna(0)