from app.celery_app import celery_app
from app.ml.retraining_scheduler import retrain_models_if_needed
from app.observability.logger import setup_logger
from app.services.supplier_prediction_service import SupplierPredictionService

logger = setup_logger(__name__)


@celery_app.task(name="app.tasks.run_supplier_pipeline")
def run_supplier_pipeline() -> str:
    logger.info("Celery task started: supplier prediction pipeline.")
    SupplierPredictionService.get_predictions(period="all")
    logger.info("Celery task completed: supplier pipeline cached in Redis.")
    return "ok"


@celery_app.task(name="app.tasks.run_model_retraining")
def run_model_retraining() -> bool:
    logger.info("Celery task started: scheduled model retraining.")
    result = retrain_models_if_needed(reason="celery_beat_scheduled")
    logger.info("Celery task completed: model retraining triggered=%s.", result)
    return result