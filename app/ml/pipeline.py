import pandas as pd

from app.ml.anomaly_detector import detect_anomalies
from app.ml.drift_detector import detect_feature_drift
from app.ml.feature_builder import build_supplier_features
from app.observability.logger import setup_logger

logger = setup_logger(__name__)


DRIFT_FEATURES = [
    "b_failure_rate",
    "b_pending_rate",
    "bp_error_rate",
    "bp_high_retry_rate",
    "booking_not_issued_rate",
    "rr_refund_risk_score_100",
    "cr_credit_risk_score_100",
    "supplier_session_risk_score_100",
    "wt_wallet_risk_score_100",
    "risk_score",
]


def run_prediction_pipeline(days: int | None = 30) -> pd.DataFrame:
    logger.info("Starting supplier prediction pipeline...")

    features_df = build_supplier_features(days=days)

    drift_result = detect_feature_drift(
        features_df,
        DRIFT_FEATURES,
    )
    logger.info("Feature drift check result: %s", drift_result)

    prediction_df = detect_anomalies(features_df)

    logger.info("Supplier prediction pipeline completed successfully.")

    return prediction_df


