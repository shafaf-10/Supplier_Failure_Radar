# import random
# import hashlib
# from datetime import datetime, timedelta

# from faker import Faker
# from sqlalchemy import text

# from app.infra.database import engine
# from app.observability.logger import setup_logger

# logger = setup_logger(__name__)


# fake = Faker()

# TOTAL_AGENTS = 100
# TOTAL_USERS = 1002


# AGENT_TYPES = [
#     "B2B_AGENT",
#     "CORPORATE_AGENT",
#     "SUB_AGENT",
#     "WHOLESALE_AGENT",
# ]

# BUSINESS_TYPES = [
#     "TRAVEL_AGENCY",
#     "TOUR_OPERATOR",
#     "CORPORATE_TRAVEL",
#     "ONLINE_TRAVEL_AGENT",
# ]

# COUNTRIES = ["UAE", "Qatar", "Saudi Arabia", "India"]

# CITIES = [
#     "Dubai",
#     "Abu Dhabi",
#     "Sharjah",
#     "Doha",
#     "Riyadh",
#     "Kochi",
#     "Kannur",
#     "Bengaluru",
#     "Chennai",
#     "Mumbai",
# ]


# def fake_password(value: str) -> str:
#     return hashlib.sha256(value.encode()).hexdigest()


# def clear_users_agents():
#     with engine.begin() as conn:
#         conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
#         conn.execute(text("TRUNCATE TABLE agents"))
#         conn.execute(text("TRUNCATE TABLE users"))
#         conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


# def create_agent(conn, index):
#     company = fake.company()
#     city = random.choice(CITIES)
#     country = random.choice(COUNTRIES)

#     created_at = datetime.now() - timedelta(
#         days=random.randint(30, 900)
#     )

#     email = f"agency{index:03d}@afinetripdemo.com"

#     result = conn.execute(
#         text("""
#             INSERT INTO agents (
#                 user_id,
#                 parent_id,
#                 email,
#                 establishment_name,
#                 director_name,
#                 nature_of_business,
#                 cr_number,
#                 cr_expiry_date,
#                 vat_number,
#                 street,
#                 country,
#                 state,
#                 city,
#                 province,
#                 office_telephone,
#                 office_email,
#                 bank_name,
#                 bank_branch,
#                 account_number,
#                 iban,
#                 manager_name,
#                 manager_email,
#                 manager_mobile,
#                 finance_name,
#                 finance_email,
#                 finance_mobile,
#                 ticketing_contact,
#                 holidays_contact,
#                 annual_volume_words,
#                 annual_volume_figures,
#                 agent_type,
#                 business_type,
#                 recommended_by,
#                 cr_copy_path,
#                 vat_certificate_path,
#                 authorized_id_path,
#                 company_stamp_path,
#                 scanned_signature_path,
#                 signature_data,
#                 onboarding_submitted_at,
#                 is_active,
#                 approval_status,
#                 created_at,
#                 updated_at
#             )
#             VALUES (
#                 NULL,
#                 NULL,
#                 :email,
#                 :establishment_name,
#                 :director_name,
#                 :nature_of_business,
#                 :cr_number,
#                 :cr_expiry_date,
#                 :vat_number,
#                 :street,
#                 :country,
#                 :state,
#                 :city,
#                 :province,
#                 :office_telephone,
#                 :office_email,
#                 :bank_name,
#                 :bank_branch,
#                 :account_number,
#                 :iban,
#                 :manager_name,
#                 :manager_email,
#                 :manager_mobile,
#                 :finance_name,
#                 :finance_email,
#                 :finance_mobile,
#                 :ticketing_contact,
#                 :holidays_contact,
#                 :annual_volume_words,
#                 :annual_volume_figures,
#                 :agent_type,
#                 :business_type,
#                 :recommended_by,
#                 NULL,
#                 NULL,
#                 NULL,
#                 NULL,
#                 NULL,
#                 NULL,
#                 :onboarding_submitted_at,
#                 :is_active,
#                 :approval_status,
#                 :created_at,
#                 :updated_at
#             )
#         """),
#         {
#             "email": email,
#             "establishment_name": company,
#             "director_name": fake.name(),
#             "nature_of_business": "Travel and airline ticketing services",
#             "cr_number": f"CR-{random.randint(100000, 999999)}",
#             "cr_expiry_date": datetime.now().date()
#             + timedelta(days=random.randint(90, 1000)),
#             "vat_number": f"VAT-{random.randint(100000000, 999999999)}",
#             "street": fake.street_address(),
#             "country": country,
#             "state": city,
#             "city": city,
#             "province": city,
#             "office_telephone": f"+9714{random.randint(1000000, 9999999)}",
#             "office_email": email,
#             "bank_name": random.choice(
#                 ["Emirates NBD", "ADCB", "Mashreq Bank", "HDFC Bank", "QNB"]
#             ),
#             "bank_branch": city,
#             "account_number": str(random.randint(1000000000, 9999999999)),
#             "iban": f"AE{random.randint(1000000000000000000000, 9999999999999999999999)}",
#             "manager_name": fake.name(),
#             "manager_email": f"manager{index:03d}@afinetripdemo.com",
#             "manager_mobile": f"+9715{random.randint(10000000, 99999999)}",
#             "finance_name": fake.name(),
#             "finance_email": f"finance{index:03d}@afinetripdemo.com",
#             "finance_mobile": f"+9715{random.randint(10000000, 99999999)}",
#             "ticketing_contact": f"Ticketing {company}",
#             "holidays_contact": f"Holidays {company}",
#             "annual_volume_words": "One million AED",
#             "annual_volume_figures": random.randint(100000, 5000000),
#             "agent_type": random.choice(AGENT_TYPES),
#             "business_type": random.choice(BUSINESS_TYPES),
#             "recommended_by": random.choice(
#                 ["Sales Team", "Referral", "Online Lead", "Corporate Network"]
#             ),
#             "onboarding_submitted_at": created_at,
#             "is_active": 1,
#             "approval_status": random.choice(
#                 ["APPROVED", "APPROVED", "APPROVED", "PENDING"]
#             ),
#             "created_at": created_at,
#             "updated_at": created_at,
#         },
#     )

