from app.ml.feature_builder import build_supplier_features
from app.ml.anomaly_detector import detect_anomalies


def run_prediction_pipeline():
    """
    Production pipeline:
    1. Build latest supplier features from MySQL
    2. Predict risk + detect anomalies
    3. Update supplier_features and supplier_predictions tables
    """

    print("Starting supplier prediction pipeline...")

    build_supplier_features()
    detect_anomalies()

    print("Supplier prediction pipeline completed successfully.")

    return {
        "status": "success",
        "message": "Supplier prediction pipeline completed successfully",
    }


if __name__ == "__main__":
    run_prediction_pipeline()