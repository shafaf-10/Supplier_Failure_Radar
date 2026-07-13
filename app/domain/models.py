from pydantic import BaseModel
from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    Numeric,
)
from sqlalchemy.orm import declarative_base


Base = declarative_base()
class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255))
    email = Column(String(255), unique=True)
    phone = Column(String(50))
    password = Column(String(255))

    two_factor_secret = Column(Text)
    two_factor_recovery_codes = Column(Text)
    two_factor_confirmed_at = Column(DateTime)

    google2fa_secret = Column(Text)
    google2fa_enabled_at = Column(DateTime)

    is_active = Column(Integer, default=1)
    email_verified_at = Column(DateTime)
    remember_token = Column(String(255))

    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    parent_id = Column(BigInteger)

    email = Column(String(255))
    establishment_name = Column(String(255))
    director_name = Column(String(255))
    nature_of_business = Column(String(255))

    cr_number = Column(String(100))
    cr_expiry_date = Column(Date)
    vat_number = Column(String(100))

    street = Column(String(255))
    country = Column(String(100))
    state = Column(String(100))
    city = Column(String(100))
    province = Column(String(100))

    office_telephone = Column(String(50))
    office_email = Column(String(255))

    bank_name = Column(String(255))
    bank_branch = Column(String(255))
    account_number = Column(String(100))
    iban = Column(String(100))

    manager_name = Column(String(255))
    manager_email = Column(String(255))
    manager_mobile = Column(String(50))

    finance_name = Column(String(255))
    finance_email = Column(String(255))
    finance_mobile = Column(String(50))

    ticketing_contact = Column(String(100))
    holidays_contact = Column(String(100))

    annual_volume_words = Column(String(255))
    annual_volume_figures = Column(Numeric(15, 2))

    agent_type = Column(String(100))
    business_type = Column(String(100))
    recommended_by = Column(String(255))

    cr_copy_path = Column(String(500))
    vat_certificate_path = Column(String(500))
    authorized_id_path = Column(String(500))
    company_stamp_path = Column(String(500))
    scanned_signature_path = Column(String(500))
    signature_data = Column(Text)

    onboarding_submitted_at = Column(DateTime)
    is_active = Column(Integer, default=1)
    approval_status = Column(String(50))

    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Airline(Base):
    __tablename__ = "airlines"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    iata_code = Column(String(10))
    airline_name = Column(String(255))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Airport(Base):
    __tablename__ = "airports"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255))
    country = Column(String(100))
    iata_code = Column(String(10))
    city_name = Column(String(100))
    city_code = Column(String(20))
    country_code = Column(String(20))
    region_code = Column(String(20))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True)
    name = Column(String(255))
    is_active = Column(Integer)
    health_status = Column(String(50))
    last_checked_at = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class BookingProcess(Base):
    __tablename__ = "booking_processes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    provider_code = Column(String(50))
    state = Column(String(50))
    current_step = Column(String(100))
    context = Column(Text)
    supplier_context = Column(Text)
    error_context = Column(Text)
    idempotency_key = Column(String(255))
    trace_id = Column(String(255))
    attempts = Column(Integer)
    last_transition_at = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    booking_process_id = Column(BigInteger)
    booking_ref_id = Column(String(100))
    invoice_number = Column(String(100))
    pnr = Column(String(100))
    supplier_pnr = Column(String(100))
    booking_ref = Column(String(100))
    trace_id = Column(String(255))
    provider = Column(String(50))
    status = Column(String(50))
    refundable = Column(Integer)
    fare_type = Column(String(50))
    currency = Column(String(10))
    total_amount = Column(Numeric(12, 2))
    warnings = Column(Text)
    booked_at = Column(DateTime)
    agent_id = Column(BigInteger)
    user_id = Column(BigInteger)
    created_at = Column(DateTime)
    booking_date = Column(DateTime)
    updated_at = Column(DateTime)
    last_ticketing_date = Column(DateTime)
    hold_date = Column(DateTime)
    issue_date = Column(DateTime)
    owner = Column(String(100))
    passenger_count = Column(Integer)


