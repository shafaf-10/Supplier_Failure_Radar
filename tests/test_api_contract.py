from fastapi.testclient import TestClient

from app.infra.settings import settings
from app.main import app

client = TestClient(app)

FAKE_PREDICTIONS = {
    "generated_at": "2026-01-01T00:00:00",
    "summary": {"total_suppliers": 2, "high_risk_count": 1},
    "suppliers": [
        {"supplier_code": "SUP-A", "risk_level": "HIGH_RISK", "risk_score": 40.0},
        {"supplier_code": "SUP-B", "risk_level": "LOW_RISK", "risk_score": 5.0},
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
        "app.api.v1.endpoints.supplier_predictions.SupplierPredictionService.get_predictions",
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
        assert isinstance(supplier["risk_score"], (int, float))


def test_limit_and_offset_are_applied(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.supplier_predictions.SupplierPredictionService.get_predictions",
        lambda period: FAKE_PREDICTIONS,
    )

    response = client.get(
        "/supplier-predictions",
        params={"period": "all", "limit": 1, "offset": 1},
        headers={"X-API-Key": settings.API_KEY},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["suppliers"]) == 1
    assert body["suppliers"][0]["supplier_code"] == "SUP-B"


def test_refresh_model_returns_expected_shape(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.supplier_predictions.SupplierPredictionService.clear_cache",
        lambda: None,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supplier_predictions.SupplierPredictionService.get_predictions",
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
    assert isinstance(body["total_suppliers"], int)