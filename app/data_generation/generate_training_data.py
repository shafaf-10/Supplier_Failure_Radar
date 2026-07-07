import random
import uuid
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy import text

from app.infra.database import SessionLocal
from app.observability.logger import setup_logger

logger = setup_logger(__name__)
from app.domain.models import (
    Supplier,
    Airline,
    Airport,
    BookingProcess,
    Booking,
    BookingFlight,
    BookingSegment,
    BookingPassenger,
    RefundRequest,
    CreditRequest,
    SearchSession,
    WalletTransaction,
)

fake = Faker()

TOTAL_BOOKINGS = 15000
CHUNK_SIZE = 1000


SUPPLIER_RISK_PROFILE = {
    "travclan": "GOOD",
    "sup_x9p4": "GOOD",
    "sup_q7d2": "MEDIUM",
    "sup_k2m7": "MEDIUM",
    "sup_f8a1": "HIGH_RISK",
    "sup_t6v3": "HIGH_RISK",
}


SUPPLIER_BEHAVIOR = {
    "GOOD": {
        "success": 0.94,
        "failed": 0.01,
        "pending": 0.02,
        "cancelled": 0.02,
        "expired": 0.01,
        "refund_probability": 0.03,
        "credit_probability": 0.04,
        "search_weights": [0.92, 0.05, 0.02, 0.01],
        "wallet_weights": [0.30, 0.45, 0.10, 0.14, 0.01],
        "attempt_min": 1,
        "attempt_max": 2,
    },
    "MEDIUM": {
        "success": 0.80,
        "failed": 0.06,
        "pending": 0.06,
        "cancelled": 0.05,
        "expired": 0.03,
        "refund_probability": 0.10,
        "credit_probability": 0.12,
        "search_weights": [0.70, 0.15, 0.09, 0.06],
        "wallet_weights": [0.25, 0.35, 0.18, 0.14, 0.08],
        "attempt_min": 1,
        "attempt_max": 4,
    },
    "HIGH_RISK": {
        "success": 0.55,
        "failed": 0.18,
        "pending": 0.12,
        "cancelled": 0.10,
        "expired": 0.05,
        "refund_probability": 0.22,
        "credit_probability": 0.25,
        "search_weights": [0.48, 0.20, 0.18, 0.14],
        "wallet_weights": [0.18, 0.28, 0.25, 0.10, 0.19],
        "attempt_min": 2,
        "attempt_max": 7,
    },
}


REFUND_STATUSES = ["PENDING", "APPROVED", "REJECTED", "REFUNDED"]
CREDIT_STATUSES = ["PENDING", "APPROVED", "REJECTED", "OVERDUE"]
SEARCH_STATUSES = ["COMPLETED", "PARTIAL", "FAILED", "TIMEOUT"]
WALLET_TYPES = ["CREDIT", "DEBIT", "HOLD", "RELEASE", "FAILED_PAYMENT"]


def clear_transaction_data(db):
    logger.info("Clearing old transaction and ML output data...")

    tables = [
        "supplier_predictions",
        "supplier_features",
        "supplier_feature_history",
        "wallet_transactions",
        "credit_requests",
        "refund_requests",
        "booking_passengers",
        "booking_segments",
        "booking_flights",
        "bookings",
        "booking_processes",
        "search_sessions",
    ]

    db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

    for table in tables:
        db.execute(text(f"DELETE FROM {table}"))

    db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    db.commit()
    logger.info("Old transaction data cleared successfully.")


def choose_supplier_group(supplier_code):
    return SUPPLIER_RISK_PROFILE.get(supplier_code, "MEDIUM")


def choose_booking_status(group):
    behavior = SUPPLIER_BEHAVIOR[group]

    return random.choices(
        population=["TICKETED", "FAILED", "PENDING", "CANCELLED", "EXPIRED"],
        weights=[
            behavior["success"],
            behavior["failed"],
            behavior["pending"],
            behavior["cancelled"],
            behavior["expired"],
        ],
        k=1,
    )[0]


