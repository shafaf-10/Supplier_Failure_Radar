from contextlib import asynccontextmanager
from datetime import datetime

import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.infra.redis_provider import clear_supplier_cache
from app.infra.settings import settings
from app.middlewares.error_handler import error_handler_middleware
from app.middlewares.request_logger import request_logger_middleware
from app.ml.pipeline import run_prediction_pipeline
from app.observability.logger import setup_logger
from app.services.cache_adapter import CacheAdapter
from app.services.supplier_prediction_service import SupplierPredictionService


logger = setup_logger(__name__)
scheduler = BackgroundScheduler()


def scheduled_supplier_pipeline():
    try:
        logger.info("Scheduled supplier prediction pipeline started.")

        prediction_df = run_prediction_pipeline()

        suppliers = [
            SupplierPredictionService._clean_supplier_record(row)
            for row in prediction_df.to_dict(orient="records")
        ]

        suppliers = sorted(
            suppliers,
            key=lambda item: item["risk_score"],
            reverse=True,
        )

        latest_date = datetime.now().isoformat(timespec="seconds")

        response = {
            "period": "all",
            "latest_date": latest_date,
            "summary": SupplierPredictionService._build_summary(suppliers),
            "suppliers": suppliers,
        }

        clear_supplier_cache()

        CacheAdapter.set(
            "supplier_predictions:all",
            response,
            expiry_seconds=300,
        )

        logger.info(
            "Scheduled supplier pipeline completed and cached in Redis."
        )

    except Exception as error:
        logger.exception(
            "Scheduled supplier pipeline failed: %s",
            error,
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

app.middleware("http")(error_handler_middleware)
app.middleware("http")(request_logger_middleware)
# app.middleware("http")(database_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {
        "message": "Supplier Failure Radar API is running"
    }