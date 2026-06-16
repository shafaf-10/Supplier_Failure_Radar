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
            SELECT MAX(COALESCE(p.created_at, f.created_at)) AS latest_date
            FROM supplier_features AS f
            LEFT JOIN supplier_predictions AS p
                ON f.supplier_code = p.supplier_code
        """)

        with engine.connect() as conn:
            latest_date = conn.execute(latest_date_query).scalar()

        where_clause = "1=1"

        if period in cls.PERIOD_INTERVALS and latest_date is not None:
            interval_value = cls.PERIOD_INTERVALS[period]

            where_clause = (
                f"COALESCE(p.created_at, f.created_at) "
                f">= DATE_SUB(:latest_date, INTERVAL {interval_value})"
            )

        query = text(f"""
            SELECT
                f.supplier_code,
                f.supplier_name,
                f.total_bookings,
                f.risk_score,
                f.risk_level,

                COALESCE(p.predicted_risk, f.risk_level) AS predicted_risk,
                COALESCE(p.prediction_probability, 0) AS prediction_probability,
                COALESCE(p.anomaly_status, 'NORMAL') AS anomaly_status,
                COALESCE(p.anomaly_score, 0) AS anomaly_score,

                COALESCE(
                    p.recommendation,
                    'Supplier is stable. Continue normal monitoring.'
                ) AS recommendation,

                COALESCE(
                    p.future_instability_probability,
                    0
                ) AS future_instability_probability,

                COALESCE(
                    p.future_risk_window,
                    'NEXT_7_DAYS'
                ) AS future_risk_window,

                COALESCE(
                    p.early_warning_status,
                    'STABLE'
                ) AS early_warning_status,

                COALESCE(
                    p.lead_signal,
                    'Normal Operations'
                ) AS lead_signal,

                COALESCE(
                    p.prediction_confidence,
                    'LOW'
                ) AS prediction_confidence,

                COALESCE(
                    p.future_recommendation,
                    p.recommendation
                ) AS future_recommendation,

                f.failure_rate,
                f.pending_rate,
                f.cancellation_rate,
                f.process_error_rate,
                f.refund_rate,
                f.credit_rejection_rate,
                f.search_failure_rate,
                f.wallet_risk_rate,
                COALESCE(p.created_at, f.created_at) AS created_at

            FROM supplier_features AS f
            LEFT JOIN supplier_predictions AS p
                ON f.supplier_code = p.supplier_code

            WHERE {where_clause}

            ORDER BY f.risk_score DESC
        """)

        params = {}

        if period in cls.PERIOD_INTERVALS and latest_date is not None:
            params["latest_date"] = latest_date

        with engine.connect() as conn:
            rows = conn.execute(
                query,
                params,
            ).mappings().all()

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