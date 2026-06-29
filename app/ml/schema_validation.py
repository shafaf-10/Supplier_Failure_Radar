import pandas as pd


REQUIRED_COLUMNS = {
    "suppliers": ["code", "name"],
    "bookings": ["id", "status", "booking_date"],
    "booking_processes": ["created_at"],
    "booking_flights": ["booking_id"],
    "booking_passengers": ["booking_id"],
    "search_sessions": ["created_at"],
    "refund_requests": ["created_at"],
    "credit_requests": ["created_at"],
    "wallet_transactions": ["created_at"],
}


def validate_table_schema(
    table_name: str,
    df: pd.DataFrame,
) -> None:
    required = REQUIRED_COLUMNS.get(table_name, [])

    missing = [
        column for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns in {table_name}: {missing}"
        )   