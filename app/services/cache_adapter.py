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
    def clear_supplier_predictions() -> None:
        """
Clear supplier prediction cache keys by deleting the known cache entries.
"""
        delete_cache("supplier_predictions:all")
        delete_cache("supplier_predictions:24h")
        delete_cache("supplier_predictions:7d")
        delete_cache("supplier_predictions:30d")
        delete_cache("supplier_predictions:1y")