import pandas as pd

from app.ml.feature_engineering.helpers import safe_rate, to_dt


def build_ticketing_features(
    bookings,
    booking_flights,
    booking_passengers,
    days=None,
):
    if bookings is None or bookings.empty:
        return pd.DataFrame()

    booking_df = bookings.copy()

    booking_df = to_dt(
        booking_df,
        [
            "created_at",
            "booking_date",
            "booked_at",
            "last_ticketing_date",
            "issue_date",
        ],
    )

    if days is not None and "created_at" in booking_df.columns:
        latest_date = booking_df["created_at"].max()
        cutoff = latest_date - pd.Timedelta(days=days)
        booking_df = booking_df[booking_df["created_at"] >= cutoff]

    booking_df["supplier_code"] = booking_df["provider"]

    booking_df["booking_pnr_missing"] = (
        booking_df["pnr"].isna()
        | (booking_df["pnr"].astype(str).str.strip() == "")
    ).astype(int)

    booking_df["supplier_pnr_missing"] = (
        booking_df["supplier_pnr"].isna()
        | (booking_df["supplier_pnr"].astype(str).str.strip() == "")
    ).astype(int)

    booking_status = booking_df["status"].astype(str).str.upper()

    booking_df["booking_not_issued"] = (
        ~booking_status.isin(
            ["TICKETED", "ISSUED", "CONFIRMED", "COMPLETED"]
        )
    ).astype(int)

    booking_features = booking_df.groupby("supplier_code").agg(
        ticket_booking_total=("supplier_code", "count"),
        booking_pnr_missing_count=("booking_pnr_missing", "sum"),
        supplier_pnr_missing_count=("supplier_pnr_missing", "sum"),
        booking_not_issued_count=("booking_not_issued", "sum"),
    ).reset_index()

    booking_features["booking_pnr_missing_rate"] = safe_rate(
        booking_features["booking_pnr_missing_count"],
        booking_features["ticket_booking_total"],
    ).fillna(0)

    booking_features["supplier_pnr_missing_rate"] = safe_rate(
        booking_features["supplier_pnr_missing_count"],
        booking_features["ticket_booking_total"],
    ).fillna(0)

    booking_features["booking_not_issued_rate"] = safe_rate(
        booking_features["booking_not_issued_count"],
        booking_features["ticket_booking_total"],
    ).fillna(0)

    supplier_parts = [booking_features]

    if booking_flights is not None and not booking_flights.empty:
        flights = booking_flights.copy()

        flights = to_dt(
            flights,
            [
                "created_at",
                "updated_at",
                "ticket_time_limit",
            ],
        )

        flight_map = booking_df[
            ["id", "supplier_code"]
        ].rename(columns={"id": "booking_id"})

        flights = flights.merge(
            flight_map,
            on="booking_id",
            how="left",
        )

        flights["flight_pnr_missing"] = (
            flights["flight_pnr"].isna()
            | (flights["flight_pnr"].astype(str).str.strip() == "")
        ).astype(int)

        flight_status = flights["current_status"].astype(str).str.upper()

        flights["flight_not_ticketed"] = (
            ~flight_status.isin(
                ["TICKETED", "ISSUED", "CONFIRMED", "COMPLETED"]
            )
        ).astype(int)

        latest_date = flights["created_at"].max()

        flights["ticket_time_limit_expired"] = (
            flights["ticket_time_limit"].notna()
            & (flights["ticket_time_limit"] < latest_date)
            & (flights["flight_not_ticketed"] == 1)
        ).astype(int)

        flight_features = flights.groupby("supplier_code").agg(
            ticket_flight_total=("supplier_code", "count"),
            flight_pnr_missing_count=("flight_pnr_missing", "sum"),
            flight_not_ticketed_count=("flight_not_ticketed", "sum"),
            ticket_time_limit_expired_count=(
                "ticket_time_limit_expired",
                "sum",
            ),
        ).reset_index()

        flight_features["flight_pnr_missing_rate"] = safe_rate(
            flight_features["flight_pnr_missing_count"],
            flight_features["ticket_flight_total"],
        ).fillna(0)

        flight_features["flight_not_ticketed_rate"] = safe_rate(
            flight_features["flight_not_ticketed_count"],
            flight_features["ticket_flight_total"],
        ).fillna(0)

        flight_features["ticket_time_limit_expired_rate"] = safe_rate(
            flight_features["ticket_time_limit_expired_count"],
            flight_features["ticket_flight_total"],
        ).fillna(0)

        supplier_parts.append(flight_features)

    if booking_passengers is not None and not booking_passengers.empty:
        passengers = booking_passengers.copy()

        passengers = to_dt(
            passengers,
            [
                "created_at",
                "updated_at",
                "fare_calculated_at",
            ],
        )

        passenger_map = booking_df[
            ["id", "supplier_code"]
        ].rename(columns={"id": "booking_id"})

        passengers = passengers.merge(
            passenger_map,
            on="booking_id",
            how="left",
        )

        passengers["ticket_number_missing"] = (
            passengers["ticket_number"].isna()
            | (passengers["ticket_number"].astype(str).str.strip() == "")
        ).astype(int)

        passenger_features = passengers.groupby("supplier_code").agg(
            ticket_passenger_total=("supplier_code", "count"),
            ticket_number_missing_count=("ticket_number_missing", "sum"),
        ).reset_index()

        passenger_features["ticket_number_missing_rate"] = safe_rate(
            passenger_features["ticket_number_missing_count"],
            passenger_features["ticket_passenger_total"],
        ).fillna(0)

        supplier_parts.append(passenger_features)

    supplier_ticketing_features = supplier_parts[0]

    for part in supplier_parts[1:]:
        supplier_ticketing_features = supplier_ticketing_features.merge(
            part,
            on="supplier_code",
            how="outer",
        )

    supplier_ticketing_features = supplier_ticketing_features.fillna(0)

    supplier_ticketing_features["supplier_ticketing_risk_score_100"] = (
        supplier_ticketing_features["booking_pnr_missing_rate"] * 20
        + supplier_ticketing_features["supplier_pnr_missing_rate"] * 20
        + supplier_ticketing_features["booking_not_issued_rate"] * 20
        + supplier_ticketing_features.get("flight_pnr_missing_rate", 0) * 15
        + supplier_ticketing_features.get("flight_not_ticketed_rate", 0) * 10
        + supplier_ticketing_features.get(
            "ticket_time_limit_expired_rate",
            0,
        )
        * 10
        + supplier_ticketing_features.get("ticket_number_missing_rate", 0) * 5
    ).clip(0, 100)

    return supplier_ticketing_features