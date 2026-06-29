from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Response


prediction_runs_total = Counter(
    "supplier_prediction_runs_total",
    "Total supplier prediction pipeline runs",
)

cache_hits_total = Counter(
    "supplier_cache_hits_total",
    "Total supplier prediction cache hits",
)

cache_misses_total = Counter(
    "supplier_cache_misses_total",
    "Total supplier prediction cache misses",
)

pipeline_duration_seconds = Histogram(
    "supplier_pipeline_duration_seconds",
    "Supplier prediction pipeline duration in seconds",
)


def metrics_response():
    return Response(
        generate_latest(),
        media_type="text/plain",
    )