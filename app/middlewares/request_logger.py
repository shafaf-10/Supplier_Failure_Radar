import time
from urllib import response
import uuid

from fastapi import Request
from app.observability.logger import setup_logger

logger = setup_logger(__name__)


async def request_logger_middleware(
    request: Request,
    call_next,
):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    response = await call_next(request)

    process_time = round(
        time.time() - start_time,
        4,
    )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)

    logger.info(
    "request_id=%s method=%s path=%s status_code=%s duration=%ss",
    request_id,
    request.method,
    request.url.path,
    response.status_code,
    process_time,
    )
    return response