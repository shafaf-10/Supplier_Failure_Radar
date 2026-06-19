from app.ml.feature_builder import build_supplier_features
from app.ml.anomaly_detector import detect_anomalies
from app.observability.logger import setup_logger


logger = setup_logger(__name__)


def run_prediction_pipeline():
    """
    Production pipeline:
    1. Build latest supplier features from MySQL in memory
    2. Predict risk + detect anomalies in memory
    3. Return prediction dataframe

    Note:
    No supplier_features table.
    No supplier_predictions table.
    Predictions are returned directly to the API/service layer.
    """

    logger.info("Starting supplier prediction pipeline...")

    features_df = build_supplier_features()
    prediction_df = detect_anomalies(features_df)

    logger.info("Supplier prediction pipeline completed successfully.")

    return prediction_df


if __name__ == "__main__":
    result_df = run_prediction_pipeline()
    print(result_df)