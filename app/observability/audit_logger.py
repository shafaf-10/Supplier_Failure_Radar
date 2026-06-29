from app.observability.logger import setup_logger

audit_logger = setup_logger("audit")


def log_prediction_view(
    request_id: str | None,
    period: str,
    limit: int,
    offset: int,
) -> None:
    audit_logger.info(
        "event=prediction_view request_id=%s period=%s limit=%s offset=%s",
        request_id,
        period,
        limit,
        offset,
    )