"""Seed canonical entities into admin SQLite DB from SSOT_Build HLT JSONs.

Wipes everything first. 0 HLTs.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from admin.db import init_db, SessionLocal, Horse, Owner, Trainer, Lease, HLT

SSOT_ROOT = Path("/home/evo/workspace/projects/SSOT_Build/data")

HLT_FILES = [
    "hlt/LSE-001.json",
    "hlt/LSE-002.json",
    "hlt/LSE-003.json",
    "hlt/LSE-004.json",
]

OWNER_FILES = [
    "owners/OWN-001.json",
    "owners/OWN-002.json",
]

TRAINER_FILES = [
    "trainers/wexford-stables.json",
    "trainers/stephen-gray-racing.json",
]


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _wipe(db):
    from sqlalchemy import text
    for tbl in ["documents", "hlts", "leases", "horses", "owners", "trainers"]:
        db.execute(text(f"DELETE FROM {tbl}"))
    db.commit()


def seed():
    init_db()
    db = SessionLocal()
    try:
        _wipe(db)
        print("Wiped all tables.")

        # ─── Horses ───────────────────────────────────────────────────────
        seen_chips = set()
        for fname in HLT_FILES:
            path = SSOT_ROOT / fname
            if not path.exists():
                print(f"  SKIP: {fname} not found")
                continue
            data = _load(path)
            chip = data.get("horse_microchip")
            if not chip or chip in seen_chips:
                continue
            seen_chips.add(chip)
            name = data.get("horse_name", "")
            year = data.get("horse_year", "")
            full_name = f"{name} (NZ) {year}" if year else name
            h = Horse(
                microchip=chip,
                name=full_name,
                name_slug=f"{name}-{year}".replace(" ", "-").lower() if year else name.replace(" ", "-").lower(),
                sex="",
                colour="",
                status="active",
            )
            db.merge(h)
            print(f"  Horse: {full_name} ({chip})")

        # ─── Owners ───────────────────────────────────────────────────────
        for fname in OWNER_FILES:
            path = SSOT_ROOT / fname
            if not path.exists():
                print(f"  SKIP: {fname} not found")
                continue
            data = _load(path)
            o = Owner(
                id=data.get("owner_id", ""),
                name=data.get("owner_name", ""),
                email=data.get("email"),
                phone=data.get("phone"),
                entity_type=data.get("entity_type", "individual"),
                contact_name=data.get("contact_name"),
                website=data.get("website"),
            )
            db.merge(o)
            print(f"  Owner: {o.name} ({o.id})")

        # ─── Trainers ─────────────────────────────────────────────────────
        for fname in TRAINER_FILES:
            path = SSOT_ROOT / fname
            if not path.exists():
                print(f"  SKIP: {fname} not found")
                continue
            data = _load(path)
            t = Trainer(
                id=data.get("trainer_id", ""),
                name=data.get("trainer_name", ""),
                stable_name=data.get("stable_name"),
                location=data.get("location"),
                email=None,
                phone=None,
                bio=data.get("bio"),
            )
            db.merge(t)
            print(f"  Trainer: {t.name} ({t.id})")

        db.commit()

        hc = db.query(Horse).count()
        oc = db.query(Owner).count()
        tc = db.query(Trainer).count()
        lc = db.query(Lease).count()
        hltc = db.query(HLT).count()
        print(f"\nDone. Horses: {hc}, Owners: {oc}, Trainers: {tc}, Leases: {lc}, HLTs: {hltc}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
