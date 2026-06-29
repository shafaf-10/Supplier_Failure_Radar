def get_recommendation(
    risk_level: str,
    anomaly_status: str,
) -> str:
    if anomaly_status == "ANOMALY":
        return (
            "Immediate investigation required. Check booking failures, "
            "API retries, ticketing SLA, refund delay, search timeout, "
            "credit exposure, and wallet failed payments."
        )

    if risk_level == "HIGH_RISK":
        return (
            "Supplier is high risk. Reduce dependency, monitor ticketing SLA, "
            "refund delays, high retries, and wallet exposure."
        )

    if risk_level == "MEDIUM_RISK":
        return (
            "Supplier needs monitoring. Watch booking pending rate, process retry, "
            "search completion gap, refund pending rate, and wallet holds."
        )

    return "Supplier is stable. Continue normal monitoring."