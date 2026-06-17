import random
import hashlib
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy import text

from app.infra.database import engine


fake = Faker()

TOTAL_AGENTS = 100
TOTAL_USERS = 1002


AGENT_TYPES = [
    "B2B_AGENT",
    "CORPORATE_AGENT",
    "SUB_AGENT",
    "WHOLESALE_AGENT",
]

BUSINESS_TYPES = [
    "TRAVEL_AGENCY",
    "TOUR_OPERATOR",
    "CORPORATE_TRAVEL",
    "ONLINE_TRAVEL_AGENT",
]

COUNTRIES = ["UAE", "Qatar", "Saudi Arabia", "India"]

CITIES = [
    "Dubai",
    "Abu Dhabi",
    "Sharjah",
    "Doha",
    "Riyadh",
    "Kochi",
    "Kannur",
    "Bengaluru",
    "Chennai",
    "Mumbai",
]


def fake_password(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def clear_users_agents():
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        conn.execute(text("TRUNCATE TABLE agents"))
        conn.execute(text("TRUNCATE TABLE users"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def create_agent(conn, index):
    company = fake.company()
    city = random.choice(CITIES)
    country = random.choice(COUNTRIES)

    created_at = datetime.now() - timedelta(
        days=random.randint(30, 900)
    )

    email = f"agency{index:03d}@afinetripdemo.com"

    result = conn.execute(
        text("""
            INSERT INTO agents (
                user_id,
                parent_id,
                email,
                establishment_name,
                director_name,
                nature_of_business,
                cr_number,
                cr_expiry_date,
                vat_number,
                street,
                country,
                state,
                city,
                province,
                office_telephone,
                office_email,
                bank_name,
                bank_branch,
                account_number,
                iban,
                manager_name,
                manager_email,
                manager_mobile,
                finance_name,
                finance_email,
                finance_mobile,
                ticketing_contact,
                holidays_contact,
                annual_volume_words,
                annual_volume_figures,
                agent_type,
                business_type,
                recommended_by,
                cr_copy_path,
                vat_certificate_path,
                authorized_id_path,
                company_stamp_path,
                scanned_signature_path,
                signature_data,
                onboarding_submitted_at,
                is_active,
                approval_status,
                created_at,
                updated_at
            )
            VALUES (
                NULL,
                NULL,
                :email,
                :establishment_name,
                :director_name,
                :nature_of_business,
                :cr_number,
                :cr_expiry_date,
                :vat_number,
                :street,
                :country,
                :state,
                :city,
                :province,
                :office_telephone,
                :office_email,
                :bank_name,
                :bank_branch,
                :account_number,
                :iban,
                :manager_name,
                :manager_email,
                :manager_mobile,
                :finance_name,
                :finance_email,
                :finance_mobile,
                :ticketing_contact,
                :holidays_contact,
                :annual_volume_words,
                :annual_volume_figures,
                :agent_type,
                :business_type,
                :recommended_by,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                :onboarding_submitted_at,
                :is_active,
                :approval_status,
                :created_at,
                :updated_at
            )
        """),
        {
            "email": email,
            "establishment_name": company,
            "director_name": fake.name(),
            "nature_of_business": "Travel and airline ticketing services",
            "cr_number": f"CR-{random.randint(100000, 999999)}",
            "cr_expiry_date": datetime.now().date()
            + timedelta(days=random.randint(90, 1000)),
            "vat_number": f"VAT-{random.randint(100000000, 999999999)}",
            "street": fake.street_address(),
            "country": country,
            "state": city,
            "city": city,
            "province": city,
            "office_telephone": f"+9714{random.randint(1000000, 9999999)}",
            "office_email": email,
            "bank_name": random.choice(
                ["Emirates NBD", "ADCB", "Mashreq Bank", "HDFC Bank", "QNB"]
            ),
            "bank_branch": city,
            "account_number": str(random.randint(1000000000, 9999999999)),
            "iban": f"AE{random.randint(1000000000000000000000, 9999999999999999999999)}",
            "manager_name": fake.name(),
            "manager_email": f"manager{index:03d}@afinetripdemo.com",
            "manager_mobile": f"+9715{random.randint(10000000, 99999999)}",
            "finance_name": fake.name(),
            "finance_email": f"finance{index:03d}@afinetripdemo.com",
            "finance_mobile": f"+9715{random.randint(10000000, 99999999)}",
            "ticketing_contact": f"Ticketing {company}",
            "holidays_contact": f"Holidays {company}",
            "annual_volume_words": "One million AED",
            "annual_volume_figures": random.randint(100000, 5000000),
            "agent_type": random.choice(AGENT_TYPES),
            "business_type": random.choice(BUSINESS_TYPES),
            "recommended_by": random.choice(
                ["Sales Team", "Referral", "Online Lead", "Corporate Network"]
            ),
            "onboarding_submitted_at": created_at,
            "is_active": 1,
            "approval_status": random.choice(
                ["APPROVED", "APPROVED", "APPROVED", "PENDING"]
            ),
            "created_at": created_at,
            "updated_at": created_at,
        },
    )

    return result.lastrowid


def create_user(conn, index, agent_id):
    full_name = fake.name()
    email = f"user{index:04d}@afinetripdemo.com"

    created_at = datetime.now() - timedelta(
        days=random.randint(1, 720)
    )

    result = conn.execute(
        text("""
            INSERT INTO users (
                agent_id,
                name,
                email,
                phone,
                password,
                is_active,
                email_verified_at,
                remember_token,
                created_at,
                updated_at
            )
            VALUES (
                :agent_id,
                :name,
                :email,
                :phone,
                :password,
                :is_active,
                :email_verified_at,
                NULL,
                :created_at,
                :updated_at
            )
        """),
        {
            "agent_id": agent_id,
            "name": full_name,
            "email": email,
            "phone": f"+9715{random.randint(10000000, 99999999)}",
            "password": fake_password("password123"),
            "is_active": 1,
            "email_verified_at": created_at,
            "created_at": created_at,
            "updated_at": created_at,
        },
    )

    return result.lastrowid


def assign_primary_user_to_agent(conn, agent_id, user_id):
    conn.execute(
        text("""
            UPDATE agents
            SET user_id = :user_id
            WHERE id = :agent_id
        """),
        {
            "user_id": user_id,
            "agent_id": agent_id,
        },
    )


def generate_users_agents():
    print("Clearing old users and agents...")
    clear_users_agents()

    print("Generating 100 agents and 1002 linked users...")

    with engine.begin() as conn:
        agent_ids = []

        for i in range(1, TOTAL_AGENTS + 1):
            agent_id = create_agent(conn, i)
            agent_ids.append(agent_id)

        user_count_by_agent = {
            agent_id: 0
            for agent_id in agent_ids
        }

        for i in range(1, TOTAL_USERS + 1):
            agent_id = random.choice(agent_ids)

            user_id = create_user(
                conn=conn,
                index=i,
                agent_id=agent_id,
            )

            user_count_by_agent[agent_id] += 1

            if user_count_by_agent[agent_id] == 1:
                assign_primary_user_to_agent(
                    conn=conn,
                    agent_id=agent_id,
                    user_id=user_id,
                )

    print("Generation completed successfully.")
    print(f"Agents created: {TOTAL_AGENTS}")
    print(f"Users created: {TOTAL_USERS}")
    print("Each user is linked to a valid agent_id.")
    print("Each agent has a primary user_id.")


if __name__ == "__main__":
    generate_users_agents()