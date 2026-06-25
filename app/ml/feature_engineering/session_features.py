import pandas as pd

from app.ml.feature_engineering.helpers import safe_rate, to_dt


def build_session_features(search_sessions, days=None):
    if search_sessions is None or search_sessions.empty:
        return pd.DataFrame()

    sessions = search_sessions.copy()

    sessions = to_dt(
        sessions,
        [
            "created_at",
            "updated_at",
            "expires_at",
        ],
    )

    if days is not None and "created_at" in sessions.columns:
        latest_date = sessions["created_at"].max()
        cutoff = latest_date - pd.Timedelta(days=days)
        sessions = sessions[sessions["created_at"] >= cutoff]

    if sessions.empty:
        return pd.DataFrame()

    status = sessions["status"].astype(str).str.upper()

    sessions["ss_failed"] = status.eq("FAILED").astype(int)
    sessions["ss_partial"] = status.eq("PARTIAL").astype(int)
    sessions["ss_timeout"] = status.eq("TIMEOUT").astype(int)
    sessions["ss_completed"] = status.eq("COMPLETED").astype(int)

    sessions["completion_gap"] = (
        sessions["expected_suppliers"].fillna(0)
        - sessions["completed_suppliers"].fillna(0)
    ).clip(lower=0)

    sessions["completion_gap_rate"] = sessions.apply(
        lambda row: safe_rate(
            row["completion_gap"],
            row["expected_suppliers"],
        ),
        axis=1,
    )

    session_features = sessions.groupby("supplier_code").agg(
        ss_total=("supplier_code", "count"),
        ss_failed=("ss_failed", "sum"),
        ss_partial=("ss_partial", "sum"),
        ss_timeout=("ss_timeout", "sum"),
        ss_completed=("ss_completed", "sum"),
        ss_completion_gap_rate=("completion_gap_rate", "mean"),
    ).reset_index()

    total = session_features["ss_total"]

    session_features["ss_failure_rate"] = safe_rate(
        session_features["ss_failed"],
        total,
    ).fillna(0)

    session_features["ss_partial_rate"] = safe_rate(
        session_features["ss_partial"],
        total,
    ).fillna(0)

    session_features["ss_timeout_rate"] = safe_rate(
        session_features["ss_timeout"],
        total,
    ).fillna(0)


    session_features["supplier_session_risk_score_100"] = (
        session_features["ss_failure_rate"] * 30
        + session_features["ss_partial_rate"] * 20
        + session_features["ss_timeout_rate"] * 30
        + session_features["ss_completion_gap_rate"] * 20
    ).clip(0, 100)

    return session_features.fillna(0)