import json

try:
    import redis
except Exception:
    redis = None

from app.infra.settings import settings


redis_client = None

try:
    if redis is not None:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

        redis_client.ping()

except Exception:
    redis_client = None


def get_cache(key):
    if redis_client is None:
        return None

    try:
        data = redis_client.get(key)

        if data is None:
            return None

        return json.loads(data)

    except Exception:
        return None


def set_cache(key, value, expiry_seconds=300):
    if redis_client is None:
        print("REDIS NOT CONNECTED")
        return

    try:
        print(f"WRITING TO REDIS: {key}")

        redis_client.setex(
            key,
            expiry_seconds,
            json.dumps(value, default=str),
        )

    except Exception as error:
        print(f"REDIS ERROR: {error}")

def delete_cache(key):
    if redis_client is None:
        return

    try:
        redis_client.delete(key)
    except Exception:
        return


def clear_supplier_cache():
    if redis_client is None:
        return

    try:
        keys = redis_client.keys(
            "supplier_predictions:*"
        )

        for key in keys:
            redis_client.delete(key)

    except Exception:
        return