import os
import requests

from app.observability.logger import setup_logger

logger = setup_logger(__name__)


def send_webhook(message: dict) -> None:
    webhook_url = os.getenv("WEBHOOK_URL")

    if not webhook_url:
        logger.warning("WEBHOOK_URL is not configured. Webhook skipped.")
        return

    try:
        response = requests.post(
            webhook_url,
            json=message,
            timeout=5,
        )

        response.raise_for_status()
        logger.info("Webhook notification sent successfully.")

    except Exception as error:
        logger.exception("Webhook notification failed: %s", error)