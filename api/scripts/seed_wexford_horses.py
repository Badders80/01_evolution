#!/usr/bin/env python3
"""
Seed the 4 Wexford Stables horses into Mission Control SQLite database.
"""

import sys
sys.path.insert(0, '/home/evo/evo_01/01_evolution/api')

from admin.db import SessionLocal, Horse, Trainer

# Horse data scraped from loveracing.nz
HORSES = [
    {
        "microchip": "985125000126462",
        "name": "Prudentia",
        "name_slug": "prudentia-nz-2021",
        "foaling_date": "2021-11-13",
        "sex": "Mare",
        "colour": "Bay",
        "sire_name": "Proisir",
        "dam_name": "Little Bit Irish",
        "breeder": "Goldeye Trust",
        "loveracing_id": 427416,
        "breeding_url": "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx",
    },
    {
        "microchip": "985125000139165",
        "name": "Hottathanafantasy",
        "name_slug": "hottathanafantasy-nz-2023",
        "foaling_date": "2023-10-24",
        "sex": "Filly",
        "colour": "Bay",
        "sire_name": "Contributer",
        "dam_name": "Whiffle",
        "breeder": "Goldeye Trust",
        "loveracing_id": 452052,
        "breeding_url": "https://loveracing.nz/Breeding/452052/Hottathanafantasy-NZ-2023.aspx",
    },
    {
        "microchip": "985125000139219",
        "name": "I Stole A Manolo",
        "name_slug": "i-stole-a-manolo-nz-2023",
        "foaling_date": "2023-08-30",
        "sex": "Filly",
        "colour": "Bay",
        "sire_name": "Satono Aladdin",
        "dam_name": "Canuhandleajandal",
        "breeder": "Goldeye Trust",
        "loveracing_id": 451442,
        "breeding_url": "https://loveracing.nz/Breeding/451442/I-Stole-A-Manolo-NZ-2023.aspx",
    },
    {
        "microchip": "985125000126713",
        "name": "First Gear",
        "name_slug": "first-gear-nz-2021",
        "foaling_date": "2021-10-02",
        "sex": "Gelding",
        "colour": "Bay",
        "sire_name": "Derryn",
        "dam_name": "A'Guin Ace",
        "breeder": "M & W Rose",
        "loveracing_id": 428364,
        "breeding_url": "https://loveracing.nz/Breeding/428364/First-Gear-NZ-2021.aspx",
    },
]


def seed_horses():
    session = SessionLocal()
    try:
        for horse_data in HORSES:
            # Check if horse already exists
            existing = session.query(Horse).filter_by(microchip=horse_data["microchip"]).first()
            if existing:
                print(f"⏭️  {horse_data['name']} already exists (microchip: {horse_data['microchip']})")
                continue
            
            # Create new horse
            horse = Horse(**horse_data)
            session.add(horse)
            print(f"✅ Added {horse_data['name']} ({horse_data['sex']}, {horse_data['colour']}) - Microchip: {horse_data['microchip']}")
        
        session.commit()
        print(f"\n🎉 Successfully seeded {len(HORSES)} horses into Mission Control database")
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_horses()
