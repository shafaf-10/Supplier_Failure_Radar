import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

RATE_LIMIT = 60
WINDOW_SECONDS = 60

_request_log = defaultdict(deque)


def cleanup_old_clients(now: float) -> None:
    expired_clients = []

    for client_key, timestamps in _request_log.items():
        while timestamps and now - timestamps[0] > WINDOW_SECONDS:
            timestamps.popleft()

        if not timestamps:
            expired_clients.append(client_key)

    for client_key in expired_clients:
        del _request_log[client_key]


async def rate_limit_middleware(
    request: Request,
    call_next,
):
    api_key = request.headers.get("X-API-Key")
    client_key = (
        f"key:{api_key}"
        if api_key
        else f"ip:{request.client.host if request.client else 'unknown'}"
    )

    now = time.time()

    cleanup_old_clients(now)

    timestamps = _request_log[client_key]

    if len(timestamps) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded. Try again later.",
            },
        )

    timestamps.append(now)

    return await call_next(request)