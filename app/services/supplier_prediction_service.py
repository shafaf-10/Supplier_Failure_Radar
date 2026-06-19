# from sqlalchemy import text

# from app.infra.database import engine
# from app.services.cache_adapter import CacheAdapter


# class SupplierPredictionService:
#     CACHE_PREFIX = "supplier_predictions"

#     PERIOD_INTERVALS = {
#         "24h": "1 DAY",
#         "7d": "7 DAY",
#         "30d": "30 DAY",
#         "1y": "365 DAY",
#     }

#     @classmethod
#     def get_predictions(cls, period: str = "all"):
#         cache_key = f"{cls.CACHE_PREFIX}:{period}"

#         cached = CacheAdapter.get(cache_key)
#         if cached:
#             return cached

#         latest_date_query = text("""
#             SELECT MAX(created_at) AS latest_date
#             FROM supplier_predictions
#         """)

#         with engine.connect() as conn:
#             latest_date = conn.execute(latest_date_query).scalar()

#         where_clause = "1=1"
#         params = {}

#         if period in cls.PERIOD_INTERVALS and latest_date is not None:
#             interval_value = cls.PERIOD_INTERVALS[period]

#             where_clause = (
#                 f"created_at >= DATE_SUB(:latest_date, INTERVAL {interval_value})"
#             )

#             params["latest_date"] = latest_date

#         query = text(f"""
#             SELECT
#                 supplier_code,
#                 supplier_name,
#                 total_bookings,

#                 risk_score,
#                 risk_level,
#                 predicted_risk,
#                 prediction_probability,

#                 anomaly_status,
#                 anomaly_score,

#                 recommendation,

#                 future_instability_probability,
#                 future_risk_window,
#                 early_warning_status,
#                 lead_signal,
#                 prediction_confidence,
#                 future_recommendation,

#                 failure_rate,
#                 pending_rate,
#                 cancellation_rate,
#                 process_error_rate,
#                 refund_rate,
#                 credit_rejection_rate,
#                 search_failure_rate,
#                 wallet_risk_rate,

#                 created_at

#             FROM supplier_predictions

#             WHERE {where_clause}

#             ORDER BY risk_score DESC
#         """)

#         with engine.connect() as conn:
#             rows = conn.execute(query, params).mappings().all()

#         suppliers = [dict(row) for row in rows]
#         total = len(suppliers)

#         response = {
#             "period": period,
#             "latest_date": str(latest_date) if latest_date else None,
#             "summary": {
#                 "total_suppliers": total,
#                 "high_risk_suppliers": sum(
#                     1 for s in suppliers
#                     if s["risk_level"] == "HIGH_RISK"
#                 ),
#                 "medium_risk_suppliers": sum(
#                     1 for s in suppliers
#                     if s["risk_level"] == "MEDIUM_RISK"
#                 ),
#                 "low_risk_suppliers": sum(
#                     1 for s in suppliers
#                     if s["risk_level"] == "LOW_RISK"
#                 ),
#                 "anomaly_suppliers": sum(
#                     1 for s in suppliers
#                     if s["anomaly_status"] == "ANOMALY"
#                 ),
#                 "critical_future_warnings": sum(
#                     1 for s in suppliers
#                     if s["early_warning_status"] == "CRITICAL_WARNING"
#                 ),
#                 "warning_suppliers": sum(
#                     1 for s in suppliers
#                     if s["early_warning_status"] in [
#                         "WARNING",
#                         "CRITICAL_WARNING",
#                     ]
#                 ),
#                 "average_risk_score": round(
#                     sum(float(s["risk_score"] or 0) for s in suppliers) / total,
#                     2,
#                 ) if total else 0,
#                 "average_future_instability_probability": round(
#                     (
#                         sum(
#                             float(
#                                 s["future_instability_probability"] or 0
#                             )
#                             for s in suppliers
#                         )
#                         / total
#                     ) * 100,
#                     2,
#                 ) if total else 0,
#             },
#             "suppliers": suppliers,
#         }

#         CacheAdapter.set(
#             cache_key,
#             response,
#             expiry_seconds=60,
#         )

#         return response

#     @classmethod
#     def clear_cache(cls):
#         CacheAdapter.clear_supplier_predictions()


from datetime import datetime

import pandas as pd

from app.ml.pipeline import run_prediction_pipeline
from app.services.cache_adapter import CacheAdapter
from app.observability.logger import setup_logger


logger = setup_logger(__name__)


class SupplierPredictionService:
    CACHE_PREFIX = "supplier_predictions"

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
            "anomaly_score": round(
                cls._to_float(row.get("anomaly_score")),
                6,
            ),

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
                1 for s in suppliers
                if s["risk_level"] == "HIGH_RISK"
            ),
            "medium_risk_suppliers": sum(
                1 for s in suppliers
                if s["risk_level"] == "MEDIUM_RISK"
            ),
            "low_risk_suppliers": sum(
                1 for s in suppliers
                if s["risk_level"] == "LOW_RISK"
            ),
            "anomaly_suppliers": sum(
                1 for s in suppliers
                if s["anomaly_status"] == "ANOMALY"
            ),
            "critical_future_warnings": sum(
                1 for s in suppliers
                if s["early_warning_status"] == "CRITICAL_WARNING"
            ),
            "warning_suppliers": sum(
                1 for s in suppliers
                if s["early_warning_status"] in [
                    "WARNING",
                    "CRITICAL_WARNING",
                ]
            ),
            "average_risk_score": round(
                sum(float(s["risk_score"] or 0) for s in suppliers) / total,
                2,
            ) if total else 0,
            "average_future_instability_probability": round(
                (
                    sum(
                        float(s["future_instability_probability"] or 0)
                        for s in suppliers
                    )
                    / total
                ) * 100,
                2,
            ) if total else 0,
        }

    @classmethod
    def get_predictions(cls, period: str = "all"):
        cache_key = f"{cls.CACHE_PREFIX}:{period}"

        cached = CacheAdapter.get(cache_key)
        if cached:
            logger.info("Returning supplier predictions from Redis cache.")
            return cached

        logger.info("Cache miss. Running supplier prediction pipeline in memory.")

        prediction_df = run_prediction_pipeline()

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
                expiry_seconds=60,
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