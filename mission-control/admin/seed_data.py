#!/usr/bin/env python3
"""
Seed script to populate the new build database with the exact data from the old SSOT_Build seed.json
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin.db import SessionLocal, Horse, Owner, Trainer, GoverningBody, Lease, HLT, Document, init_db
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def seed_database():
    """Populate database with the 4 core horses, trainers, owners, governing bodies, and leases"""
    init_db()
    db = SessionLocal()

    try:
        # Clear existing data (optional - comment out if you want to keep existing)
        print("Clearing existing data...")
        db.query(HLT).delete()
        db.query(Lease).delete()
        db.query(Document).delete()
        db.query(Horse).delete()
        db.query(Owner).delete()
        db.query(Trainer).delete()
        db.query(GoverningBody).delete()
        db.commit()

        # ─── Governing Bodies ─────────────────────────────────────────────────────
        print("Seeding governing bodies...")
        nztr = GoverningBody(
            governing_body_code="NZTR",
            governing_body_name="New Zealand Thoroughbred Racing",
            website="https://www.nztr.co.nz",
            status="active",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        drc = GoverningBody(
            governing_body_code="DRC",
            governing_body_name="Dubai Racing Club",
            website="https://www.dubairacingclub.com",
            status="pipeline",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add_all([nztr, drc])
        db.commit()

        # ─── Trainers ────────────────────────────────────────────────────────────
        print("Seeding trainers...")
        wexford = Trainer(
            id="TRN-001",
            name="Wexford Stables",
            stable_name="Wexford Stables",
            contact_name="Andrew Scott",
            phone="+64 27 360 2276",
            email="info@wexfordstables.co.nz",
            website="https://www.wexfordstables.co.nz",
            nztr_license_number="",
            bio="Loaded from SSOT_Build.xlsx trainer profile.",
            profile_status="active",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        stephen_gray = Trainer(
            id="TRN-002",
            name="Stephen Gray Racing",
            stable_name="Copper Belt Lodge",
            contact_name="Stephen Gray",
            phone="+64 21 933 183",
            email="stephen@stephengrayracing.com",
            website="https://www.stephengrayracing.com",
            nztr_license_number="",
            bio="Loaded from SSOT_Build.xlsx trainer profile; name normalized to Gray per horse docs.",
            profile_status="active",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add_all([wexford, stephen_gray])
        db.commit()

        # ─── Owners ──────────────────────────────────────────────────────────────
        print("Seeding owners...")
        bax = Owner(
            id="OWN-001",
            name="B.A.X Bloodstock Achieving Xcellence Limited",
            entity_type="company",
            contact_name="Kylie Bax",
            phone="+64 21 557 045",
            email="baxltd@yahoo.com",
            website="https://www.baxltd.com",
            profile_status="active",
            address="",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        stephen_gray_owner = Owner(
            id="OWN-002",
            name="Stephen Gray Racing",
            entity_type="company",
            contact_name="Stephen Gray",
            phone="+64 21 933 183",
            email="stephen@stephengrayracing.com",
            website="https://www.stephengrayracing.com",
            profile_status="active",
            address="",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add_all([bax, stephen_gray_owner])
        db.commit()

        # ─── Horses ──────────────────────────────────────────────────────────────
        print("Seeding horses...")
        first_gear = Horse(
            microchip="985125000126713",
            name="First Gear",
            name_slug="first-gear",
            foaling_date="2021-10-02",
            sex="Gelding",
            colour="Bay",
            sire_name="Derryn (AUS)",
            dam_name="A'Guin Ace (NZ)",
            breeder="",
            trainer_id="TRN-002",
            status="active",
            loveracing_id=428364,
            breeding_url="https://loveracing.nz/Breeding/428364/First-Gear-NZ-2021.aspx",
            performance_profile_url="https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?DisplayContext=Modal&HorseID=428364",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        prudentia = Horse(
            microchip="985125000126462",
            name="Prudentia",
            name_slug="prudentia",
            foaling_date="2021-11-13",
            sex="Mare",
            colour="Bay",
            sire_name="Proisir (AUS)",
            dam_name="Little Bit Irish (NZ)",
            breeder="",
            trainer_id="TRN-001",
            status="active",
            loveracing_id=427416,
            breeding_url="https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx",
            performance_profile_url="https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?DisplayContext=Modal&HorseID=427416",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        hottathanafantasy = Horse(
            microchip="985125000139165",
            name="Hottathanafantasy",
            name_slug="hottathanafantasy",
            foaling_date="2023-10-24",
            sex="Filly",
            colour="Bay",
            sire_name="Contributer (IRE)",
            dam_name="Whiffle (USA)",
            breeder="",
            trainer_id="TRN-001",
            status="active",
            loveracing_id=452052,
            breeding_url="https://loveracing.nz/Breeding/452052/Hottathanafantasy-NZ-2023.aspx",
            performance_profile_url="https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?DisplayContext=Modal&HorseID=452052",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        i_stole_a_manolo = Horse(
            microchip="985125000139219",
            name="I Stole A Manolo",
            name_slug="i-stole-a-manolo",
            foaling_date="2023-08-30",
            sex="Filly",
            colour="Bay",
            sire_name="Satono Aladdin (JPN)",
            dam_name="Canuhandleajandal (NZ)",
            breeder="",
            trainer_id="TRN-001",
            status="active",
            loveracing_id=451442,
            breeding_url="https://loveracing.nz/Breeding/451442/I-Stole-A-Manolo-NZ-2023.aspx",
            performance_profile_url="https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?DisplayContext=Modal&HorseID=451442",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add_all([first_gear, prudentia, hottathanafantasy, i_stole_a_manolo])
        db.commit()

        # ─── Leases ──────────────────────────────────────────────────────────────
        print("Seeding leases...")
        lse001 = Lease(
            lease_id="LSE-001",
            horse_id="985125000126713",
            start_date="2025-07-01",
            end_date="2026-06-30",
            duration_months=12,
            percent_leased=10.0,
            token_count=20,
            min_unit_size=0.5,
            price_basis="per_1pct",
            price_period="month",
            price_amount=40.0,
            price_per_1pct_per_month=40.0,
            price_per_1pct_per_year=480.0,
            monthly_stake_price=400.0,
            annual_stake_price=4800.0,
            total_issuance_value_nzd=4800.0,
            percent_per_token=0.5,
            token_price_nzd=240.0,
            investor_share_percent=80.0,
            owner_share_percent=20.0,
            platform_fee_percent=0.0,
            lease_status="complete",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        lse002 = Lease(
            lease_id="LSE-002",
            horse_id="985125000126462",
            start_date="2026-01-01",
            end_date="2027-06-30",
            duration_months=18,
            percent_leased=5.0,
            token_count=20,
            min_unit_size=0.25,
            price_basis="per_1pct",
            price_period="month",
            price_amount=65.0,
            price_per_1pct_per_month=65.0,
            price_per_1pct_per_year=780.0,
            monthly_stake_price=325.0,
            annual_stake_price=3900.0,
            total_issuance_value_nzd=5850.0,
            percent_per_token=0.25,
            token_price_nzd=292.5,
            investor_share_percent=75.0,
            owner_share_percent=25.0,
            platform_fee_percent=0.0,
            lease_status="draft",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        lse003 = Lease(
            lease_id="LSE-003",
            horse_id="985125000139165",
            start_date="2025-03-01",
            end_date="2026-06-30",
            duration_months=16,
            percent_leased=5.0,
            token_count=20,
            min_unit_size=0.25,
            price_basis="per_1pct",
            price_period="month",
            price_amount=70.0,
            price_per_1pct_per_month=70.0,
            price_per_1pct_per_year=840.0,
            monthly_stake_price=350.0,
            annual_stake_price=4200.0,
            total_issuance_value_nzd=5600.0,
            percent_per_token=0.25,
            token_price_nzd=280.0,
            investor_share_percent=75.0,
            owner_share_percent=25.0,
            platform_fee_percent=0.0,
            lease_status="draft",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        lse004 = Lease(
            lease_id="LSE-004",
            horse_id="985125000139219",
            start_date="2026-03-01",
            end_date="2027-06-30",
            duration_months=16,
            percent_leased=5.0,
            token_count=20,
            min_unit_size=0.25,
            price_basis="per_1pct",
            price_period="month",
            price_amount=70.0,
            price_per_1pct_per_month=70.0,
            price_per_1pct_per_year=840.0,
            monthly_stake_price=350.0,
            annual_stake_price=4200.0,
            total_issuance_value_nzd=5600.0,
            percent_per_token=0.25,
            token_price_nzd=280.0,
            investor_share_percent=75.0,
            owner_share_percent=25.0,
            platform_fee_percent=0.0,
            lease_status="draft",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add_all([lse001, lse002, lse003, lse004])
        db.commit()

        # ─── HLTs ────────────────────────────────────────────────────────────────
        print("Seeding HLTs...")
        import uuid

        hlt1 = HLT(
            id="HLT-001",
            horse_microchip="985125000126713",
            owner_id="OWN-002",
            trainer_id="TRN-002",
            governing_body_code="NZTR",
            lease_id="LSE-001",
            status="coming_soon",
            term_sheet_status="pending",
            pds_status="pending",
            sa_status="pending",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        hlt2 = HLT(
            id="HLT-002",
            horse_microchip="985125000126462",
            owner_id="OWN-001",
            trainer_id="TRN-001",
            governing_body_code="NZTR",
            lease_id="LSE-002",
            status="coming_soon",
            term_sheet_status="pending",
            pds_status="pending",
            sa_status="pending",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        hlt3 = HLT(
            id="HLT-003",
            horse_microchip="985125000139165",
            owner_id="OWN-001",
            trainer_id="TRN-001",
            governing_body_code="NZTR",
            lease_id="LSE-003",
            status="coming_soon",
            term_sheet_status="pending",
            pds_status="pending",
            sa_status="pending",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        hlt4 = HLT(
            id="HLT-004",
            horse_microchip="985125000139219",
            owner_id="OWN-001",
            trainer_id="TRN-001",
            governing_body_code="NZTR",
            lease_id="LSE-004",
            status="coming_soon",
            term_sheet_status="pending",
            pds_status="pending",
            sa_status="pending",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add_all([hlt1, hlt2, hlt3, hlt4])
        db.commit()

        print("\n✅ Database seeded successfully!")
        print(f"  • 2 Governing Bodies (NZTR, DRC)")
        print(f"  • 2 Trainers (Wexford Stables, Stephen Gray Racing)")
        print(f"  • 2 Owners (B.A.X Bloodstock, Stephen Gray Racing)")
        print(f"  • 4 Horses (First Gear, Prudentia, Hottathanafantasy, I Stole A Manolo)")
        print(f"  • 4 Leases (LSE-001 through LSE-004)")
        print(f"  • 4 HLTs (one per horse)")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()