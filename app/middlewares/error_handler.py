from fastapi import Request
from fastapi.responses import JSONResponse


async def error_handler_middleware(
    request: Request,
    call_next,
):
    try:
        response = await call_next(request)
        return response

    except Exception as error:
        print(f"ERROR: {str(error)}")

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal Server Error",
                "error": str(error),
            },
        )