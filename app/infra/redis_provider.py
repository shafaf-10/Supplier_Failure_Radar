import json

from app.infra.settings import settings
from app.observability.logger import setup_logger

logger = setup_logger(__name__)

try:
    import redis
except Exception:
    redis = None


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

except Exception as error:
    logger.warning("Redis connection failed: %s", error)
    redis_client = None


def get_cache(key):
    if redis_client is None:
        return None

    try:
        data = redis_client.get(key)

        if data is None:
            return None

        return json.loads(data)

    except Exception as error:
        logger.warning("Redis get failed for key %s: %s", key, error)
        return None


def set_cache(key, value, expiry_seconds=300):
    if redis_client is None:
        logger.warning("Redis not connected. Cache set skipped for key: %s", key)
        return

    try:
        logger.info("Writing to Redis cache key: %s", key)

        redis_client.setex(
            key,
            expiry_seconds,
            json.dumps(value, default=str),
        )

    except Exception as error:
        logger.warning("Redis set failed for key %s: %s", key, error)


def delete_cache(key):
    if redis_client is None:
        return

    try:
        redis_client.delete(key)

    except Exception as error:
        logger.warning("Redis delete failed for key %s: %s", key, error)