#     return result.lastrowid


# def create_user(conn, index, agent_id):
#     full_name = fake.name()
#     email = f"user{index:04d}@afinetripdemo.com"

#     created_at = datetime.now() - timedelta(
#         days=random.randint(1, 720)
#     )

#     result = conn.execute(
#         text("""
#             INSERT INTO users (
#                 agent_id,
#                 name,
#                 email,
#                 phone,
#                 password,
#                 is_active,
#                 email_verified_at,
#                 remember_token,
#                 created_at,
#                 updated_at
#             )
#             VALUES (
#                 :agent_id,
#                 :name,
#                 :email,
#                 :phone,
#                 :password,
#                 :is_active,
#                 :email_verified_at,
#                 NULL,
#                 :created_at,
#                 :updated_at
#             )
#         """),
#         {
#             "agent_id": agent_id,
#             "name": full_name,
#             "email": email,
#             "phone": f"+9715{random.randint(10000000, 99999999)}",
#             "password": fake_password("password123"),
#             "is_active": 1,
#             "email_verified_at": created_at,
#             "created_at": created_at,
#             "updated_at": created_at,
#         },
#     )

#     return result.lastrowid


# def assign_primary_user_to_agent(conn, agent_id, user_id):
#     conn.execute(
#         text("""
#             UPDATE agents
#             SET user_id = :user_id
#             WHERE id = :agent_id
#         """),
#         {
#             "user_id": user_id,
#             "agent_id": agent_id,
#         },
#     )


# def generate_users_agents():
#     logger.info("Clearing old users and agents...")
#     clear_users_agents()

#     logger.info("Generating %s agents and %s linked users...", TOTAL_AGENTS, TOTAL_USERS)

#     with engine.begin() as conn:
#         agent_ids = []

#         for i in range(1, TOTAL_AGENTS + 1):
#             agent_id = create_agent(conn, i)
#             agent_ids.append(agent_id)

#         user_count_by_agent = {
#             agent_id: 0
#             for agent_id in agent_ids
#         }

#         for i in range(1, TOTAL_USERS + 1):
#             agent_id = random.choice(agent_ids)

#             user_id = create_user(
#                 conn=conn,
#                 index=i,
#                 agent_id=agent_id,
#             )

#             user_count_by_agent[agent_id] += 1

#             if user_count_by_agent[agent_id] == 1:
#                 assign_primary_user_to_agent(
#                     conn=conn,
#                     agent_id=agent_id,
#                     user_id=user_id,
#                 )

#     logger.info("Generation completed successfully.")
#     logger.info("Agents created: %s", TOTAL_AGENTS)
#     logger.info("Users created: %s", TOTAL_USERS)
#     logger.info("Each user is linked to a valid agent_id.")
#     logger.info("Each agent has a primary user_id.")


# if __name__ == "__main__":
#     generate_users_agents()



import hashlib
import json
import random
import secrets
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy import text

from app.infra.database import engine
from app.observability.logger import setup_logger

logger = setup_logger(__name__)
fake = Faker()
Faker.seed(42)
random.seed(42)

TOTAL_ADMINS = 3
TOTAL_AGENTS = 1000
DEFAULT_PASSWORD = "Password@123"