class BookingFlight(Base):
    __tablename__ = "booking_flights"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    booking_id = Column(BigInteger)
    purchase_id = Column(String(100))
    flight_pnr = Column(String(100))
    validating_airline = Column(String(10))
    adult_count = Column(Integer)
    child_count = Column(Integer)
    infant_count = Column(Integer)
    currency = Column(String(10))
    current_status = Column(String(50))
    refundable = Column(Integer)
    fare_type = Column(String(50))
    ticket_time_limit = Column(DateTime)
    fop = Column(String(50))
    sequence = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class BookingSegment(Base):
    __tablename__ = "booking_segments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    booking_flight_id = Column(BigInteger)
    airline = Column(String(10))
    flight_number = Column(String(20))
    cabin_class = Column(String(50))
    fare_basis = Column(String(50))
    departure_airport = Column(String(10))
    arrival_airport = Column(String(10))
    departure_time = Column(DateTime)
    arrival_time = Column(DateTime)
    departure_terminal = Column(String(20))
    arrival_terminal = Column(String(20))
    duration_minutes = Column(Integer)
    stop_over = Column(Integer)
    aircraft_code = Column(String(20))
    codeshare = Column(Integer)
    operating_airline = Column(String(10))
    sequence = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    marketing_carrier = Column(String(10))
    trip_indicator = Column(String(50))


class BookingPassenger(Base):
    __tablename__ = "booking_passengers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    booking_id = Column(BigInteger)
    booking_flight_id = Column(BigInteger)
    type = Column(String(50))
    title = Column(String(20))
    first_name = Column(String(100))
    last_name = Column(String(100))
    dob = Column(Date)
    gender = Column(String(20))
    nationality = Column(String(100))
    passport_number = Column(String(100))
    passport_expiry = Column(Date)
    ticket_number = Column(String(100))
    ff_airline = Column(String(10))
    ff_number = Column(String(100))
    email = Column(String(255))
    phone_code = Column(String(20))
    phone = Column(String(50))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    base_fare = Column(Numeric(12, 2))
    total_fare = Column(Numeric(12, 2))
    ancillary_total = Column(Numeric(12, 2))
    fare_calculated_at = Column(DateTime)


class RefundRequest(Base):
    __tablename__ = "refund_requests"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    booking_id = Column(BigInteger)
    agent_id = Column(BigInteger)
    reference_no = Column(String(100))
    pnr = Column(String(100))
    status = Column(String(50))
    requested_amount = Column(Numeric(12, 2))
    refunded_amount = Column(Numeric(12, 2))
    reason = Column(Text)
    admin_notes = Column(Text)
    refunded_at = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class CreditRequest(Base):
    __tablename__ = "credit_requests"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    agent_id = Column(BigInteger)
    admin_id = Column(BigInteger)
    supplier_code = Column(String(50))
    amount = Column(Numeric(12, 2))
    requested_credit_days = Column(Integer)
    service_fee_amount = Column(Numeric(12, 2))
    remarks = Column(Text)
    status = Column(String(50))
    settlement_due_date = Column(DateTime)
    approved_at = Column(DateTime)
    rejected_at = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class SearchSession(Base):
    __tablename__ = "search_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    public_id = Column(String(100))
    supplier_code = Column(String(50))
    criteria_hash = Column(String(255))
    status = Column(String(50))
    expected_suppliers = Column(Integer)
    completed_suppliers = Column(Integer)
    expires_at = Column(DateTime)
    criteria = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    parent_id = Column(BigInteger)
    wallet_account_id = Column(BigInteger)
    supplier_code = Column(String(50))
    type = Column(String(50))
    ledger_category = Column(String(100))
    balance_bucket = Column(String(100))
    opening_balance = Column(Numeric(12, 2))
    closing_balance = Column(Numeric(12, 2))
    credit_days_term = Column(Integer)
    due_date = Column(DateTime)
    agent_id = Column(BigInteger)
    amount = Column(Numeric(12, 2))
    currency = Column(String(10))
    payment_amount = Column(Numeric(12, 2))
    payment_currency = Column(String(10))
    fx_rate = Column(Numeric(10, 4))
    fx_source = Column(String(100))
    reference_type = Column(String(100))
    reference_id = Column(BigInteger)
    description = Column(Text)
    running_balance = Column(Numeric(12, 2))
    created_by = Column(BigInteger)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


