# # from sqlalchemy import text

# # from app.infra.database import engine

# # TABLES = [
# #     "suppliers",
# #     "airlines",
# #     "airports",
# #     "booking_processes",
# #     "bookings",
# #     "booking_flights",
# #     "booking_segments",
# #     "booking_passengers",
# #     "refund_requests",
# #     "credit_requests",
# #     "search_sessions",
# #     "wallet_transactions",
# #     "supplier_features",
# #     "supplier_predictions",
# # ]

# # with engine.connect() as conn:
# #     print("\n===== TABLE COUNTS =====\n")

# #     for table in TABLES:
# #         result = conn.execute(
# #             text(f"SELECT COUNT(*) FROM {table}")
# #         ).scalar()

# #         print(f"{table:<25} : {result}")

# #     print("\nVerification Completed.")
# import sys
# from pathlib import Path

# ROOT_DIR = Path(__file__).resolve().parents[1]
# sys.path.insert(0, str(ROOT_DIR))

# import pandas as pd

# from app.infra.database import engine


# REQUIRED_TABLES = [
#     "suppliers",
#     "bookings",
#     "booking_processes",
#     "booking_flights",
#     "booking_passengers",
#     "refund_requests",
#     "credit_requests",
#     "search_sessions",
#     "wallet_transactions",
# ]


# def test_required_tables_exist():
#     tables = pd.read_sql("SHOW TABLES", engine)
#     existing_tables = set(tables.iloc[:, 0].tolist())

#     for table in REQUIRED_TABLES:
#         assert table in existing_tables, f"Missing table: {table}"


# def test_suppliers_exist():
#     df = pd.read_sql("SELECT COUNT(*) AS count FROM suppliers", engine)
#     assert df["count"].iloc[0] > 0


# def test_bookings_exist():
#     df = pd.read_sql("SELECT COUNT(*) AS count FROM bookings", engine)
#     assert df["count"].iloc[0] > 0


# # def test_predictions_exist():
# #     df = pd.read_sql("SELECT COUNT(*) AS count FROM supplier_predictions", engine)
# #     assert df["count"].iloc[0] > 0


# def test_booking_user_agent_relationship():
#     query = """
#         SELECT COUNT(*) AS invalid_count
#         FROM bookings b
#         LEFT JOIN users u ON b.user_id = u.id
#         LEFT JOIN agents a ON b.agent_id = a.id
#         WHERE b.user_id IS NULL
#            OR b.agent_id IS NULL
#            OR u.id IS NULL
#            OR a.id IS NULL
#            OR u.agent_id != b.agent_id
#     """

#     df = pd.read_sql(query, engine)
#     assert df["invalid_count"].iloc[0] == 0


# def test_supplier_predictions_have_valid_risk_levels():
#     query = """
#         SELECT COUNT(*) AS invalid_count
#         FROM supplier_predictions
#         WHERE risk_level NOT IN ('LOW_RISK', 'MEDIUM_RISK', 'HIGH_RISK')
#     """

#     df = pd.read_sql(query, engine)
#     assert df["invalid_count"].iloc[0] == 0



import sys
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.infra.database import engine


REQUIRED_TABLES = [
    "suppliers",
    "bookings",
    "booking_processes",
    "booking_flights",
    "booking_passengers",
    "refund_requests",
    "credit_requests",
    "search_sessions",
    "wallet_transactions",
    "users",
    "agents",
]


def test_required_tables_exist():
    tables = pd.read_sql("SHOW TABLES", engine)
    existing_tables = set(tables.iloc[:, 0].tolist())

    for table in REQUIRED_TABLES:
        assert table in existing_tables, f"Missing table: {table}"


def test_suppliers_exist():
    df = pd.read_sql("SELECT COUNT(*) AS count FROM suppliers", engine)
    assert df["count"].iloc[0] > 0


def test_bookings_exist():
    df = pd.read_sql("SELECT COUNT(*) AS count FROM bookings", engine)
    assert df["count"].iloc[0] > 0


def test_booking_user_agent_relationship():
    query = """
        SELECT COUNT(*) AS invalid_count
        FROM bookings b
        LEFT JOIN users u ON b.user_id = u.id
        LEFT JOIN agents a ON b.agent_id = a.id
        WHERE b.user_id IS NULL
           OR b.agent_id IS NULL
           OR u.id IS NULL
           OR a.id IS NULL
           OR u.agent_id != b.agent_id
    """

    df = pd.read_sql(query, engine)
    assert df["invalid_count"].iloc[0] == 0


def test_prediction_pipeline_runs():
    from app.ml.pipeline import run_prediction_pipeline

    df = run_prediction_pipeline()

    assert df is not None
    assert not df.empty


def test_prediction_pipeline_has_valid_risk_levels():
    from app.ml.pipeline import run_prediction_pipeline

    df = run_prediction_pipeline()

    valid_levels = {
        "LOW_RISK",
        "MEDIUM_RISK",
        "HIGH_RISK",
    }

    assert set(df["risk_level"].unique()).issubset(valid_levels)


def test_prediction_pipeline_required_columns():
    from app.ml.pipeline import run_prediction_pipeline

    df = run_prediction_pipeline()

    required_columns = [
        "supplier_code",
        "supplier_name",
        "risk_score",
        "risk_level",
        "predicted_risk",
        "prediction_probability",
        "anomaly_status",
        "future_instability_probability",
        "total_bookings",
    ]

    for column in required_columns:
        assert column in df.columns, f"Missing prediction column: {column}"