# from fastapi.testclient import TestClient

# from app.infra.settings import settings
# from app.main import app

# client = TestClient(app)

# FAKE_PREDICTIONS = {
#     "generated_at": "2026-01-01T00:00:00",
#     "summary": {"total_suppliers": 2, "high_risk_count": 1},
#     "suppliers": [
#         {"supplier_code": "SUP-A", "risk_level": "HIGH_RISK", "risk_score": 40.0},
#         {"supplier_code": "SUP-B", "risk_level": "LOW_RISK", "risk_score": 5.0},
#     ],
# }


# def test_missing_api_key_is_rejected():
#     response = client.get("/supplier-predictions")
#     assert response.status_code == 422


# def test_wrong_api_key_is_rejected():
#     response = client.get(
#         "/supplier-predictions",
#         headers={"X-API-Key": "wrong-key"},
#     )
#     assert response.status_code == 401


# def test_invalid_period_returns_400():
#     response = client.get(
#         "/supplier-predictions",
#         params={"period": "not-a-real-period"},
#         headers={"X-API-Key": settings.API_KEY},
#     )
#     assert response.status_code == 400
#     assert "Invalid period" in response.json()["detail"]


# def test_valid_request_returns_expected_shape(monkeypatch):
#     monkeypatch.setattr(
#         "app.api.v1.endpoints.supplier_predictions.SupplierPredictionService.get_predictions",
#         lambda period: FAKE_PREDICTIONS,
#     )

#     response = client.get(
#         "/supplier-predictions",
#         params={"period": "all"},
#         headers={"X-API-Key": settings.API_KEY},
#     )

#     assert response.status_code == 200
#     body = response.json()

#     assert "suppliers" in body
#     assert "summary" in body
#     assert "limit" in body
#     assert "offset" in body
#     assert isinstance(body["suppliers"], list)
#     assert body["limit"] == 100
#     assert body["offset"] == 0

#     for supplier in body["suppliers"]:
#         assert "supplier_code" in supplier
#         assert "risk_level" in supplier
#         assert "risk_score" in supplier
#         assert isinstance(supplier["risk_score"], (int, float))


# def test_limit_and_offset_are_applied(monkeypatch):
#     monkeypatch.setattr(
#         "app.api.v1.endpoints.supplier_predictions.SupplierPredictionService.get_predictions",
#         lambda period: FAKE_PREDICTIONS,
#     )

#     response = client.get(
#         "/supplier-predictions",
#         params={"period": "all", "limit": 1, "offset": 1},
#         headers={"X-API-Key": settings.API_KEY},
#     )

#     assert response.status_code == 200
#     body = response.json()
#     assert len(body["suppliers"]) == 1
#     assert body["suppliers"][0]["supplier_code"] == "SUP-B"


# def test_refresh_model_returns_expected_shape(monkeypatch):
#     monkeypatch.setattr(
#         "app.api.v1.endpoints.supplier_predictions.SupplierPredictionService.clear_cache",
#         lambda: None,
#     )
#     monkeypatch.setattr(
#         "app.api.v1.endpoints.supplier_predictions.SupplierPredictionService.get_predictions",
#         lambda period: FAKE_PREDICTIONS,
#     )

#     response = client.post(
#         "/refresh-model",
#         headers={"X-API-Key": settings.API_KEY},
#     )

#     assert response.status_code == 200
#     body = response.json()

#     assert body["status"] == "success"
#     assert "summary" in body
#     assert "total_suppliers" in body
#     assert isinstance(body["total_suppliers"], int)


from fastapi.testclient import TestClient

from app.infra.settings import settings
from app.main import app

client = TestClient(app)


