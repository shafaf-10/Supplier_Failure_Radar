from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.infra.settings import settings
from app.middlewares.error_handler import error_handler_middleware
from app.middlewares.rate_limiter import rate_limit_middleware
from app.middlewares.request_logger import request_logger_middleware
from app.observability.logger import setup_logger
from app.observability.metrics import metrics_response

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API startup complete. Scheduled jobs now run via Celery Beat, not in-process.")
    yield
    logger.info("API shutdown.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)


# FastAPI registers this function through the route decorator.
@app.get("/health")
def health_check():  # noqa
    return {
        "status": "ok",
        "service": "supplier-failure-radar",
    }


# FastAPI registers this function through the route decorator.
@app.get("/metrics")
def metrics():  # noqa
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


# FastAPI registers this function through the route decorator.
@app.get("/")
def root():  # noqa
    return {
        "message": "Supplier Failure Radar API is running",
    }