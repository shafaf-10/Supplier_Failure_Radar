from fastapi import Request
from fastapi.responses import JSONResponse

from app.observability.logger import setup_logger

logger = setup_logger(__name__)


async def error_handler_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response

    except Exception as error:
        logger.exception(
            "Unhandled error occurred. Method=%s Path=%s Error=%s",
            request.method,
            request.url.path,
            error,
        )

        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Internal server error",
            },
        )