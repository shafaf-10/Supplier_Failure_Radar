import time
from datetime import datetime

import joblib
import pandas as pd

from app.infra.paths import MODEL_DIR
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

FUTURE_MODEL_FILE = (
    MODEL_DIR / "future_failure_model.pkl"
)


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
    def _get_model_validation_info(
        cls,
    ) -> dict:
        default_info = {
            "training_data_provenance": (
                "UNKNOWN"
            ),
            "production_validated": False,
            "prediction_status": (
                "MODEL_NOT_VALIDATED"
            ),
            "prediction_notice": (
                "Model validation information "
                "is unavailable."
            ),
        }

        if not FUTURE_MODEL_FILE.exists():
            return {
                **default_info,
                "prediction_status": (
                    "HEURISTIC_FALLBACK"
                ),
                "prediction_notice": (
                    "The trained future model is "
                    "missing. Future probabilities "
                    "may use a weighted heuristic "
                    "fallback and are not ML "
                    "forecasts."
                ),
            }

        try:
            future_bundle = joblib.load(
                FUTURE_MODEL_FILE
            )

            if not isinstance(
                future_bundle,
                dict,
            ):
                return default_info

            provenance = str(
                future_bundle.get(
                    "training_data_provenance",
                    "UNKNOWN",
                )
            ).strip().upper()

            production_validated = bool(
                future_bundle.get(
                    "production_validated",
                    False,
                )
            )

            if (
                provenance == "REAL"
                and production_validated
            ):
                return {
                    "training_data_provenance": (
                        provenance
                    ),
                    "production_validated": True,
                    "prediction_status": (
                        "PRODUCTION_VALIDATED"
                    ),
                    "prediction_notice": (
                        "Future prediction model "
                        "was trained and validated "
                        "using real supplier traffic."
                    ),
                }

            if provenance == "SYNTHETIC":
                return {
                    "training_data_provenance": (
                        provenance
                    ),
                    "production_validated": False,
                    "prediction_status": (
                        "DEVELOPMENT_ONLY"
                    ),
                    "prediction_notice": (
                        "Future probabilities come "
                        "from a model trained on "
                        "synthetic generated data. "
                        "They are for development "
                        "validation and are not "
                        "proven on real supplier "
                        "traffic."
                    ),
                }

            return {
                **default_info,
                "training_data_provenance": (
                    provenance
                ),
            }

        except Exception as error:
            logger.exception(
                "Could not read future model "
                "validation metadata: %s",
                error,
            )

            return default_info

    @classmethod
    def _to_float(
        cls,
        value,
        default: float = 0.0,
    ) -> float:
        try:
            if value is None or pd.isna(value):
                return default

            return float(value)

        except Exception:
            return default

    @classmethod
    def _to_int(
        cls,
        value,
        default: int = 0,
    ) -> int:
        try:
            if value is None or pd.isna(value):
                return default

            return int(float(value))

        except Exception:
            return default

    @classmethod
    def _clean_supplier_record(
        cls,
        row,
    ) -> dict:
        future_probability_24h = round(
            cls._to_float(
                row.get(
                    "future_probability_24h"
                )
            ),
            4,
        )

        future_probability_3d = round(
            cls._to_float(
                row.get(
                    "future_probability_3d"
                )
            ),
            4,
        )

        future_probability_7d = round(
            cls._to_float(
                row.get(
                    "future_probability_7d",
                    row.get(
                        "future_instability_probability"
                    ),
                )
            ),
            4,
        )

        future_severity = str(
            row.get(
                "future_unavailability_severity",
                "LOW",
            )
            or "LOW"
        ).upper()

        return {
            "supplier_code": row.get(
                "supplier_code"
            ),
            "supplier_name": row.get(
                "supplier_name"
            ),
            "total_bookings": cls._to_int(
                row.get(
                    "total_bookings"
                )
            ),
            "risk_score": round(
                cls._to_float(
                    row.get(
                        "risk_score"
                    )
                ),
                2,
            ),
            "risk_level": row.get(
                "risk_level"
            ),
            "predicted_risk": row.get(
                "predicted_risk"
            ),
            "prediction_probability": round(
                cls._to_float(
                    row.get(
                        "prediction_probability"
                    )
                ),
                4,
            ),
            "current_anomaly_status": row.get(
                "current_anomaly_status"
            ),
            "current_anomaly_score": round(
                cls._to_float(
                    row.get(
                        "current_anomaly_score"
                    )
                ),
                6,
            ),
            "recommendation": row.get(
                "recommendation"
            ),

            # Multi-horizon future predictions
            "future_probability_24h": (
                future_probability_24h
            ),
            "future_probability_3d": (
                future_probability_3d
            ),
            "future_probability_7d": (
                future_probability_7d
            ),
            "future_unavailability_severity": (
                future_severity
            ),

            # Backward-compatible field.
            # It represents the seven-day probability.
            "future_instability_probability": (
                future_probability_7d
            ),

            "future_risk_window": row.get(
                "future_risk_window"
            ),
            "early_warning_status": row.get(
                "early_warning_status"
            ),
            "lead_signal": row.get(
                "lead_signal"
            ),
            "prediction_confidence": row.get(
                "prediction_confidence"
            ),
            "future_recommendation": row.get(
                "future_recommendation"
            ),

            # Current supplier metrics
            "failure_rate": round(
                cls._to_float(
                    row.get(
                        "failure_rate"
                    )
                ),
                4,
            ),
            "pending_rate": round(
                cls._to_float(
                    row.get(
                        "pending_rate"
                    )
                ),
                4,
            ),
            "cancellation_rate": round(
                cls._to_float(
                    row.get(
                        "cancellation_rate"
                    )
                ),
                4,
            ),
            "process_error_rate": round(
                cls._to_float(
                    row.get(
                        "process_error_rate"
                    )
                ),
                4,
            ),
            "refund_rate": round(
                cls._to_float(
                    row.get(
                        "refund_rate"
                    )
                ),
                4,
            ),
            "credit_rejection_rate": round(
                cls._to_float(
                    row.get(
                        "credit_rejection_rate"
                    )
                ),
                4,
            ),
            "search_failure_rate": round(
                cls._to_float(
                    row.get(
                        "search_failure_rate"
                    )
                ),
                4,
            ),
            "wallet_risk_rate": round(
                cls._to_float(
                    row.get(
                        "wallet_risk_rate"
                    )
                ),
                4,
            ),
            "created_at": (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            ),
        }

    @classmethod
    def _average_probability(
        cls,
        suppliers: list[dict],
        field_name: str,
    ) -> float:
        if not suppliers:
            return 0.0

        total_probability = sum(
            cls._to_float(
                supplier.get(
                    field_name,
                    0,
                )
            )
            for supplier in suppliers
        )

        return round(
            (
                total_probability
                / len(suppliers)
            )
            * 100,
            2,
        )

    @classmethod
    def _build_summary(
        cls,
        suppliers: list[dict],
    ) -> dict:
        total = len(suppliers)

        average_risk_score = (
            round(
                sum(
                    cls._to_float(
                        supplier.get(
                            "risk_score",
                            0,
                        )
                    )
                    for supplier in suppliers
                )
                / total,
                2,
            )
            if total
            else 0
        )

        return {
            "total_suppliers": total,
            "high_risk_suppliers": sum(
                1
                for supplier in suppliers
                if supplier.get(
                    "risk_level"
                ) == "HIGH_RISK"
            ),
            "medium_risk_suppliers": sum(
                1
                for supplier in suppliers
                if supplier.get(
                    "risk_level"
                ) == "MEDIUM_RISK"
            ),
            "low_risk_suppliers": sum(
                1
                for supplier in suppliers
                if supplier.get(
                    "risk_level"
                ) == "LOW_RISK"
            ),
            "current_anomaly_suppliers": sum(
                1
                for supplier in suppliers
                if supplier.get(
                    "current_anomaly_status"
                ) == "CURRENT_ANOMALY"
            ),
            "critical_future_warnings": sum(
                1
                for supplier in suppliers
                if supplier.get(
                    "early_warning_status"
                ) == "CRITICAL_WARNING"
            ),
            "warning_suppliers": sum(
                1
                for supplier in suppliers
                if supplier.get(
                    "early_warning_status"
                )
                in {
                    "WARNING",
                    "CRITICAL_WARNING",
                }
            ),
            "high_severity_suppliers": sum(
                1
                for supplier in suppliers
                if supplier.get(
                    "future_unavailability_severity"
                ) == "HIGH"
            ),
            "medium_severity_suppliers": sum(
                1
                for supplier in suppliers
                if supplier.get(
                    "future_unavailability_severity"
                ) == "MEDIUM"
            ),
            "low_severity_suppliers": sum(
                1
                for supplier in suppliers
                if supplier.get(
                    "future_unavailability_severity"
                ) == "LOW"
            ),
            "average_risk_score": (
                average_risk_score
            ),
            "average_future_instability_probability": (
                cls._average_probability(
                    suppliers,
                    "future_probability_7d",
                )
            ),
            "average_future_probability_24h": (
                cls._average_probability(
                    suppliers,
                    "future_probability_24h",
                )
            ),
            "average_future_probability_3d": (
                cls._average_probability(
                    suppliers,
                    "future_probability_3d",
                )
            ),
            "average_future_probability_7d": (
                cls._average_probability(
                    suppliers,
                    "future_probability_7d",
                )
            ),
        }

    @classmethod
    def get_predictions(
        cls,
        period: str = "all",
    ):
        cache_key = (
            f"{cls.CACHE_PREFIX}:{period}"
        )

        cached = CacheAdapter.get(
            cache_key
        )

        if cached:
            cache_hits_total.inc()

            logger.info(
                "Returning supplier predictions "
                "from Redis cache."
            )

            return cached

        cache_misses_total.inc()

        logger.info(
            "Cache miss. Waiting for Redis "
            "pipeline lock."
        )

        pipeline_lock = get_redis_lock(
            lock_name=(
                "supplier_prediction_pipeline_lock"
            ),
            timeout=300,
            blocking_timeout=30,
        )

        if pipeline_lock is None:
            logger.warning(
                "Redis lock unavailable. "
                "Running pipeline without "
                "distributed lock."
            )

            return cls._run_pipeline_and_cache(
                period=period,
                cache_key=cache_key,
            )

        with pipeline_lock:
            cached = CacheAdapter.get(
                cache_key
            )

            if cached:
                cache_hits_total.inc()

                logger.info(
                    "Cache filled by another request. "
                    "Returning cached data."
                )

                return cached

            return cls._run_pipeline_and_cache(
                period=period,
                cache_key=cache_key,
            )

    @classmethod
    def _run_pipeline_and_cache(
        cls,
        period: str,
        cache_key: str,
    ):
        logger.info(
            "Running supplier prediction "
            "pipeline in memory."
        )

        days = cls.PERIOD_TO_DAYS.get(
            period,
            30,
        )

        start_time = time.time()

        prediction_runs_total.inc()

        try:
            prediction_df = (
                run_prediction_pipeline(
                    days=days
                )
            )

            pipeline_duration_seconds.observe(
                time.time() - start_time
            )

        except Exception as error:
            pipeline_duration_seconds.observe(
                time.time() - start_time
            )

            logger.exception(
                "Pipeline failed. Trying stale "
                "cached data. Error: %s",
                error,
            )

            stale_cached = CacheAdapter.get(
                cache_key
            )

            if stale_cached:
                stale_cached["warning"] = (
                    "Pipeline failed. Serving "
                    "cached prediction data."
                )

                return stale_cached

            raise

        model_validation = (
            cls._get_model_validation_info()
        )

        if (
            prediction_df is None
            or prediction_df.empty
        ):
            response = {
                "period": period,
                "latest_date": None,
                "model_validation": (
                    model_validation
                ),
                "summary": cls._build_summary(
                    []
                ),
                "suppliers": [],
            }

            CacheAdapter.set(
                cache_key,
                response,
                expiry_seconds=300,
            )

            return response

        prediction_df = (
            prediction_df.sort_values(
                by="risk_score",
                ascending=False,
            )
        )

        suppliers = [
            cls._clean_supplier_record(
                row
            )
            for row
            in prediction_df.to_dict(
                orient="records"
            )
        ]

        for supplier in suppliers:
            if (
                supplier.get(
                    "early_warning_status"
                )
                == "CRITICAL_WARNING"
            ):
                send_webhook(
                    {
                        "supplier_code": (
                            supplier[
                                "supplier_code"
                            ]
                        ),
                        "supplier_name": (
                            supplier[
                                "supplier_name"
                            ]
                        ),
                        "risk_level": (
                            supplier[
                                "risk_level"
                            ]
                        ),
                        "future_probability_24h": (
                            supplier[
                                "future_probability_24h"
                            ]
                        ),
                        "future_probability_3d": (
                            supplier[
                                "future_probability_3d"
                            ]
                        ),
                        "future_probability_7d": (
                            supplier[
                                "future_probability_7d"
                            ]
                        ),
                        "future_unavailability_severity": (
                            supplier[
                                "future_unavailability_severity"
                            ]
                        ),
                        "future_risk_window": (
                            supplier[
                                "future_risk_window"
                            ]
                        ),
                    }
                )

        latest_date = (
            datetime.now().isoformat(
                timespec="seconds"
            )
        )

        response = {
            "period": period,
            "latest_date": latest_date,
            "model_validation": (
                model_validation
            ),
            "summary": cls._build_summary(
                suppliers
            ),
            "suppliers": suppliers,
        }

        CacheAdapter.set(
            cache_key,
            response,
            expiry_seconds=60,
        )

        logger.info(
            "Supplier predictions generated "
            "and cached successfully."
        )

        return response

    @classmethod
    def clear_cache(
        cls,
    ):
        CacheAdapter.clear_supplier_predictions()