import requests

from app.observability.logger import setup_logger

logger = setup_logger(__name__)


def send_webhook(message: dict) -> None:
    webhook_url = None  # Replace with config later

    if not webhook_url:
        return

    try:
        requests.post(
            webhook_url,
            json=message,
            timeout=5,
        )
    except Exception as error:
        logger.exception("Webhook notification failed: %s", error)