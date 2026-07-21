import pandas as pd

from app.ml.model_thresholds import (
    FEATURE_WEIGHTS,
    WARNING_THRESHOLDS,
)


HEURISTIC_PREDICTION_SOURCE = "HEURISTIC"
HEURISTIC_PREDICTION_METHOD = "WEIGHTED_RULES"


def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(
        minimum,
        min(value, maximum),
    )


def get_lead_signal(
    row: pd.Series,
) -> str:
    signals = {
        "Booking Failure": row.get(
            "failure_rate",
            0,
        ),
        "Pending Booking": row.get(
            "pending_rate",
            0,
        ),
        "Process Error": row.get(
            "process_error_rate",
            0,
        ),
        "Refund Risk": row.get(
            "refund_rate",
            0,
        ),
        "Credit Rejection": row.get(
            "credit_rejection_rate",
            0,
        ),
        "Search Failure": row.get(
            "search_failure_rate",
            0,
        ),
        "Wallet Risk": row.get(
            "wallet_risk_rate",
            0,
        ),
    }

    normalized_signals = {
        signal: float(score or 0)
        for signal, score in signals.items()
    }

    max_score = max(
        normalized_signals.values()
    )

    top_signals = [
        signal
        for signal, score
        in normalized_signals.items()
        if score == max_score
    ]

    return " / ".join(
        sorted(top_signals)
    )


def calculate_future_instability_probability(
    row: pd.Series,
) -> float:
    """
    Calculate a rule-based instability estimate.

    Important:
    This function is not a machine-learning model.
    Its weights are manually configured through
    FEATURE_WEIGHTS.
    """

    weighted_score = 0.0

    for feature, weight in FEATURE_WEIGHTS.items():
        feature_value = float(
            row.get(
                feature,
                0,
            )
            or 0
        )

        weighted_score += (
            feature_value
            * float(weight)
        )

    risk_score = float(
        row.get(
            "risk_score",
            0,
        )
        or 0
    ) / 100

    weighted_score = (
        weighted_score * 1.80
        + risk_score * 0.80
    )

    probability = clamp(
        weighted_score
    )

    return round(
        probability,
        4,
    )


def get_early_warning_status(
    probability: float,
) -> str:
    thresholds = WARNING_THRESHOLDS

    if probability >= thresholds["CRITICAL"]:
        return "CRITICAL_WARNING"

    if probability >= thresholds["WARNING"]:
        return "WARNING"

    if probability >= thresholds["WATCH"]:
        return "WATCHLIST"

    return "STABLE"


def get_future_prediction_confidence(
    probability: float,
) -> str:
    """
    Return confidence in the heuristic warning level.

    This is not statistical ML confidence.
    """

    thresholds = WARNING_THRESHOLDS

    if (
        probability >= thresholds["CRITICAL"]
        or probability <= 0.20
    ):
        return "HIGH"

    if probability >= thresholds["WARNING"]:
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


def generate_future_risk_recommendation(
    row: pd.Series,
) -> str:
    probability = float(
        row.get(
            "future_instability_probability",
            0,
        )
        or 0
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
        "NEXT_24_HOURS": (
            "the next 24 hours"
        ),
        "NEXT_3_DAYS": (
            "the next 3 days"
        ),
        "NEXT_7_DAYS": (
            "the next 7 days"
        ),
    }.get(
        prediction_horizon,
        "the next 7 days",
    )

    percentage = round(
        probability * 100,
        1,
    )

    if status == "CRITICAL_WARNING":
        return (
            "Heuristic rules indicate a high "
            f"instability risk for {readable_horizon} "
            f"({percentage}%). Primary signal: "
            f"{lead_signal}. Reduce dependency, "
            "keep a backup supplier ready, and "
            "monitor closely. This is not an ML "
            "forecast."
        )

    if status == "WARNING":
        return (
            "Heuristic rules indicate elevated "
            f"instability risk for {readable_horizon} "
            f"({percentage}%). Primary signal: "
            f"{lead_signal}. Monitor operations "
            "and prepare fallback routing. This is "
            "not an ML forecast."
        )

    if status == "WATCHLIST":
        return (
            "Heuristic rules place this supplier "
            f"on the watchlist with a {percentage}% "
            f"risk estimate. Main signal: "
            f"{lead_signal}. This is not an ML "
            "forecast."
        )

    return (
        "Heuristic rules indicate that the "
        f"supplier appears stable for "
        f"{readable_horizon}. The rule-based "
        f"risk estimate is {percentage}%. "
        "This is not an ML forecast."
    )


def add_future_risk_predictions(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add rule-based fallback estimates.

    This function must only be used when the
    trained future ML model is unavailable.
    """

    if df is None or df.empty:
        return df

    output = df.copy()

    for column in FEATURE_WEIGHTS.keys():
        if column not in output.columns:
            output[column] = 0

    if "risk_score" not in output.columns:
        output["risk_score"] = 0

    output["lead_signal"] = output.apply(
        get_lead_signal,
        axis=1,
    )

    output[
        "future_instability_probability"
    ] = output.apply(
        calculate_future_instability_probability,
        axis=1,
    )

    output["future_risk_window"] = (
        "NEXT_7_DAYS"
    )

    output[
        "early_warning_status"
    ] = output[
        "future_instability_probability"
    ].apply(
        get_early_warning_status
    )

    output[
        "future_unavailability_severity"
    ] = output[
        "future_instability_probability"
    ].apply(
        get_future_unavailability_severity
    )

    output[
        "prediction_confidence"
    ] = output[
        "future_instability_probability"
    ].apply(
        get_future_prediction_confidence
    )

    # Explicitly identify that this result is
    # rule-based and not machine learning.
    output["prediction_source"] = (
        HEURISTIC_PREDICTION_SOURCE
    )

    output["prediction_method"] = (
        HEURISTIC_PREDICTION_METHOD
    )

    output["ml_prediction"] = False

    output["model_available"] = False

    output["prediction_disclaimer"] = (
        "Rule-based fallback generated from "
        "manually configured feature weights. "
        "This result is not an ML forecast."
    )

    output[
        "future_recommendation"
    ] = output.apply(
        generate_future_risk_recommendation,
        axis=1,
    )

    return output