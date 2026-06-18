from app.ml.feature_builder import build_supplier_features
from app.ml.anomaly_detector import detect_anomalies


def run_prediction_pipeline():
    """
    Production pipeline:
    1. Build latest supplier features from MySQL in memory
    2. Predict risk + detect anomalies
    3. Update only supplier_predictions table

    Note:
    supplier_features table is not used.
    Features are generated in code and passed directly to the prediction step.
    """

    print("Starting supplier prediction pipeline...")

    features_df = build_supplier_features()
    detect_anomalies(features_df)

    print("Supplier prediction pipeline completed successfully.")

    return {
        "status": "success",
        "message": "Supplier prediction pipeline completed successfully",
    }


if __name__ == "__main__":
    run_prediction_pipeline()