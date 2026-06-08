"""
HLT Mission Control — SQLite persistence layer.

SQLAlchemy ORM models that mirror the existing Pydantic models
in models/__init__.py for local dev use.
"""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

# Path relative to this file → admin/ssot_local.db
DB_PATH = Path(__file__).parent / "ssot_local.db"
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=ENGINE)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Models ───────────────────────────────────────────────────────────────────

from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey


class Horse(Base):
    __tablename__ = "horses"

    microchip = Column(String(15), primary_key=True)
    name = Column(Text, nullable=False)
    name_slug = Column(Text)
    foaling_date = Column(Text)          # ISO date
    sex = Column(Text)
    colour = Column(Text)
    sire_name = Column(Text)
    dam_name = Column(Text)
    breeder = Column(Text)
    trainer_id = Column(Text, nullable=True)
    status = Column(Text, default="active")
    loveracing_id = Column(Integer, nullable=True)
    breeding_url = Column(Text)
    created_at = Column(Text, default=utc_now)
    updated_at = Column(Text, default=utc_now, onupdate=utc_now)


class Owner(Base):
    __tablename__ = "owners"

    id = Column(String(32), primary_key=True)
    name = Column(Text, nullable=False)
    email = Column(Text)
    phone = Column(Text)
    entity_type = Column(Text)
    contact_name = Column(Text)
    website = Column(Text)
    profile_status = Column(Text, default="active")
    address = Column(Text)
    created_at = Column(Text, default=utc_now)
    updated_at = Column(Text, default=utc_now, onupdate=utc_now)


class Trainer(Base):
    __tablename__ = "trainers"

    id = Column(String(32), primary_key=True)
    name = Column(Text, nullable=False)
    stable_name = Column(Text)
    location = Column(Text)
    email = Column(Text)
    phone = Column(Text)
    nztr_license_number = Column(Text)
    bio = Column(Text)
    profile_status = Column(Text, default="active")
    created_at = Column(Text, default=utc_now)
    updated_at = Column(Text, default=utc_now, onupdate=utc_now)


class Lease(Base):
    __tablename__ = "leases"

    lease_id = Column(String(32), primary_key=True)
    horse_id = Column(String(15), ForeignKey("horses.microchip"), nullable=False)
    start_date = Column(Text)
    end_date = Column(Text)
    duration_months = Column(Integer)
    percent_leased = Column(Float)
    token_count = Column(Integer)
    min_unit_size = Column(Float)
    price_basis = Column(Text)
    price_period = Column(Text)
    price_amount = Column(Float)
    price_per_1pct_per_month = Column(Float)
    price_per_1pct_per_year = Column(Float)
    monthly_stake_price = Column(Float)
    annual_stake_price = Column(Float)
    total_issuance_value_nzd = Column(Float)
    percent_per_token = Column(Float)
    token_price_nzd = Column(Float)
    investor_share_percent = Column(Float)
    owner_share_percent = Column(Float)
    platform_fee_percent = Column(Float, default=0)
    lease_status = Column(Text, default="draft")
    created_at = Column(Text, default=utc_now)
    updated_at = Column(Text, default=utc_now, onupdate=utc_now)


class HLT(Base):
    __tablename__ = "hlts"

    id = Column(String(32), primary_key=True)
    horse_microchip = Column(String(15), ForeignKey("horses.microchip"), nullable=False)
    owner_id = Column(String(32), ForeignKey("owners.id"), nullable=False)
    trainer_id = Column(String(32), ForeignKey("trainers.id"), nullable=False)
    lease_id = Column(String(32), ForeignKey("leases.lease_id"), nullable=False)
    status = Column(Text, default="draft")
    term_sheet_status = Column(Text, default="pending")
    pds_status = Column(Text, default="pending")
    sa_status = Column(Text, default="pending")
    created_at = Column(Text, default=utc_now)
    updated_at = Column(Text, default=utc_now, onupdate=utc_now)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(32), primary_key=True)
    hlt_id = Column(String(32), ForeignKey("hlts.id"), nullable=False)
    doc_type = Column(Text)   # term_sheet, pds, sa, photo
    file_path = Column(Text)
    file_name = Column(Text)
    mime_type = Column(Text)
    created_at = Column(Text, default=utc_now)


# ─── Init ─────────────────────────────────────────────────────────────────────

def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=ENGINE)


# Enforce foreign keys on every connection
@event.listens_for(ENGINE, "connect")
def _fk_pragma(dbapi_conn, connection_record):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")