AGENT_TYPES = ["B2B_AGENT", "CORPORATE_AGENT", "SUB_AGENT", "WHOLESALE_AGENT"]
BUSINESS_TYPES = ["TRAVEL_AGENCY", "TOUR_OPERATOR", "CORPORATE_TRAVEL", "ONLINE_TRAVEL_AGENT"]
APPROVAL_STATUSES = ["APPROVED", "APPROVED", "APPROVED", "APPROVED", "PENDING"]

LOCATION_DATA = [
    ("United Arab Emirates", "Dubai", "Dubai", "Dubai", "+971"),
    ("United Arab Emirates", "Abu Dhabi", "Abu Dhabi", "Abu Dhabi", "+971"),
    ("United Arab Emirates", "Sharjah", "Sharjah", "Sharjah", "+971"),
    ("Qatar", "Doha", "Doha", "Doha", "+974"),
    ("Saudi Arabia", "Riyadh", "Riyadh", "Riyadh", "+966"),
    ("India", "Kerala", "Kochi", "Ernakulam", "+91"),
    ("India", "Kerala", "Kannur", "Kannur", "+91"),
    ("India", "Karnataka", "Bengaluru", "Bengaluru Urban", "+91"),
    ("India", "Tamil Nadu", "Chennai", "Chennai", "+91"),
    ("India", "Maharashtra", "Mumbai", "Mumbai", "+91"),
]

BANKS = ["Emirates NBD", "ADCB", "Mashreq Bank", "QNB", "HDFC Bank", "ICICI Bank", "SBI"]


