from app.infra.redis_provider import (
    get_cache,
    set_cache,
    delete_cache,
)


class CacheAdapter:

    @staticmethod
    def get(key):
        return get_cache(key)

    @staticmethod
    def set(
        key,
        value,
        expiry_seconds=300,
    ):
        return set_cache(
            key,
            value,
            expiry_seconds,
        )

    @staticmethod
    def delete(key):
        return delete_cache(key)