from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.infra.settings import settings
from app.middlewares.error_handler import error_handler_middleware
from app.middlewares.request_logger import request_logger_middleware
from app.middlewares.rate_limiter import rate_limit_middleware
from app.observability.logger import setup_logger
from app.observability.metrics import metrics_response
from app.services.supplier_prediction_service import SupplierPredictionService

logger = setup_logger(__name__)
scheduler = BackgroundScheduler()
_scheduler_failure_count = 0


def scheduled_supplier_pipeline():
    global _scheduler_failure_count

    try:
        logger.info("Scheduled supplier prediction pipeline started.")

        SupplierPredictionService.get_predictions(period="all")
        _scheduler_failure_count = 0

        logger.info("Scheduled supplier pipeline completed and cached in Redis.")

    except Exception as error:
        _scheduler_failure_count += 1

        logger.exception(
            "Scheduled supplier pipeline failed. Consecutive failures: %s. Error: %s",
            _scheduler_failure_count,
            error,
        )

        if _scheduler_failure_count >= 3:
            logger.error(
                "ALERT: Supplier prediction scheduler failed %s times consecutively.",
                _scheduler_failure_count,
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        scheduled_supplier_pipeline,
        trigger="interval",
        minutes=15,
        id="supplier_prediction_pipeline",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started. Supplier pipeline runs every 15 minutes.")

    yield

    scheduler.shutdown()
    logger.info("Scheduler stopped.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "supplier-failure-radar",
    }


@app.get("/metrics")
def metrics():
    return metrics_response()


app.middleware("http")(error_handler_middleware)
app.middleware("http")(request_logger_middleware)
app.middleware("http")(rate_limit_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {
        "message": "Supplier Failure Radar API is running",
    }