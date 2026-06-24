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
    
    @staticmethod
    def clear_supplier_predictions() -> None:
        """
        Clear cached supplier prediction results.
        Safe method used after model refresh.
        """
        CacheAdapter._cache.pop("supplier_predictions", None)


    @staticmethod
    def clear_supplier_predictions() -> None:
        """
        Clear supplier prediction cache keys.
        Current Redis adapter supports deleting one key at a time.
        """
        delete_cache("supplier_predictions:all")
        delete_cache("supplier_predictions:24h")
        delete_cache("supplier_predictions:7d")
        delete_cache("supplier_predictions:30d")
        delete_cache("supplier_predictions:1y")