def hash_password(value: str) -> str:
    """Create a deterministic demo password hash.

    This generator is for synthetic development data only. Production passwords
    must be created by the application's real password-hashing service.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def random_phone(country_code: str) -> str:
    digits = 9 if country_code in {"+971", "+974", "+966"} else 10
    return f"{country_code}{random.randint(10 ** (digits - 1), (10 ** digits) - 1)}"


def random_secret(length: int = 32) -> str:
    return secrets.token_hex(length // 2)


def clear_users_agents() -> None:
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        conn.execute(text("TRUNCATE TABLE agents"))
        conn.execute(text("TRUNCATE TABLE users"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def insert_user(conn, *, name: str, email: str, phone: str, created_at: datetime, is_admin: bool) -> int:
    two_factor_enabled = is_admin or random.random() < 0.12
    two_factor_confirmed_at = created_at + timedelta(days=random.randint(0, 15)) if two_factor_enabled else None
    google2fa_enabled_at = two_factor_confirmed_at if two_factor_enabled else None

    result = conn.execute(
        text(
            """
            INSERT INTO users (
                name,
                email,
                phone,
                password,
                two_factor_secret,
                two_factor_recovery_codes,
                two_factor_confirmed_at,
                google2fa_secret,
                google2fa_enabled_at,
                is_active,
                email_verified_at,
                remember_token,
                created_at,
                updated_at
            ) VALUES (
                :name,
                :email,
                :phone,
                :password,
                :two_factor_secret,
                :two_factor_recovery_codes,
                :two_factor_confirmed_at,
                :google2fa_secret,
                :google2fa_enabled_at,
                :is_active,
                :email_verified_at,
                :remember_token,
                :created_at,
                :updated_at
            )
            """
        ),
        {
            "name": name,
            "email": email,
            "phone": phone,
            "password": hash_password(DEFAULT_PASSWORD),
            "two_factor_secret": random_secret() if two_factor_enabled else None,
            "two_factor_recovery_codes": json.dumps([random_secret(12) for _ in range(8)]) if two_factor_enabled else None,
            "two_factor_confirmed_at": two_factor_confirmed_at,
            "google2fa_secret": random_secret() if two_factor_enabled else None,
            "google2fa_enabled_at": google2fa_enabled_at,
            "is_active": 1,
            "email_verified_at": created_at + timedelta(minutes=random.randint(5, 720)),
            "remember_token": None,
            "created_at": created_at,
            "updated_at": created_at,
        },
    )
    return int(result.lastrowid)


def insert_agent(conn, *, index: int, user_id: int, created_at: datetime) -> int:
    country, state, city, province, country_code = random.choice(LOCATION_DATA)
    company = fake.unique.company()
    slug = f"agent{index:04d}"
    approval_status = random.choice(APPROVAL_STATUSES)
    active = 1 if approval_status == "APPROVED" else random.choice([0, 1])
    annual_volume = random.randint(100_000, 15_000_000)

    result = conn.execute(
        text(
            """
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
            ) VALUES (
                :user_id,
                :parent_id,
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
                :cr_copy_path,
                :vat_certificate_path,
                :authorized_id_path,
                :company_stamp_path,
                :scanned_signature_path,
                :signature_data,
                :onboarding_submitted_at,
                :is_active,
                :approval_status,
                :created_at,
                :updated_at
            )
            """
        ),
        {
            "user_id": user_id,
            "parent_id": None,
            "email": f"{slug}@afinetripdemo.com",
            "establishment_name": company,
            "director_name": fake.name(),
            "nature_of_business": random.choice([
                "Travel and airline ticketing services",
                "Corporate travel management",
                "Tour operation and holiday packages",
                "Online flight and hotel distribution",
            ]),
            "cr_number": f"CR-{index:06d}-{random.randint(1000, 9999)}",
            "cr_expiry_date": datetime.now().date() + timedelta(days=random.randint(90, 1200)),
            "vat_number": f"VAT-{random.randint(100000000, 999999999)}",
            "street": fake.street_address(),
            "country": country,
            "state": state,
            "city": city,
            "province": province,
            "office_telephone": random_phone(country_code),
            "office_email": f"office.{slug}@afinetripdemo.com",
            "bank_name": random.choice(BANKS),
            "bank_branch": city,
            "account_number": str(random.randint(10**11, (10**12) - 1)),
            "iban": f"AE{random.randint(10**21, (10**22) - 1)}",
            "manager_name": fake.name(),
            "manager_email": f"manager.{slug}@afinetripdemo.com",
            "manager_mobile": random_phone(country_code),
            "finance_name": fake.name(),
            "finance_email": f"finance.{slug}@afinetripdemo.com",
            "finance_mobile": random_phone(country_code),
            "ticketing_contact": random_phone(country_code),
            "holidays_contact": random_phone(country_code),
            "annual_volume_words": f"Approximately {annual_volume:,} in annual booking volume",
            "annual_volume_figures": annual_volume,
            "agent_type": random.choice(AGENT_TYPES),
            "business_type": random.choice(BUSINESS_TYPES),
            "recommended_by": random.choice(["Sales Team", "Referral", "Online Lead", "Corporate Network"]),
            "cr_copy_path": f"demo/agents/{index}/cr_copy.pdf",
            "vat_certificate_path": f"demo/agents/{index}/vat_certificate.pdf",
            "authorized_id_path": f"demo/agents/{index}/authorized_id.pdf",
            "company_stamp_path": f"demo/agents/{index}/company_stamp.png",
            "scanned_signature_path": f"demo/agents/{index}/signature.png",
            "signature_data": None,
            "onboarding_submitted_at": created_at + timedelta(hours=random.randint(1, 48)),
            "is_active": active,
            "approval_status": approval_status,
            "created_at": created_at,
            "updated_at": created_at + timedelta(days=random.randint(0, 30)),
        },
    )
    return int(result.lastrowid)


def assign_parent_agents(conn, agent_ids: list[int]) -> None:
    parent_candidates = agent_ids[: max(25, len(agent_ids) // 10)]
    for agent_id in agent_ids:
        if agent_id in parent_candidates or random.random() >= 0.28:
            continue
        parent_id = random.choice(parent_candidates)
        if parent_id != agent_id:
            conn.execute(
                text("UPDATE agents SET parent_id = :parent_id WHERE id = :agent_id"),
                {"parent_id": parent_id, "agent_id": agent_id},
            )


def generate_users_agents() -> None:
    logger.info("Clearing old users and agents...")
    clear_users_agents()

    with engine.begin() as conn:
        logger.info("Creating %s admin users...", TOTAL_ADMINS)
        for index in range(1, TOTAL_ADMINS + 1):
            created_at = datetime.now() - timedelta(days=random.randint(400, 900))
            insert_user(
                conn,
                name=f"System Admin {index}",
                email=f"admin{index}@afinetripdemo.com",
                phone=f"+9715000000{index}",
                created_at=created_at,
                is_admin=True,
            )

        logger.info("Creating %s agent users and agents...", TOTAL_AGENTS)
        agent_ids: list[int] = []
        for index in range(1, TOTAL_AGENTS + 1):
            created_at = datetime.now() - timedelta(days=random.randint(30, 730))
            user_id = insert_user(
                conn,
                name=fake.name(),
                email=f"user{index:04d}@afinetripdemo.com",
                phone=random_phone(random.choice(["+971", "+974", "+966", "+91"])),
                created_at=created_at,
                is_admin=False,
            )
            agent_ids.append(insert_agent(conn, index=index, user_id=user_id, created_at=created_at))

        assign_parent_agents(conn, agent_ids)

    logger.info("Generation completed successfully.")
    logger.info("Admin users created: %s (expected IDs 1-3 after truncate)", TOTAL_ADMINS)
    logger.info("Agent users created: %s", TOTAL_AGENTS)
    logger.info("Agents created: %s", TOTAL_AGENTS)
    logger.info("Relationship: agents.user_id references users.id")


if __name__ == "__main__":
    generate_users_agents()