"""
Seed script for supplier reference data.

Run with:
    python -m app.data_generation.seed_suppliers

Safe to run multiple times: existing suppliers (matched by `code`)
are left untouched, only missing ones are inserted.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.data_generation.models import Supplier
from app.infra.database import engine
from app.observability.logger import setup_logger

logger = setup_logger(__name__)

SUPPLIER_SEED_DATA = [
    {"code": "SUP-AMADEUS", "name": "Amadeus GDS", "is_active": 1, "health_status": "HEALTHY"},
    {"code": "SUP-SABRE", "name": "Sabre GDS", "is_active": 1, "health_status": "HEALTHY"},
    {"code": "SUP-TRAVELPORT", "name": "Travelport GDS", "is_active": 1, "health_status": "HEALTHY"},
    {"code": "SUP-EMIRATES", "name": "Emirates Direct Connect", "is_active": 1, "health_status": "HEALTHY"},
    {"code": "SUP-QATAR", "name": "Qatar Airways Direct Connect", "is_active": 1, "health_status": "HEALTHY"},
    {"code": "SUP-ETIHAD", "name": "Etihad Direct Connect", "is_active": 1, "health_status": "HEALTHY"},
    {"code": "SUP-FLYDUBAI", "name": "flydubai Direct Connect", "is_active": 1, "health_status": "HEALTHY"},
    {"code": "SUP-AIRARABIA", "name": "Air Arabia Direct Connect", "is_active": 1, "health_status": "HEALTHY"},
]


def seed_suppliers() -> None:
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        existing_codes = {row[0] for row in session.query(Supplier.code).all()}

        new_suppliers = [
            Supplier(
                code=entry["code"],
                name=entry["name"],
                is_active=entry["is_active"],
                health_status=entry["health_status"],
                created_at=now,
                updated_at=now,
            )
            for entry in SUPPLIER_SEED_DATA
            if entry["code"] not in existing_codes
        ]

        if not new_suppliers:
            logger.info("All %d seed suppliers already exist. Nothing to insert.", len(SUPPLIER_SEED_DATA))
            return

        skipped = len(SUPPLIER_SEED_DATA) - len(new_suppliers)
        session.add_all(new_suppliers)
        session.commit()
        logger.info("Inserted %d new seed suppliers (skipped %d already present).",
                     len(new_suppliers), skipped)


if __name__ == "__main__":
    seed_suppliers()