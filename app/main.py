
from app.middlewares.request_logger import (
    request_logger_middleware,
)

from app.middlewares.error_handler import (
    error_handler_middleware,
)

from app.middlewares.database_middleware import (
    database_middleware,
)
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.infra.settings import settings
from app.infra.redis_provider import clear_supplier_cache



scheduler = BackgroundScheduler()


def scheduled_supplier_pipeline():
    try:
        from app.ml.pipeline import run_prediction_pipeline

        run_prediction_pipeline()
        
        clear_supplier_cache()
        print("Scheduled supplier pipeline completed.")
    except Exception as error:
        print(f"Scheduled supplier pipeline failed: {error}")


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
    print("Scheduler started. Supplier pipeline runs every 15 minutes.")

    yield

    scheduler.shutdown()
    print("Scheduler stopped.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)
app.middleware("http")(
    error_handler_middleware
)

app.middleware("http")(
    request_logger_middleware
)

app.middleware("http")(
    database_middleware
)

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