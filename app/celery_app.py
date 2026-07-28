from celery import Celery

from app.infra.settings import settings

REDIS_URL = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

celery_app = Celery(
    "supplier_failure_radar",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "supplier-prediction-pipeline-every-15-min": {
            "task": "app.tasks.run_supplier_pipeline",
            "schedule": 15 * 60,
        },
        "model-retraining-every-60-min": {
            "task": "app.tasks.run_model_retraining",
            "schedule": 60 * 60,
        },
    },
)