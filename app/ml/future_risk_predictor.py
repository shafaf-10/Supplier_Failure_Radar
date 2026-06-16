import pandas as pd


FEATURE_WEIGHTS = {
    "failure_rate": 0.18,
    "pending_rate": 0.10,
    "process_error_rate": 0.16,
    "refund_rate": 0.10,
    "credit_rejection_rate": 0.10,
    "search_failure_rate": 0.20,
    "wallet_risk_rate": 0.16,
}


def clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(value, maximum))


def get_lead_signal(row):
    signals = {
        "Booking Failure": row.get("failure_rate", 0),
        "Pending Booking": row.get("pending_rate", 0),
        "Process Error": row.get("process_error_rate", 0),
        "Refund Risk": row.get("refund_rate", 0),
        "Credit Rejection": row.get("credit_rejection_rate", 0),
        "Search Failure": row.get("search_failure_rate", 0),
        "Wallet Risk": row.get("wallet_risk_rate", 0),
    }

    return max(signals, key=signals.get)


def calculate_future_instability_probability(row):
    weighted_score = 0

    for feature, weight in FEATURE_WEIGHTS.items():
        weighted_score += row.get(feature, 0) * weight

    risk_score = row.get("risk_score", 0) / 100

    weighted_score = (
    weighted_score * 1.80
    + risk_score * 0.80
)

    if str(row.get("anomaly_status", "")).upper() == "ANOMALY":
     weighted_score += 0.20

    probability = clamp(weighted_score)

    return round(probability, 4)


def get_early_warning_status(probability):
    if probability >= 0.70:
        return "CRITICAL_WARNING"

    if probability >= 0.45:
        return "WARNING"

    if probability >= 0.25:
        return "WATCHLIST"

    return "STABLE"


def get_prediction_confidence(probability):
    if probability >= 0.70 or probability <= 0.20:
        return "HIGH"

    if probability >= 0.45:
        return "MEDIUM"

    return "LOW"


def generate_future_recommendation(row):
    probability = row.get("future_instability_probability", 0)
    lead_signal = row.get("lead_signal", "Operational Risk")
    status = row.get("early_warning_status", "STABLE")

    pct = round(probability * 100, 1)

    if status == "CRITICAL_WARNING":
        return (
            f"High probability of supplier instability in the next 7 days "
            f"({pct}%). Primary lead signal: {lead_signal}. "
            f"Reduce dependency, keep backup supplier ready, and monitor closely."
        )

    if status == "WARNING":
        return (
            f"Supplier shows warning signs for possible instability in the next 7 days "
            f"({pct}%). Primary lead signal: {lead_signal}. "
            f"Monitor operations and prepare fallback routing."
        )

    if status == "WATCHLIST":
        return (
            f"Supplier should be kept on watchlist. Instability probability is {pct}%. "
            f"Main signal: {lead_signal}."
        )

    return (
        f"Supplier appears stable for the next 7 days. "
        f"Instability probability is {pct}%."
    )


def add_future_risk_predictions(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    output = df.copy()

    for col in FEATURE_WEIGHTS.keys():
        if col not in output.columns:
            output[col] = 0

    if "risk_score" not in output.columns:
        output["risk_score"] = 0

    if "anomaly_status" not in output.columns:
        output["anomaly_status"] = "NORMAL"

    output["lead_signal"] = output.apply(
        get_lead_signal,
        axis=1,
    )

    output["future_instability_probability"] = output.apply(
        calculate_future_instability_probability,
        axis=1,
    )

    output["future_risk_window"] = "NEXT_7_DAYS"

    output["early_warning_status"] = output[
        "future_instability_probability"
    ].apply(get_early_warning_status)

    output["prediction_confidence"] = output[
        "future_instability_probability"
    ].apply(get_prediction_confidence)

    output["future_recommendation"] = output.apply(
        generate_future_recommendation,
        axis=1,
    )

    return output