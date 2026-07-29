from app.ml.prediction_recommendations import get_recommendation


def test_recommendation_current_anomaly_overrides_risk_level():
    result = get_recommendation(risk_level="LOW_RISK", anomaly_status="CURRENT_ANOMALY")
    assert "Immediate investigation required" in result


def test_recommendation_high_risk():
    result = get_recommendation(risk_level="HIGH_RISK", anomaly_status="CURRENT_NORMAL")
    assert "high risk" in result


def test_recommendation_medium_risk():
    result = get_recommendation(risk_level="MEDIUM_RISK", anomaly_status="CURRENT_NORMAL")
    assert "needs monitoring" in result


def test_recommendation_low_risk_default():
    result = get_recommendation(risk_level="LOW_RISK", anomaly_status="CURRENT_NORMAL")
    assert "stable" in result