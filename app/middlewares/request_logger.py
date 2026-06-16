import time
import uuid

from fastapi import Request


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

    print(
        f"[{request_id}] "
        f"{request.method} "
        f"{request.url.path} "
        f"{response.status_code} "
        f"{process_time}s"
    )

    return response