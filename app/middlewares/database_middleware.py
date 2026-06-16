from fastapi import Request


async def database_middleware(
    request: Request,
    call_next,
):
    try:
        response = await call_next(request)
        return response

    except Exception:
        raise

    finally:
        try:
            from app.infra.database import engine

            engine.dispose()

        except Exception:
            pass