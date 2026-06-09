"""Seed admin SQLite with full canonical data from SSOT_Build.

Sources:
- Horses: HLT JSONs + i-stole-a-manolo.json + seed_canonical_entities.py
- Owners: OWN-001.json, OWN-002.json
- Trainers: wexford-stables.json, stephen-gray-racing.json

Wipes everything. 0 HLTs. 0 leases.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from admin.db import init_db, SessionLocal, Horse, Owner, Trainer, Lease, HLT, GoverningBody


def seed():
    init_db()
    db = SessionLocal()
    try:
        from sqlalchemy import text
        for tbl in ["documents", "hlts", "leases", "horses", "owners", "trainers", "governing_bodies"]:
            db.execute(text(f"DELETE FROM {tbl}"))
        db.commit()
        print("Wiped all tables.")

        # ─── Horses (full data from SSOT_Build canonical records) ─────────
        horses = [
            {
                "microchip": "985125000126713",
                "name": "First Gear (NZ) 2021",
                "name_slug": "first-gear-nz-2021",
                "foaling_date": "2021-09-15",
                "sex": "filly",
                "colour": "Bay",
                "sire_name": "Contributer (IRE)",
                "dam_name": "Whiffle (USA)",
                "breeder": None,
                "status": "active",
                "loveracing_id": 428364,
                "breeding_url": "https://loveracing.nz/Breeding/428364/First-Gear-NZ-2021.aspx",
            },
            {
                "microchip": "985125000126462",
                "name": "Prudentia (NZ) 2021",
                "name_slug": "prudentia-nz-2021",
                "foaling_date": "2021-09-15",
                "sex": "filly",
                "colour": "Bay",
                "sire_name": "Proisir",
                "dam_name": "Prudent",
                "breeder": "B.A.X Bloodstock Ltd",
                "status": "active",
                "loveracing_id": 427416,
                "breeding_url": "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx",
            },
            {
                "microchip": "985125000139165",
                "name": "Hottathanafantasy (NZ) 2023",
                "name_slug": "hottathanafantasy-nz-2023",
                "foaling_date": "2023-08-30",
                "sex": "filly",
                "colour": "Bay",
                "sire_name": "Contributer (IRE)",
                "dam_name": "Whiffle (USA)",
                "breeder": None,
                "status": "active",
                "loveracing_id": 452052,
                "breeding_url": "https://loveracing.nz/Breeding/452052/Hottathanafantasy-NZ-2023.aspx",
            },
            {
                "microchip": "985125000139219",
                "name": "I Stole A Manolo (NZ) 2023",
                "name_slug": "i-stole-a-manolo-nz-2023",
                "foaling_date": "2023-08-30",
                "sex": "filly",
                "colour": "Bay",
                "sire_name": "Satono Aladdin (JPN)",
                "dam_name": "Canuhandleajandal (NZ)",
                "breeder": None,
                "status": "active",
                "loveracing_id": 451442,
                "breeding_url": "https://loveracing.nz/Breeding/451442/I-Stole-A-Manolo-NZ-2023.aspx",
            },
        ]
        for h in horses:
            db.merge(Horse(**h))
            print(f"  Horse: {h['name']} ({h['microchip']})")

        # ─── Owners (from OWN-001.json, OWN-002.json) ────────────────────
        owners = [
            {
                "id": "OWN-001",
                "name": "B.A.X Bloodstock Achieving Xcellence Limited",
                "email": "baxltd@yahoo.com",
                "phone": "+64 21 557 045",
                "entity_type": "company",
                "contact_name": "Kylie Bax",
                "website": "https://www.baxltd.com",
            },
            {
                "id": "OWN-002",
                "name": "Stephen Gray Racing",
                "email": "stephen@stephengrayracing.com",
                "phone": "+64 21 933 183",
                "entity_type": "company",
                "contact_name": "Stephen Gray",
                "website": "https://www.stephengrayracing.com",
            },
        ]
        for o in owners:
            db.merge(Owner(**o))
            print(f"  Owner: {o['name']} ({o['id']})")

        # ─── Governing Bodies (from HLT canonical data) ────────────────────
        governing_bodies = [
            {
                "governing_body_code": "NZTR",
                "governing_body_name": "New Zealand Thoroughbred Racing",
                "website": "https://www.nzracing.co.nz",
                "status": "active",
                "notes": "Seeded from SSOT_Build LSE-001.json",
            },
        ]
        for gb in governing_bodies:
            db.merge(GoverningBody(**gb))
            print(f"  Governing Body: {gb['governing_body_name']} ({gb['governing_body_code']})")

        # ─── Trainers (from wexford-stables.json, stephen-gray-racing.json) ─
        trainers = [
            {
                "id": "TRN-001",
                "name": "Wexford Stables",
                "stable_name": "Wexford Stables",
                "location": "Matamata, New Zealand",
                "email": "info@wexfordstables.co.nz",
                "phone": "+64 7 888 7371",
                "contact_name": "Andrew Scott",
                "website": "https://www.wexfordstables.co.nz",
                "bio": "Wexford Stables is one of New Zealand's most iconic racing operations, established in 1961 by Hall of Fame trainer Dave O'Sullivan. Now led by Lance O'Sullivan ONZM and Andrew Scott, the stable continues a legacy of excellence from its world-class training facility in Matamata.",
            },
            {
                "id": "TRN-002",
                "name": "Stephen Gray",
                "stable_name": "Copper Belt Lodge",
                "location": "Cambridge, New Zealand",
                "email": "stephen@stephengrayracing.com",
                "phone": "+64 21 933 183",
                "contact_name": "Stephen Gray",
                "website": "https://www.stephengrayracing.com",
                "bio": "Stephen Gray operates Copper Belt Lodge, a boutique training facility based in Cambridge in the heart of New Zealand's Waikato thoroughbred country. Known for his patient, horse-first approach.",
            },
        ]
        for t in trainers:
            db.merge(Trainer(**t))
            print(f"  Trainer: {t['name']} ({t['id']})")

        db.commit()

        hc = db.query(Horse).count()
        oc = db.query(Owner).count()
        tc = db.query(Trainer).count()
        lc = db.query(Lease).count()
        hltc = db.query(HLT).count()
        gc = db.query(GoverningBody).count()
        print(f"\nDone. Horses: {hc}, Owners: {oc}, Trainers: {tc}, Governing Bodies: {gc}, Leases: {lc}, HLTs: {hltc}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
