import json
from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split


ROOT_DIR = Path(__file__).resolve().parents[2]

FEATURE_FILE = ROOT_DIR / "outputs" / "supplier_features.csv"

MODEL_DIR = ROOT_DIR / "app" / "ml" / "models"
RISK_MODEL_FILE = MODEL_DIR / "risk_model.pkl"
FUTURE_MODEL_FILE = MODEL_DIR / "future_failure_model.pkl"

METRICS_FILE = ROOT_DIR / "outputs" / "model_metrics.json"


FEATURE_COLUMNS = [
    "b_failure_rate",
    "b_pending_rate",
    "b_cancellation_rate",
    "b_deadline_miss_rate",
    "b_estimated_failure_loss",
    "bp_error_rate",
    "bp_stuck_rate",
    "bp_high_retry_rate",
    "bp_attempts_mean",
    "booking_not_issued_rate",
    "supplier_pnr_missing_rate",
    "ticket_number_missing_rate",
    "supplier_ticketing_risk_score_100",
    "ss_failure_rate",
    "ss_partial_rate",
    "ss_timeout_rate",
    "ss_completion_gap_rate",
    "supplier_session_risk_score_100",
    "rr_pending_rate",
    "rr_rejected_rate",
    "rr_avg_refund_delay_days",
    "rr_refund_risk_score_100",
    "cr_rejection_rate",
    "cr_overdue_rate",
    "cr_pending_rate",
    "cr_credit_risk_score_100",
    "wt_failed_payment_rate",
    "wt_hold_rate",
    "wt_negative_balance_rate",
    "wt_wallet_risk_score_100",
]


LABEL_MAP = {
    "LOW_RISK": 0,
    "MEDIUM_RISK": 1,
    "HIGH_RISK": 2,
}

REVERSE_LABEL_MAP = {
    0: "LOW_RISK",
    1: "MEDIUM_RISK",
    2: "HIGH_RISK",
}


def validate_features(df):
    missing_cols = [
        col for col in FEATURE_COLUMNS
        if col not in df.columns
    ]

    if missing_cols:
        raise ValueError(
            f"Missing feature columns: {missing_cols}. "
            "Run feature_builder.py again."
        )

    if "risk_level" not in df.columns:
        raise ValueError("risk_level column missing.")

    return True


def create_future_failure_target(df):
    future_failure = (
        (df["risk_score"] >= 30)
        | (
            (df["risk_score"] >= 18)
            & (
                (df["b_failure_rate"] >= 0.08)
                | (df["bp_error_rate"] >= 0.15)
                | (df["ss_failure_rate"] >= 0.25)
                | (df["ss_timeout_rate"] >= 0.18)
            )
        )
        | (
            (df["risk_score"] >= 15)
            & (
                (df["wt_wallet_risk_score_100"] >= 12)
                | (df["cr_rejection_rate"] >= 0.15)
            )
        )
    )

    return future_failure.astype(int)


def evaluate_model(model, X, y, class_names):
    class_count = y.nunique()

    if len(y) < 10 or class_count < 2:
        model.fit(X, y)
        preds = model.predict(X)

        accuracy = accuracy_score(y, preds)

        report = classification_report(
            y,
            preds,
            labels=list(range(len(class_names))),
            target_names=class_names,
            output_dict=True,
            zero_division=0,
        )

        return accuracy, report, "trained_and_evaluated_on_full_data_small_dataset"

    try:
        stratify_value = y if y.value_counts().min() >= 2 else None

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.30,
            random_state=42,
            stratify=stratify_value,
        )

        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        accuracy = accuracy_score(y_test, preds)

        report = classification_report(
            y_test,
            preds,
            labels=list(range(len(class_names))),
            target_names=class_names,
            output_dict=True,
            zero_division=0,
        )

        model.fit(X, y)

        return accuracy, report, "train_test_split_then_refit_full_data"

    except Exception:
        model.fit(X, y)
        preds = model.predict(X)

        accuracy = accuracy_score(y, preds)

        report = classification_report(
            y,
            preds,
            labels=list(range(len(class_names))),
            target_names=class_names,
            output_dict=True,
            zero_division=0,
        )

        return accuracy, report, "fallback_full_data_training"


def train_best_classifier(X, y, class_names):
    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            class_weight="balanced",
        ),
        "GradientBoosting": GradientBoostingClassifier(
            random_state=42,
        ),
    }

    results = {}

    best_model_name = None
    best_model = None
    best_accuracy = -1

    for model_name, model in models.items():
        accuracy, report, evaluation_method = evaluate_model(
            model,
            X,
            y,
            class_names,
        )

        results[model_name] = {
            "accuracy": accuracy,
            "evaluation_method": evaluation_method,
            "classification_report": report,
        }

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model_name = model_name
            best_model = model

    return best_model_name, best_model, best_accuracy, results


