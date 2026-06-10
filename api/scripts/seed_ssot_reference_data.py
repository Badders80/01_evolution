#!/usr/bin/env python3
"""
Seed SSOT reference data from SSOT_Build into Mission Control SQLite.
Creates rock-solid canonical records for owners, trainers, and governing bodies.
"""

import sys
import json
sys.path.insert(0, '/home/evo/evo_01/01_evolution/api')

from admin.db import SessionLocal, Owner, Trainer, GoverningBody

# Source data from SSOT_Build
SSOT_BUILD_PATH = "/home/evo/workspace/projects/SSOT_Build/dist/intake/v0.1/seed.json"


def load_ssot_data():
    """Load canonical data from SSOT_Build seed.json."""
    with open(SSOT_BUILD_PATH, 'r') as f:
        return json.load(f)


def seed_governing_bodies(session, bodies):
    """Seed governing bodies."""
    print("\n🏛️  Governing Bodies:")
    for body_data in bodies:
        existing = session.query(GoverningBody).filter_by(governing_body_code=body_data["governing_body_code"]).first()
        if existing:
            print(f"  ⏭️  {body_data['governing_body_code']} already exists")
            continue
        
        body = GoverningBody(
            governing_body_code=body_data["governing_body_code"],
            governing_body_name=body_data["governing_body_name"],
            website=body_data.get("website"),
            status=body_data.get("status", "active"),
            notes="Seeded from SSOT_Build canonical data",
        )
        session.add(body)
        print(f"  ✅ {body_data['governing_body_name']} ({body_data['governing_body_code']})")


def seed_trainers(session, trainers):
    """Seed trainers/stables."""
    print("\n🏇 Trainers / Stables:")
    for trainer_data in trainers:
        existing = session.query(Trainer).filter_by(id=trainer_data["trainer_id"]).first()
        if existing:
            print(f"  ⏭️  {trainer_data['trainer_name']} already exists")
            continue
        
        # Extract social links
        social = trainer_data.get("social_links", {})
        
        trainer = Trainer(
            id=trainer_data["trainer_id"],
            name=trainer_data["trainer_name"],
            stable_name=trainer_data.get("stable_name"),
            location=trainer_data.get("location"),
            email=trainer_data.get("email"),
            phone=trainer_data.get("phone"),
            website=trainer_data.get("website"),
            bio=trainer_data.get("bio"),
            contact_name=trainer_data.get("contact_name"),
            profile_status=trainer_data.get("profile_status", "active"),
        )
        session.add(trainer)
        print(f"  ✅ {trainer_data['trainer_name']} ({trainer_data.get('stable_name', 'N/A')})")


def seed_owners(session, owners):
    """Seed owners."""
    print("\n👥 Owners:")
    for owner_data in owners:
        existing = session.query(Owner).filter_by(id=owner_data["owner_id"]).first()
        if existing:
            print(f"  ⏭️  {owner_data['owner_name']} already exists")
            continue
        
        owner = Owner(
            id=owner_data["owner_id"],
            name=owner_data["owner_name"],
            email=owner_data.get("email"),
            phone=owner_data.get("phone"),
            entity_type=owner_data.get("entity_type"),
            contact_name=owner_data.get("contact_name"),
            website=owner_data.get("website"),
            profile_status=owner_data.get("profile_status", "active"),
        )
        session.add(owner)
        print(f"  ✅ {owner_data['owner_name']} ({owner_data['entity_type']})")


def main():
    print("=" * 60)
    print("SSOT Reference Data Seeder")
    print("=" * 60)
    print(f"\nLoading data from: {SSOT_BUILD_PATH}")
    
    data = load_ssot_data()
    
    session = SessionLocal()
    try:
        # Seed in dependency order
        seed_governing_bodies(session, data.get("governingBodies", []))
        seed_trainers(session, data.get("trainers", []))
        seed_owners(session, data.get("owners", []))
        
        session.commit()
        print("\n🎉 Successfully seeded SSOT reference data into Mission Control")
        print("=" * 60)
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
