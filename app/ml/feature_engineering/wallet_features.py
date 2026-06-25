import pandas as pd

from app.ml.feature_engineering.helpers import safe_rate, to_dt


def build_wallet_features(wallet_transactions, days=None):
    if wallet_transactions is None or wallet_transactions.empty:
        return pd.DataFrame()

    wallets = wallet_transactions.copy()

    wallets = to_dt(
        wallets,
        [
            "created_at",
            "updated_at",
            "due_date",
        ],
    )

    if days is not None and "created_at" in wallets.columns:
        latest_date = wallets["created_at"].max()
        cutoff = latest_date - pd.Timedelta(days=days)
        wallets = wallets[wallets["created_at"] >= cutoff]

    wallets = wallets.dropna(subset=["supplier_code"])

    if wallets.empty:
        return pd.DataFrame()

    wallet_type = wallets["type"].astype(str).str.upper()

    wallets["wt_failed_payment_flag"] = wallet_type.eq("FAILED_PAYMENT").astype(int)
    wallets["wt_hold_flag"] = wallet_type.eq("HOLD").astype(int)
    wallets["wt_debit_flag"] = wallet_type.eq("DEBIT").astype(int)
    wallets["wt_negative_closing_balance_flag"] = (
        wallets["closing_balance"].fillna(0) < 0
    ).astype(int)

    wallet_features = wallets.groupby("supplier_code").agg(
        wt_total=("supplier_code", "count"),
        wt_failed_payment=("wt_failed_payment_flag", "sum"),
        wt_hold=("wt_hold_flag", "sum"),
        wt_debit=("wt_debit_flag", "sum"),
        wt_negative_closing_balance=("wt_negative_closing_balance_flag", "sum"),
        wt_amount_sum=("amount", "sum"),
        wt_amount_mean=("amount", "mean"),
        wt_opening_balance_mean=("opening_balance", "mean"),
        wt_closing_balance_mean=("closing_balance", "mean"),
    ).reset_index()

    total = wallet_features["wt_total"]

    wallet_features["wt_failed_payment_rate"] = safe_rate(
        wallet_features["wt_failed_payment"],
        total,
    ).fillna(0)

    wallet_features["wt_hold_rate"] = safe_rate(
        wallet_features["wt_hold"],
        total,
    ).fillna(0)

    wallet_features["wt_debit_rate"] = safe_rate(
        wallet_features["wt_debit"],
        total,
    ).fillna(0)

    wallet_features["wt_negative_balance_rate"] = safe_rate(
        wallet_features["wt_negative_closing_balance"],
        total,
    ).fillna(0)

    wallet_features["wt_risk_rate"] = safe_rate(
        wallet_features["wt_failed_payment"]
        + wallet_features["wt_hold"]
        + wallet_features["wt_negative_closing_balance"],
        total,
    ).fillna(0)

    wallet_features["wt_wallet_risk_score_100"] = (
        wallet_features["wt_failed_payment_rate"] * 40
        + wallet_features["wt_hold_rate"] * 25
        + wallet_features["wt_negative_balance_rate"] * 25
        + wallet_features["wt_debit_rate"] * 10
    ).clip(0, 100)

    return wallet_features.fillna(0)