def get_positive_class_probability(model, X):
    if not hasattr(model, "predict_proba"):
        return [0.0] * len(X)

    probabilities = model.predict_proba(X)

    if probabilities.shape[1] == 1:
        only_class = int(model.classes_[0])
        if only_class == 1:
            return [1.0] * len(X)
        return [0.0] * len(X)

    class_list = list(model.classes_)

    if 1 in class_list:
        positive_index = class_list.index(1)
    else:
        positive_index = probabilities.shape[1] - 1

    return probabilities[:, positive_index]


def train_models():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not FEATURE_FILE.exists():
        raise FileNotFoundError(
            f"Feature file not found: {FEATURE_FILE}. "
            "Run python -m app.ml.pipeline first."
        )

    print(f"Loading features from: {FEATURE_FILE}")

    df = pd.read_csv(FEATURE_FILE)
    df = df.fillna(0).copy()

    validate_features(df)

    X = df[FEATURE_COLUMNS]

    df["risk_target"] = df["risk_level"].map(LABEL_MAP)

    if df["risk_target"].isna().any():
        raise ValueError("risk_level contains unknown values.")

    y_risk = df["risk_target"].astype(int)

    (
        best_risk_model_name,
        best_risk_model,
        best_risk_accuracy,
        risk_results,
    ) = train_best_classifier(
        X,
        y_risk,
        ["LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"],
    )

    risk_model_bundle = {
        "model": best_risk_model,
        "model_name": best_risk_model_name,
        "feature_columns": FEATURE_COLUMNS,
        "label_map": LABEL_MAP,
        "reverse_label_map": REVERSE_LABEL_MAP,
        "model_purpose": "Current supplier risk classification",
    }

    joblib.dump(risk_model_bundle, RISK_MODEL_FILE)

    df["future_failure_7d"] = create_future_failure_target(df)
    y_future = df["future_failure_7d"].astype(int)

    (
        best_future_model_name,
        best_future_model,
        best_future_accuracy,
        future_results,
    ) = train_best_classifier(
        X,
        y_future,
        ["STABLE_NEXT_7D", "FAILURE_RISK_NEXT_7D"],
    )

    future_model_bundle = {
        "model": best_future_model,
        "model_name": best_future_model_name,
        "feature_columns": FEATURE_COLUMNS,
        "target": "future_failure_7d",
        "model_purpose": "Future supplier instability probability for next 7 days",
        "target_meaning": (
            "1 means supplier shows strong operational signals of possible "
            "instability in the next 7 days."
        ),
        "important_note": (
            "This is an ML-based proxy future-failure model. For real production "
            "forecasting, replace this proxy target with historical future failure labels."
        ),
    }

    joblib.dump(future_model_bundle, FUTURE_MODEL_FILE)

    metrics = {
        "dataset": {
            "row_count": int(len(df)),
            "supplier_count": int(df["supplier_code"].nunique())
            if "supplier_code" in df.columns
            else int(len(df)),
            "warning": (
                "Dataset is small. Accuracy may be optimistic. "
                "Collect supplier snapshots for stronger production forecasting."
            ),
        },
        "risk_model": {
            "best_model": best_risk_model_name,
            "best_accuracy": best_risk_accuracy,
            "target_distribution": df["risk_level"].value_counts().to_dict(),
            "results": risk_results,
        },
        "future_failure_model": {
            "best_model": best_future_model_name,
            "best_accuracy": best_future_accuracy,
            "target_distribution": df["future_failure_7d"].value_counts().to_dict(),
            "results": future_results,
        },
    }



    risk_preds = best_risk_model.predict(X)
    future_probs = get_positive_class_probability(best_future_model, X)

    output = df[
        [
            "supplier_code",
            "risk_score",
            "risk_level",
            "future_failure_7d",
        ]
    ].copy()

    output["predicted_risk"] = [
        REVERSE_LABEL_MAP[int(pred)]
        for pred in risk_preds
    ]

    output["future_failure_probability"] = [
        round(float(prob), 4)
        for prob in future_probs
    ]

    print("Production ML training completed successfully.")
    print(f"Risk model: {best_risk_model_name}")
    print(f"Risk accuracy: {best_risk_accuracy:.4f}")
    print(f"Risk model saved to: {RISK_MODEL_FILE}")

    print(f"Future failure model: {best_future_model_name}")
    print(f"Future failure accuracy: {best_future_accuracy:.4f}")
    print(f"Future failure model saved to: {FUTURE_MODEL_FILE}")

    print(f"Metrics saved to: {METRICS_FILE}")

    print("\nPredictions:")
    print(output)


if __name__ == "__main__":
    train_models()