FAKE_PREDICTIONS = {
    "period": "all",
    "latest_date": "2026-01-01T00:00:00",
    "model_validation": {
        "training_data_provenance": "SYNTHETIC",
        "production_validated": False,
        "prediction_status": "WARNING",
        "prediction_notice": (
            "Prediction generated using synthetic training data."
        ),
    },
    "platform_health": {
        "platform_incident": False,
        "incident_windows": [],
        "internal_failure_events": 0,
        "internal_failure_rate": 0.0,
        "drift_status": None,
        "drifted_features": [],
    },
    "summary": {
        "total_suppliers": 2,
        "high_risk_suppliers": 1,
        "medium_risk_suppliers": 0,
        "low_risk_suppliers": 1,
        "current_anomaly_suppliers": 0,
        "critical_future_warnings": 0,
        "warning_suppliers": 0,
        "high_severity_suppliers": 0,
        "medium_severity_suppliers": 0,
        "low_severity_suppliers": 2,
        "average_risk_score": 22.5,
        "average_future_instability_probability": 0.10,
        "average_future_probability_24h": 0.05,
        "average_future_probability_3d": 0.08,
        "average_future_probability_7d": 0.10,
    },
    "suppliers": [
        {
            "supplier_code": "SUP-A",
            "supplier_name": "Supplier A",
            "total_bookings": 100,
            "risk_score": 40.0,
            "risk_level": "HIGH_RISK",
            "predicted_risk": "HIGH_RISK",
            "prediction_probability": 0.90,
            "current_anomaly_status": "CURRENT_NORMAL",
            "current_anomaly_score": 0.10,
            "recommendation": "Monitor supplier closely.",
            "future_probability_24h": 0.10,
            "future_probability_3d": 0.15,
            "future_probability_7d": 0.20,
            "future_unavailability_severity": "LOW",
            "future_instability_probability": 0.20,
            "future_risk_window": "NEXT_7_DAYS",
            "early_warning_status": "WATCHLIST",
            "lead_signal": "Operational Risk",
            "prediction_confidence": "MEDIUM",
            "future_recommendation": "Monitor closely.",
            "failure_rate": 0.05,
            "pending_rate": 0.02,
            "cancellation_rate": 0.01,
            "process_error_rate": 0.03,
            "refund_rate": 0.01,
            "credit_rejection_rate": 0.01,
            "search_failure_rate": 0.02,
            "wallet_risk_rate": 0.01,
            "internal_failure_count": 0,
            "internal_failure_rate": 0.0,
            "created_at": "2026-01-01T00:00:00",
        },
        {
            "supplier_code": "SUP-B",
            "supplier_name": "Supplier B",
            "total_bookings": 100,
            "risk_score": 5.0,
            "risk_level": "LOW_RISK",
            "predicted_risk": "LOW_RISK",
            "prediction_probability": 0.95,
            "current_anomaly_status": "CURRENT_NORMAL",
            "current_anomaly_score": 0.20,
            "recommendation": "Supplier operating normally.",
            "future_probability_24h": 0.01,
            "future_probability_3d": 0.02,
            "future_probability_7d": 0.03,
            "future_unavailability_severity": "LOW",
            "future_instability_probability": 0.03,
            "future_risk_window": "NEXT_7_DAYS",
            "early_warning_status": "STABLE",
            "lead_signal": "Operational Risk",
            "prediction_confidence": "HIGH",
            "future_recommendation": "ML model predicts low instability probability.",
            "failure_rate": 0.01,
            "pending_rate": 0.01,
            "cancellation_rate": 0.01,
            "process_error_rate": 0.01,
            "refund_rate": 0.01,
            "credit_rejection_rate": 0.01,
            "search_failure_rate": 0.01,
            "wallet_risk_rate": 0.01,
            "internal_failure_count": 0,
            "internal_failure_rate": 0.0,
            "created_at": "2026-01-01T00:00:00",
        },
    ],
}


def test_missing_api_key_is_rejected():
    response = client.get("/supplier-predictions")

    assert response.status_code == 422


def test_wrong_api_key_is_rejected():
    response = client.get(
        "/supplier-predictions",
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 401


def test_invalid_period_returns_400():
    response = client.get(
        "/supplier-predictions",
        params={"period": "not-a-real-period"},
        headers={"X-API-Key": settings.API_KEY},
    )

    assert response.status_code == 400
    assert "Invalid period" in response.json()["detail"]


def test_valid_request_returns_expected_shape(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.supplier_predictions."
        "SupplierPredictionService.get_predictions",
        lambda period: FAKE_PREDICTIONS,
    )

    response = client.get(
        "/supplier-predictions",
        params={"period": "all"},
        headers={"X-API-Key": settings.API_KEY},
    )

    assert response.status_code == 200

    body = response.json()

    assert "suppliers" in body
    assert "summary" in body
    assert "limit" in body
    assert "offset" in body

    assert isinstance(body["suppliers"], list)
    assert body["limit"] == 100
    assert body["offset"] == 0

    for supplier in body["suppliers"]:
        assert "supplier_code" in supplier
        assert "risk_level" in supplier
        assert "risk_score" in supplier
        assert isinstance(
            supplier["risk_score"],
            (int, float),
        )


def test_limit_and_offset_are_applied(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.supplier_predictions."
        "SupplierPredictionService.get_predictions",
        lambda period: FAKE_PREDICTIONS,
    )

    response = client.get(
        "/supplier-predictions",
        params={
            "period": "all",
            "limit": 1,
            "offset": 1,
        },
        headers={"X-API-Key": settings.API_KEY},
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body["suppliers"]) == 1
    assert body["suppliers"][0]["supplier_code"] == "SUP-B"


def test_refresh_model_returns_expected_shape(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.supplier_predictions."
        "SupplierPredictionService.clear_cache",
        lambda: None,
    )

    monkeypatch.setattr(
        "app.api.v1.endpoints.supplier_predictions."
        "SupplierPredictionService.get_predictions",
        lambda period: FAKE_PREDICTIONS,
    )

    response = client.post(
        "/refresh-model",
        headers={"X-API-Key": settings.API_KEY},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"
    assert "summary" in body
    assert "total_suppliers" in body
    assert isinstance(
        body["total_suppliers"],
        int,
    )

