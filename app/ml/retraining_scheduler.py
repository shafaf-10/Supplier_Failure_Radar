import threading
import time
from datetime import datetime, timedelta

from app.ml.train_model import train_models
from app.observability.logger import setup_logger


logger = setup_logger(__name__)

_RETRAIN_LOCK = threading.Lock()
_LAST_RETRAIN_TIME: datetime | None = None

MIN_RETRAIN_INTERVAL_MINUTES = 30


def retrain_models_if_needed(reason: str = "scheduled") -> bool:
    global _LAST_RETRAIN_TIME

    now = datetime.now()

    if _LAST_RETRAIN_TIME is not None:
        elapsed = now - _LAST_RETRAIN_TIME

        if elapsed < timedelta(minutes=MIN_RETRAIN_INTERVAL_MINUTES):
            logger.info(
                "Skipping retraining. Last retrain was %.2f minutes ago.",
                elapsed.total_seconds() / 60,
            )
            return False

    if not _RETRAIN_LOCK.acquire(blocking=False):
        logger.info("Skipping retraining because another retraining job is running.")
        return False

    try:
        logger.info("Starting model retraining. Reason: %s", reason)
        train_models()
        _LAST_RETRAIN_TIME = datetime.now()
        logger.info("Model retraining completed successfully.")
        return True

    except Exception:
        logger.exception("Model retraining failed.")
        return False

    finally:
        _RETRAIN_LOCK.release()


def start_retraining_scheduler(interval_minutes: int = 60) -> None:
    def scheduler_loop():
        while True:
            time.sleep(interval_minutes * 60)
            retrain_models_if_needed(reason="scheduled_feedback_loop")

    thread = threading.Thread(
        target=scheduler_loop,
        daemon=True,
        name="model-retraining-scheduler",
    )

    thread.start()
    logger.info(
        "Model retraining scheduler started. Interval: %s minutes",
        interval_minutes,
    )