def random_date():
    return datetime.now() - timedelta(
        days=random.randint(0, 90),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def get_master_data(db):
    suppliers = db.query(Supplier).order_by(Supplier.code).all()
    airlines = db.query(Airline).all()
    airports = db.query(Airport).all()

    users = db.execute(
        text("""
            SELECT
                id,
                agent_id
            FROM users
            WHERE agent_id IS NOT NULL
              AND is_active = 1
        """)
    ).mappings().all()

    if not suppliers:
        raise Exception("No suppliers found.")
    if not airlines:
        raise Exception("No airlines found.")
    if not airports:
        raise Exception("No airports found.")
    if not users:
        raise Exception("No active users linked to agents found.")

    return suppliers, airlines, airports, users


def select_user(users):
    user = random.choice(users)

    return {
        "user_id": int(user["id"]),
        "agent_id": int(user["agent_id"]),
    }


def choose_supplier_by_distribution(suppliers):
    supplier_map = {
        supplier.code: supplier
        for supplier in suppliers
    }

    weighted_codes = [
        "sup_f8a1",
        "sup_t6v3",
        "travclan",
        "sup_x9p4",
        "sup_k2m7",
        "sup_q7d2",
    ]

    weights = [
        0.25,
        0.22,
        0.18,
        0.13,
        0.12,
        0.10,
    ]

    available_codes = [
        code for code in weighted_codes
        if code in supplier_map
    ]

    if not available_codes:
        return random.choice(suppliers)

    available_weights = [
        weights[weighted_codes.index(code)]
        for code in available_codes
    ]

    selected_code = random.choices(
        available_codes,
        weights=available_weights,
        k=1,
    )[0]

    return supplier_map[selected_code]


def generate_chunk(
    db,
    start_index,
    end_index,
    suppliers,
    airlines,
    airports,
    users,
):
    for i in range(start_index, end_index):
        selected_user = select_user(users)

        user_id = selected_user["user_id"]
        agent_id = selected_user["agent_id"]

        supplier = choose_supplier_by_distribution(suppliers)
        supplier_code = supplier.code
        group = choose_supplier_group(supplier_code)
        behavior = SUPPLIER_BEHAVIOR[group]

        airline = random.choice(airlines)
        dep_airport = random.choice(airports)
        arr_airport = random.choice(airports)

        while arr_airport.iata_code == dep_airport.iata_code:
            arr_airport = random.choice(airports)

        created_at = random_date()
        status = choose_booking_status(group)

        attempts = random.randint(
            behavior["attempt_min"],
            behavior["attempt_max"],
        )

        process_state = "COMPLETED"

        if status == "FAILED":
            process_state = "FAILED"
        elif status == "PENDING":
            process_state = random.choice(["PENDING", "STUCK", "RETRYING"])
        elif status == "CANCELLED":
            process_state = "FAILED"
        elif status == "EXPIRED":
            process_state = random.choice(["FAILED", "STUCK"])

        process = BookingProcess(
            user_id=user_id,
            provider_code=supplier_code,
            state=process_state,
            current_step=random.choice(
                ["SEARCH", "FARE_CONFIRM", "BOOKING", "TICKETING", "PAYMENT"]
            ),
            context="Generated production-style B2B booking process",
            supplier_context=f"Supplier group: {group}",
            error_context=(
                fake.sentence()
                if process_state in ["FAILED", "STUCK", "RETRYING"]
                else None
            ),
            idempotency_key=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            attempts=attempts,
            last_transition_at=created_at + timedelta(minutes=random.randint(1, 30)),
            created_at=created_at,
            updated_at=created_at + timedelta(minutes=random.randint(1, 60)),
        )

        db.add(process)
        db.flush()

        passenger_count = random.randint(1, 4)
        total_amount = random.randint(3500, 85000)

        issue_date = None
        if status == "TICKETED":
            delay_hours = {
                "GOOD": random.randint(1, 4),
                "MEDIUM": random.randint(2, 10),
                "HIGH_RISK": random.randint(4, 24),
            }[group]

            issue_date = created_at + timedelta(hours=delay_hours)

        booking = Booking(
            booking_process_id=process.id,
            booking_ref_id=f"BRID{i}",
            invoice_number=f"INV{i}",
            pnr=fake.bothify(text="???###").upper(),
            supplier_pnr=fake.bothify(text="SUP???###").upper(),
            booking_ref=f"BK{i}",
            trace_id=process.trace_id,
            provider=supplier_code,
            status=status,
            refundable=random.choice([0, 1]),
            fare_type=random.choice(["PUBLISHED", "PRIVATE", "CORPORATE"]),
            currency="INR",
            total_amount=total_amount,
            warnings=(
                fake.sentence()
                if status in ["PENDING", "FAILED", "EXPIRED", "CANCELLED"]
                else None
            ),
            booked_at=created_at,
            agent_id=agent_id,
            user_id=user_id,
            created_at=created_at,
            booking_date=created_at,
            updated_at=created_at + timedelta(minutes=random.randint(1, 120)),
            last_ticketing_date=created_at + timedelta(hours=random.randint(4, 24)),
            hold_date=created_at if status == "PENDING" else None,
            issue_date=issue_date,
            owner=random.choice(["SYSTEM", "AGENT", "ADMIN"]),
            passenger_count=passenger_count,
        )

        db.add(booking)
        db.flush()

        flight = BookingFlight(
            booking_id=booking.id,
            purchase_id=f"PUR{i}",
            flight_pnr=booking.pnr,
            validating_airline=airline.iata_code,
            adult_count=max(1, passenger_count - random.randint(0, 1)),
            child_count=random.randint(0, 1),
            infant_count=random.randint(0, 1),
            currency="INR",
            current_status=status,
            refundable=booking.refundable,
            fare_type=booking.fare_type,
            ticket_time_limit=created_at + timedelta(hours=random.randint(2, 12)),
            fop=random.choice(["CASH", "CARD", "CREDIT", "WALLET"]),
            sequence=1,
            created_at=created_at,
            updated_at=booking.updated_at,
        )

        db.add(flight)
        db.flush()

        departure_time = created_at + timedelta(days=random.randint(1, 60))
        arrival_time = departure_time + timedelta(minutes=random.randint(60, 420))

        segment = BookingSegment(
            booking_flight_id=flight.id,
            airline=airline.iata_code,
            flight_number=str(random.randint(100, 9999)),
            cabin_class=random.choice(["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS"]),
            fare_basis=fake.bothify(text="??##").upper(),
            departure_airport=dep_airport.iata_code,
            arrival_airport=arr_airport.iata_code,
            departure_time=departure_time,
            arrival_time=arrival_time,
            departure_terminal=random.choice(["1", "2", "3", None]),
            arrival_terminal=random.choice(["1", "2", "3", None]),
            duration_minutes=int((arrival_time - departure_time).total_seconds() / 60),
            stop_over=random.choice([0, 1]),
            aircraft_code=random.choice(["320", "321", "737", "777", "787"]),
            codeshare=random.choice([0, 1]),
            operating_airline=airline.iata_code,
            sequence=1,
            created_at=created_at,
            updated_at=booking.updated_at,
            marketing_carrier=airline.iata_code,
            trip_indicator=random.choice(["ONEWAY", "ROUNDTRIP"]),
        )

        db.add(segment)

        for _ in range(passenger_count):
            base_fare = round(
                total_amount / passenger_count * random.uniform(0.65, 0.85),
                2,
            )
            ancillary = random.randint(0, 2500)
            total_fare = base_fare + ancillary

            passenger = BookingPassenger(
                booking_id=booking.id,
                booking_flight_id=flight.id,
                type=random.choice(["ADULT", "CHILD"]),
                title=random.choice(["MR", "MRS", "MS"]),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                dob=fake.date_of_birth(minimum_age=5, maximum_age=70),
                gender=random.choice(["MALE", "FEMALE"]),
                nationality=random.choice(["IN", "AE", "QA", "SA"]),
                passport_number=fake.bothify(text="??#######").upper(),
                passport_expiry=datetime.now().date()
                + timedelta(days=random.randint(300, 3000)),
                ticket_number=(
                    fake.bothify(text="###-##########")
                    if status == "TICKETED"
                    else None
                ),
                ff_airline=random.choice([airline.iata_code, None]),
                ff_number=fake.bothify(text="FF######"),
                email=fake.email(),
                phone_code="+91",
                phone=fake.msisdn()[:10],
                created_at=created_at,
                updated_at=booking.updated_at,
                base_fare=base_fare,
                total_fare=total_fare,
                ancillary_total=ancillary,
                fare_calculated_at=created_at,
            )

            db.add(passenger)

        if random.random() < behavior["refund_probability"]:
            refund_status = random.choices(
                REFUND_STATUSES,
                weights={
                    "GOOD": [0.15, 0.25, 0.05, 0.55],
                    "MEDIUM": [0.25, 0.25, 0.15, 0.35],
                    "HIGH_RISK": [0.40, 0.20, 0.20, 0.20],
                }[group],
                k=1,
            )[0]

            refunded_at = None
            refunded_amount = 0

            if refund_status == "REFUNDED":
                refund_days = {
                    "GOOD": random.randint(2, 7),
                    "MEDIUM": random.randint(5, 18),
                    "HIGH_RISK": random.randint(15, 45),
                }[group]

                refunded_at = created_at + timedelta(days=refund_days)
                refunded_amount = total_amount * random.uniform(0.60, 0.95)

            refund = RefundRequest(
                booking_id=booking.id,
                agent_id=agent_id,
                reference_no=f"REF{i}",
                pnr=booking.pnr,
                status=refund_status,
                requested_amount=total_amount,
                refunded_amount=round(refunded_amount, 2),
                reason=random.choice(
                    ["Flight cancelled", "Customer request", "Supplier failure"]
                ),
                admin_notes=fake.sentence(),
                refunded_at=refunded_at,
                created_at=created_at + timedelta(days=random.randint(1, 5)),
                updated_at=created_at + timedelta(days=random.randint(5, 25)),
            )

            db.add(refund)

        if random.random() < behavior["credit_probability"]:
            credit_status = random.choices(
                CREDIT_STATUSES,
                weights={
                    "GOOD": [0.10, 0.75, 0.10, 0.05],
                    "MEDIUM": [0.20, 0.50, 0.15, 0.15],
                    "HIGH_RISK": [0.30, 0.30, 0.20, 0.20],
                }[group],
                k=1,
            )[0]

            credit = CreditRequest(
                agent_id=agent_id,
                admin_id=random.randint(1, 10),
                supplier_code=supplier_code,
                amount=random.randint(10000, 300000),
                requested_credit_days=random.randint(1, 7),
                service_fee_amount=random.randint(100, 3000),
                remarks=fake.sentence(),
                status=credit_status,
                settlement_due_date=created_at + timedelta(days=random.randint(1, 7)),
                approved_at=(
                    created_at + timedelta(hours=2)
                    if credit_status == "APPROVED"
                    else None
                ),
                rejected_at=(
                    created_at + timedelta(hours=2)
                    if credit_status == "REJECTED"
                    else None
                ),
                created_at=created_at,
                updated_at=created_at + timedelta(days=random.randint(1, 8)),
            )

            db.add(credit)

        if random.random() < 0.75:
            search_status = random.choices(
                SEARCH_STATUSES,
                weights=behavior["search_weights"],
                k=1,
            )[0]

            expected = random.randint(3, 8)
            completed = expected

            if search_status == "PARTIAL":
                completed = random.randint(1, expected - 1)
            elif search_status in ["FAILED", "TIMEOUT"]:
                completed = random.randint(0, 1)

            search = SearchSession(
                public_id=str(uuid.uuid4()),
                supplier_code=supplier_code,
                criteria_hash=str(uuid.uuid4()),
                status=search_status,
                expected_suppliers=expected,
                completed_suppliers=completed,
                expires_at=created_at + timedelta(minutes=30),
                criteria=f"{dep_airport.iata_code}-{arr_airport.iata_code}",
                created_at=created_at,
                updated_at=created_at + timedelta(minutes=random.randint(1, 10)),
            )

            db.add(search)

        wallet_type = random.choices(
            WALLET_TYPES,
            weights=behavior["wallet_weights"],
            k=1,
        )[0]

        opening_balance = random.randint(50000, 800000)
        amount = random.randint(1000, 90000)

        if wallet_type in ["DEBIT", "HOLD", "FAILED_PAYMENT"]:
            closing_balance = opening_balance - amount
        else:
            closing_balance = opening_balance + amount

        wallet = WalletTransaction(
            parent_id=None,
            wallet_account_id=agent_id,
            supplier_code=supplier_code,
            type=wallet_type,
            ledger_category=random.choice(["BOOKING", "REFUND", "CREDIT", "ADJUSTMENT"]),
            balance_bucket=random.choice(["AVAILABLE", "HOLD", "CREDIT"]),
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            credit_days_term=random.randint(1, 7),
            due_date=created_at + timedelta(days=random.randint(1, 7)),
            agent_id=agent_id,
            amount=amount,
            currency="INR",
            payment_amount=amount,
            payment_currency="INR",
            fx_rate=1.0,
            fx_source="SYSTEM",
            reference_type="BOOKING",
            reference_id=booking.id,
            description=f"{group} wallet transaction for booking {booking.id}",
            running_balance=closing_balance,
            created_by=user_id,
            created_at=created_at,
            updated_at=booking.updated_at,
        )

        db.add(wallet)

    db.commit()


def main():
    db = SessionLocal()

    try:
        suppliers, airlines, airports, users = get_master_data(db)

        clear_transaction_data(db)

        print("Production-style B2B training data generation started...")
        logger.info("Total bookings: %s", TOTAL_BOOKINGS)
        print(f"Chunk size: {CHUNK_SIZE}")
        print(f"Valid users linked to agents: {len(users)}")
        print("Supplier risk mapping:")

        for supplier in suppliers:
            logger.info("- %s: %s", supplier.code, choose_supplier_group(supplier.code))

        for start in range(0, TOTAL_BOOKINGS, CHUNK_SIZE):
            end = min(start + CHUNK_SIZE, TOTAL_BOOKINGS)

            print(f"Generating records {start + 1} to {end}...")

            generate_chunk(
                db=db,
                start_index=start,
                end_index=end,
                suppliers=suppliers,
                airlines=airlines,
                airports=airports,
                users=users,
            )

            print(f"Chunk completed: {start + 1} to {end}")

        print("Production-style B2B data generation completed successfully.")

    except Exception as error:
        db.rollback()
        logger.exception("Error while generating data: %s", error)

    finally:
        db.close()


if __name__ == "__main__":
    main()