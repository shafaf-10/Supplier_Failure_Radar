import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse


RATE_LIMIT = 60
WINDOW_SECONDS = 60

_request_log = defaultdict(deque)


async def rate_limit_middleware(
    request: Request,
    call_next,
):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    timestamps = _request_log[client_ip]

    while timestamps and now - timestamps[0] > WINDOW_SECONDS:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded. Try again later."
            },
        )

    timestamps.append(now)

    return await call_next(request)