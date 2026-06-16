from sqlalchemy import text

from app.infra.database import engine

TABLES = [
    "suppliers",
    "airlines",
    "airports",
    "booking_processes",
    "bookings",
    "booking_flights",
    "booking_segments",
    "booking_passengers",
    "refund_requests",
    "credit_requests",
    "search_sessions",
    "wallet_transactions",
    "supplier_features",
    "supplier_predictions",
]

with engine.connect() as conn:
    print("\n===== TABLE COUNTS =====\n")

    for table in TABLES:
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {table}")
        ).scalar()

        print(f"{table:<25} : {result}")

    print("\nVerification Completed.")