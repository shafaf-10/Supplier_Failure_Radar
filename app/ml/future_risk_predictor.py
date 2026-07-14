
import pandas as pd

from app.ml.model_thresholds import FEATURE_WEIGHTS, WARNING_THRESHOLDS


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(value, maximum))


def get_lead_signal(row: pd.Series) -> str:
    signals = {
        "Booking Failure": row.get("failure_rate", 0),
        "Pending Booking": row.get("pending_rate", 0),
        "Process Error": row.get("process_error_rate", 0),
        "Refund Risk": row.get("refund_rate", 0),
        "Credit Rejection": row.get("credit_rejection_rate", 0),
        "Search Failure": row.get("search_failure_rate", 0),
        "Wallet Risk": row.get("wallet_risk_rate", 0),
    }

    max_score = max(signals.values())

    top_signals = [
        signal
        for signal, score in signals.items()
        if score == max_score
    ]

    return " / ".join(sorted(top_signals))


def calculate_future_instability_probability(
    row: pd.Series,
) -> float:
    weighted_score = 0.0

    for feature, weight in FEATURE_WEIGHTS.items():
        weighted_score += (
            float(row.get(feature, 0) or 0)
            * float(weight)
        )

    risk_score = float(
        row.get("risk_score", 0) or 0
    ) / 100

    weighted_score = (
        weighted_score * 1.80
        + risk_score * 0.80
    )

    probability = clamp(weighted_score)

    return round(probability, 4)


def get_early_warning_status(probability: float) -> str:
    t = WARNING_THRESHOLDS

    if probability >= t["CRITICAL"]:
        return "CRITICAL_WARNING"

    if probability >= t["WARNING"]:
        return "WARNING"

    if probability >= t["WATCH"]:
        return "WATCHLIST"

    return "STABLE"


def get_future_prediction_confidence(probability: float) -> str:
    t = WARNING_THRESHOLDS

    if probability >= t["CRITICAL"] or probability <= 0.20:
        return "HIGH"

    if probability >= t["WARNING"]:
        return "MEDIUM"

    return "LOW"

def get_future_unavailability_severity(
    probability: float,
) -> str:
    if probability >= 0.75:
        return "HIGH"

    if probability >= 0.45:
        return "MEDIUM"

    return "LOW"


def generate_future_risk_recommendation(row: pd.Series) -> str:
    probability = row.get(
    "future_instability_probability",
    0,
)

    lead_signal = row.get(
    "lead_signal",
    "Operational Risk",
)

    status = row.get(
    "early_warning_status",
    "STABLE",
)

    prediction_horizon = row.get(
    "future_risk_window",
    "NEXT_7_DAYS",
)

    readable_horizon = {
    "NEXT_24_HOURS": "the next 24 hours",
    "NEXT_3_DAYS": "the next 3 days",
    "NEXT_7_DAYS": "the next 7 days",
}.get(
    prediction_horizon,
    "the next 7 days",
)

    pct = round(probability * 100, 1)

    if status == "CRITICAL_WARNING":
        return (
            f"High probability of supplier instability in {readable_horizon} "
            f"({pct}%). Primary lead signal: {lead_signal}. "
            f"Reduce dependency, keep backup supplier ready, and monitor closely."
        )

    if status == "WARNING":
        return (
            f"High probability of supplier instability in {readable_horizon} "
            f"({pct}%). Primary lead signal: {lead_signal}. "
            f"Monitor operations and prepare fallback routing."
        )

    if status == "WATCHLIST":
        return (
            f"Supplier should be kept on watchlist. Instability probability is {pct}%. "
            f"Main signal: {lead_signal}."
        )

    return (
        f"Supplier appears stable for {readable_horizon}. "
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

    output["future_unavailability_severity"] = output[
    "future_instability_probability"
].apply(
    get_future_unavailability_severity
)

    output["future_recommendation"] = output.apply(
        generate_future_risk_recommendation,
        axis=1,
    )

    return output