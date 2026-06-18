from sqlalchemy import text

from app.infra.database import engine
from app.services.cache_adapter import CacheAdapter


class SupplierPredictionService:
    CACHE_PREFIX = "supplier_predictions"

    PERIOD_INTERVALS = {
        "24h": "1 DAY",
        "7d": "7 DAY",
        "30d": "30 DAY",
        "1y": "365 DAY",
    }

    @classmethod
    def get_predictions(cls, period: str = "all"):
        cache_key = f"{cls.CACHE_PREFIX}:{period}"

        cached = CacheAdapter.get(cache_key)
        if cached:
            return cached

        latest_date_query = text("""
            SELECT MAX(created_at) AS latest_date
            FROM supplier_predictions
        """)

        with engine.connect() as conn:
            latest_date = conn.execute(latest_date_query).scalar()

        where_clause = "1=1"
        params = {}

        if period in cls.PERIOD_INTERVALS and latest_date is not None:
            interval_value = cls.PERIOD_INTERVALS[period]

            where_clause = (
                f"created_at >= DATE_SUB(:latest_date, INTERVAL {interval_value})"
            )

            params["latest_date"] = latest_date

        query = text(f"""
            SELECT
                supplier_code,
                supplier_name,
                total_bookings,

                risk_score,
                risk_level,
                predicted_risk,
                prediction_probability,

                anomaly_status,
                anomaly_score,

                recommendation,

                future_instability_probability,
                future_risk_window,
                early_warning_status,
                lead_signal,
                prediction_confidence,
                future_recommendation,

                failure_rate,
                pending_rate,
                cancellation_rate,
                process_error_rate,
                refund_rate,
                credit_rejection_rate,
                search_failure_rate,
                wallet_risk_rate,

                created_at

            FROM supplier_predictions

            WHERE {where_clause}

            ORDER BY risk_score DESC
        """)

        with engine.connect() as conn:
            rows = conn.execute(query, params).mappings().all()

        suppliers = [dict(row) for row in rows]
        total = len(suppliers)

        response = {
            "period": period,
            "latest_date": str(latest_date) if latest_date else None,
            "summary": {
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
                            float(
                                s["future_instability_probability"] or 0
                            )
                            for s in suppliers
                        )
                        / total
                    ) * 100,
                    2,
                ) if total else 0,
            },
            "suppliers": suppliers,
        }

        CacheAdapter.set(
            cache_key,
            response,
            expiry_seconds=60,
        )

        return response

    @classmethod
    def clear_cache(cls):
        CacheAdapter.clear_supplier_predictions()