import time
from datetime import datetime

import pandas as pd

from app.infra.redis_provider import get_redis_lock
from app.ml.pipeline import run_prediction_pipeline
from app.observability.logger import setup_logger
from app.observability.metrics import (
    cache_hits_total,
    cache_misses_total,
    pipeline_duration_seconds,
    prediction_runs_total,
)
from app.services.cache_adapter import CacheAdapter
from app.services.webhook_service import send_webhook


logger = setup_logger(__name__)


class SupplierPredictionService:
    CACHE_PREFIX = "supplier_predictions"

    PERIOD_TO_DAYS = {
        "24h": 1,
        "7d": 7,
        "30d": 30,
        "1y": 365,
        "all": None,
    }

    @classmethod
    def _to_float(cls, value, default=0.0):
        try:
            if pd.isna(value):
                return default
            return float(value)
        except Exception:
            return default

    @classmethod
    def _to_int(cls, value, default=0):
        try:
            if pd.isna(value):
                return default
            return int(value)
        except Exception:
            return default

    @classmethod
    def _clean_supplier_record(cls, row):
        return {
            "supplier_code": row.get("supplier_code"),
            "supplier_name": row.get("supplier_name"),
            "total_bookings": cls._to_int(row.get("total_bookings")),
            "risk_score": round(cls._to_float(row.get("risk_score")), 2),
            "risk_level": row.get("risk_level"),
            "predicted_risk": row.get("predicted_risk"),
            "prediction_probability": round(
                cls._to_float(row.get("prediction_probability")),
                4,
            ),
            "anomaly_status": row.get("anomaly_status"),
            "anomaly_score": round(cls._to_float(row.get("anomaly_score")), 6),
            "recommendation": row.get("recommendation"),
            "future_instability_probability": round(
                cls._to_float(row.get("future_instability_probability")),
                4,
            ),
            "future_risk_window": row.get("future_risk_window"),
            "early_warning_status": row.get("early_warning_status"),
            "lead_signal": row.get("lead_signal"),
            "prediction_confidence": row.get("prediction_confidence"),
            "future_recommendation": row.get("future_recommendation"),
            "failure_rate": round(cls._to_float(row.get("failure_rate")), 4),
            "pending_rate": round(cls._to_float(row.get("pending_rate")), 4),
            "cancellation_rate": round(
                cls._to_float(row.get("cancellation_rate")),
                4,
            ),
            "process_error_rate": round(
                cls._to_float(row.get("process_error_rate")),
                4,
            ),
            "refund_rate": round(cls._to_float(row.get("refund_rate")), 4),
            "credit_rejection_rate": round(
                cls._to_float(row.get("credit_rejection_rate")),
                4,
            ),
            "search_failure_rate": round(
                cls._to_float(row.get("search_failure_rate")),
                4,
            ),
            "wallet_risk_rate": round(
                cls._to_float(row.get("wallet_risk_rate")),
                4,
            ),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

    @classmethod
    def _build_summary(cls, suppliers):
        total = len(suppliers)

        return {
            "total_suppliers": total,
            "high_risk_suppliers": sum(
                1 for s in suppliers if s["risk_level"] == "HIGH_RISK"
            ),
            "medium_risk_suppliers": sum(
                1 for s in suppliers if s["risk_level"] == "MEDIUM_RISK"
            ),
            "low_risk_suppliers": sum(
                1 for s in suppliers if s["risk_level"] == "LOW_RISK"
            ),
            "anomaly_suppliers": sum(
                1 for s in suppliers if s["anomaly_status"] == "ANOMALY"
            ),
            "critical_future_warnings": sum(
                1
                for s in suppliers
                if s["early_warning_status"] == "CRITICAL_WARNING"
            ),
            "warning_suppliers": sum(
                1
                for s in suppliers
                if s["early_warning_status"] in ["WARNING", "CRITICAL_WARNING"]
            ),
            "average_risk_score": round(
                sum(float(s["risk_score"] or 0) for s in suppliers) / total,
                2,
            )
            if total
            else 0,
            "average_future_instability_probability": round(
                (
                    sum(
                        float(s["future_instability_probability"] or 0)
                        for s in suppliers
                    )
                    / total
                )
                * 100,
                2,
            )
            if total
            else 0,
        }

    @classmethod
    def get_predictions(cls, period: str = "all"):
        cache_key = f"{cls.CACHE_PREFIX}:{period}"

        cached = CacheAdapter.get(cache_key)
        if cached:
            cache_hits_total.inc()
            logger.info("Returning supplier predictions from Redis cache.")
            return cached

        cache_misses_total.inc()
        logger.info("Cache miss. Waiting for Redis pipeline lock.")

        pipeline_lock = get_redis_lock(
            lock_name="supplier_prediction_pipeline_lock",
            timeout=300,
            blocking_timeout=30,
        )

        if pipeline_lock is None:
            logger.warning(
                "Redis lock unavailable. Running pipeline without distributed lock."
            )
            return cls._run_pipeline_and_cache(
                period=period,
                cache_key=cache_key,
            )

        with pipeline_lock:
            cached = CacheAdapter.get(cache_key)
            if cached:
                cache_hits_total.inc()
                logger.info("Cache filled by another request. Returning cached data.")
                return cached

            return cls._run_pipeline_and_cache(
                period=period,
                cache_key=cache_key,
            )

    @classmethod
    def _run_pipeline_and_cache(cls, period: str, cache_key: str):
        logger.info("Running supplier prediction pipeline in memory.")

        days = cls.PERIOD_TO_DAYS.get(period, 30)
        start_time = time.time()
        prediction_runs_total.inc()

        try:
            prediction_df = run_prediction_pipeline(days=days)
            pipeline_duration_seconds.observe(time.time() - start_time)

        except Exception as error:
            pipeline_duration_seconds.observe(time.time() - start_time)

            logger.exception(
                "Pipeline failed. Trying stale cached data. Error: %s",
                error,
            )

            stale_cached = CacheAdapter.get(cache_key)
            if stale_cached:
                stale_cached["warning"] = (
                    "Pipeline failed. Serving cached prediction data."
                )
                return stale_cached

            raise

        if prediction_df is None or prediction_df.empty:
            response = {
                "period": period,
                "latest_date": None,
                "summary": cls._build_summary([]),
                "suppliers": [],
            }

            CacheAdapter.set(
                cache_key,
                response,
                expiry_seconds=300,
            )

            return response

        prediction_df = prediction_df.sort_values(
            by="risk_score",
            ascending=False,
        )

        suppliers = [
            cls._clean_supplier_record(row)
            for row in prediction_df.to_dict(orient="records")
        ]

        for supplier in suppliers:
            if supplier["early_warning_status"] == "CRITICAL_WARNING":
                send_webhook(
                    {
                        "supplier_code": supplier["supplier_code"],
                        "supplier_name": supplier["supplier_name"],
                        "risk_level": supplier["risk_level"],
                        "future_probability": supplier[
                            "future_instability_probability"
                        ],
                    }
                )

        latest_date = datetime.now().isoformat(timespec="seconds")

        response = {
            "period": period,
            "latest_date": latest_date,
            "summary": cls._build_summary(suppliers),
            "suppliers": suppliers,
        }

        CacheAdapter.set(
            cache_key,
            response,
            expiry_seconds=60,
        )

        logger.info("Supplier predictions generated and cached successfully.")

        return response

    @classmethod
    def clear_cache(cls):
        CacheAdapter.clear_supplier_predictions()