import pandas as pd

from app.services.supplier_prediction_service import SupplierPredictionService


class DummyLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_clean_supplier_record_handles_missing_and_nan_values():
    row = {
        "supplier_code": "sup_001",
        "supplier_name": "Test Supplier",
        "total_bookings": None,
        "risk_score": float("nan"),
        "prediction_probability": None,
        "anomaly_score": None,
        "future_instability_probability": None,
    }

    result = SupplierPredictionService._clean_supplier_record(row)

    assert result["supplier_code"] == "sup_001"
    assert result["supplier_name"] == "Test Supplier"
    assert result["total_bookings"] == 0
    assert result["risk_score"] == 0.0
    assert result["prediction_probability"] == 0.0
    assert result["anomaly_score"] == 0.0
    assert result["future_instability_probability"] == 0.0


def test_build_summary_counts_supplier_statuses_correctly():
    suppliers = [
        {
            "risk_level": "HIGH_RISK",
            "anomaly_status": "ANOMALY",
            "early_warning_status": "CRITICAL_WARNING",
            "risk_score": 80,
            "future_instability_probability": 0.9,
        },
        {
            "risk_level": "MEDIUM_RISK",
            "anomaly_status": "NORMAL",
            "early_warning_status": "WARNING",
            "risk_score": 50,
            "future_instability_probability": 0.5,
        },
        {
            "risk_level": "LOW_RISK",
            "anomaly_status": "NORMAL",
            "early_warning_status": "STABLE",
            "risk_score": 20,
            "future_instability_probability": 0.1,
        },
    ]

    result = SupplierPredictionService._build_summary(suppliers)

    assert result["total_suppliers"] == 3
    assert result["high_risk_suppliers"] == 1
    assert result["medium_risk_suppliers"] == 1
    assert result["low_risk_suppliers"] == 1
    assert result["anomaly_suppliers"] == 1
    assert result["critical_future_warnings"] == 1
    assert result["warning_suppliers"] == 2
    assert result["average_risk_score"] == 50.0
    assert result["average_future_instability_probability"] == 50.0


def test_get_predictions_returns_cached_data_without_pipeline(monkeypatch):
    cached_response = {
        "period": "7d",
        "latest_date": "2026-07-07T10:00:00",
        "summary": {},
        "suppliers": [],
    }

    monkeypatch.setattr(
        "app.services.supplier_prediction_service.CacheAdapter.get",
        lambda cache_key: cached_response,
    )

    def fail_if_pipeline_runs(days=None):
        raise AssertionError("Pipeline should not run when cache exists")

    monkeypatch.setattr(
        "app.services.supplier_prediction_service.run_prediction_pipeline",
        fail_if_pipeline_runs,
    )

    result = SupplierPredictionService.get_predictions(period="7d")

    assert result == cached_response


def test_get_predictions_runs_pipeline_without_live_db(monkeypatch):
    monkeypatch.setattr(
        "app.services.supplier_prediction_service.CacheAdapter.get",
        lambda cache_key: None,
    )

    saved_cache = {}

    def fake_cache_set(cache_key, value, expiry_seconds):
        saved_cache["cache_key"] = cache_key
        saved_cache["value"] = value
        saved_cache["expiry_seconds"] = expiry_seconds

    monkeypatch.setattr(
        "app.services.supplier_prediction_service.CacheAdapter.set",
        fake_cache_set,
    )

    monkeypatch.setattr(
        "app.services.supplier_prediction_service.get_redis_lock",
        lambda lock_name, timeout=300, blocking_timeout=30: DummyLock(),
    )

    monkeypatch.setattr(
        "app.services.supplier_prediction_service.send_webhook",
        lambda payload: None,
    )

    prediction_df = pd.DataFrame(
        [
            {
                "supplier_code": "sup_001",
                "supplier_name": "Test Supplier",
                "total_bookings": 100,
                "risk_score": 85,
                "risk_level": "HIGH_RISK",
                "predicted_risk": "HIGH_RISK",
                "prediction_probability": 0.91,
                "anomaly_status": "ANOMALY",
                "anomaly_score": -0.12,
                "recommendation": "Monitor supplier",
                "future_instability_probability": 0.88,
                "future_risk_window": "NEXT_7_DAYS",
                "early_warning_status": "CRITICAL_WARNING",
                "lead_signal": "Booking Failure",
                "prediction_confidence": "HIGH",
                "future_recommendation": "Prepare backup supplier",
                "failure_rate": 0.3,
                "pending_rate": 0.2,
                "cancellation_rate": 0.1,
                "process_error_rate": 0.2,
                "refund_rate": 0.1,
                "credit_rejection_rate": 0.1,
                "search_failure_rate": 0.2,
                "wallet_risk_rate": 0.1,
            }
        ]
    )

    monkeypatch.setattr(
        "app.services.supplier_prediction_service.run_prediction_pipeline",
        lambda days=None: prediction_df,
    )

    result = SupplierPredictionService.get_predictions(period="7d")

    assert result["period"] == "7d"
    assert result["summary"]["total_suppliers"] == 1
    assert result["summary"]["high_risk_suppliers"] == 1
    assert result["suppliers"][0]["supplier_code"] == "sup_001"
    assert saved_cache["cache_key"] == "supplier_predictions:7d"
    assert saved_cache["expiry_seconds"] == 60