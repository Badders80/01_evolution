#!/usr/bin/env python3
"""
Seed Canonical Entities into Firestore from SSOT_Build JSON files.

Maps JSON files to Pydantic models and upserts into Firestore with canonical IDs.
Logs what was created vs already existed.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.cloud import firestore

# Add project root to path so `import models` works
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import GoverningBodyCreate, OwnerCreate, TrainerCreate, HLTCreate

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_ROOT = Path("/home/evo/workspace/projects/SSOT_Build/data")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_collection(db: firestore.Client, name: str) -> firestore.CollectionReference:
    return db.collection(name)


def seed_governing_bodies(db: firestore.Client) -> dict[str, str]:
    """Seed governing bodies discovered from HLT JSON files."""
    collection = _ensure_collection(db, "governing_bodies")
    results: dict[str, str] = {}

    # Extract unique governing bodies from all HLT files
    governing_bodies: dict[str, dict[str, Any]] = {}
    for hlt_path in sorted((DATA_ROOT / "hlt").glob("LSE-*.json")):
        data = _load_json(hlt_path)
        code = data.get("governing_body_code")
        name = data.get("governing_body_name")
        if code and name and code not in governing_bodies:
            governing_bodies[code] = {
                "governing_body_code": code,
                "governing_body_name": name,
                "website": None,
                "status": "active",
                "notes": f"Seeded from {hlt_path.name}",
            }

    for code, payload in governing_bodies.items():
        try:
            body = GoverningBodyCreate(**payload)
        except Exception as exc:
            logger.error("Validation failed for governing body %s: %s", code, exc)
            results[code] = "validation_error"
            continue

        doc_ref = collection.document(body.governing_body_code)
        if doc_ref.get().exists:
            logger.info("Governing body %s already exists — skipped", code)
            results[code] = "existed"
            continue

        doc_data = body.model_dump()
        doc_data["id"] = body.governing_body_code
        doc_data["created_at"] = firestore.SERVER_TIMESTAMP
        doc_data["updated_at"] = firestore.SERVER_TIMESTAMP
        doc_ref.set(doc_data)
        logger.info("Governing body %s created", code)
        results[code] = "created"

    return results


def seed_owners(db: firestore.Client) -> dict[str, str]:
    """Seed owners from SSOT_Build owner JSON files with canonical IDs."""
    collection = _ensure_collection(db, "owners")
    results: dict[str, str] = {}
    owners_dir = DATA_ROOT / "owners"
    if not owners_dir.exists():
        logger.warning("Owners directory not found: %s", owners_dir)
        return results

    for path in sorted(owners_dir.glob("OWN-*.json")):
        data = _load_json(path)
        canonical_id = data.get("owner_id")
        if not canonical_id:
            logger.error("Owner %s missing canonical owner_id — skipped", path.name)
            results[path.name] = "missing_id"
            continue

        # Map SSOT_Build fields to OwnerCreate fields
        payload = {
            "name": data.get("owner_name", data.get("name", "")),
            "email": data.get("email", "unknown@example.com"),
            "phone": data.get("phone"),
            "type": "corporate" if data.get("entity_type") == "company" else "individual",
            "entity_type": data.get("entity_type", "individual"),
            "contact_name": data.get("contact_name"),
            "website": data.get("website"),
            "x_url": data.get("x_url"),
            "instagram_url": data.get("instagram_url"),
            "facebook_url": data.get("facebook_url"),
            "profile_status": data.get("profile_status", "active"),
            "profile_origin": data.get("profile_origin"),
            "notes": data.get("notes"),
            "address": None,
            "bank_account": None,
            "ird_number": None,
        }
        if not payload["name"]:
            logger.error("Owner %s missing name — skipped", path.name)
            results[path.name] = "validation_error"
            continue

        try:
            owner = OwnerCreate(**payload)
        except Exception as exc:
            logger.error("Validation failed for owner %s: %s", path.name, exc)
            results[path.name] = "validation_error"
            continue

        doc_ref = collection.document(canonical_id)
        if doc_ref.get().exists:
            logger.info("Owner %s already exists — skipped", canonical_id)
            results[path.name] = "existed"
            continue

        doc_data = owner.model_dump()
        doc_data["id"] = canonical_id
        doc_data["created_at"] = firestore.SERVER_TIMESTAMP
        doc_data["updated_at"] = firestore.SERVER_TIMESTAMP
        doc_ref.set(doc_data)
        logger.info("Owner %s created", canonical_id)
        results[path.name] = f"created:{canonical_id}"

    return results


def seed_trainers(db: firestore.Client) -> dict[str, str]:
    """Seed trainers from SSOT_Build trainer JSON files with canonical IDs."""
    collection = _ensure_collection(db, "trainers")
    results: dict[str, str] = {}
    trainers_dir = DATA_ROOT / "trainers"
    if not trainers_dir.exists():
        logger.warning("Trainers directory not found: %s", trainers_dir)
        return results

    for path in sorted(trainers_dir.glob("*.json")):
        data = _load_json(path)
        canonical_id = data.get("trainer_id")
        if not canonical_id:
            logger.error("Trainer %s missing canonical trainer_id — skipped", path.name)
            results[path.name] = "missing_id"
            continue

        social = data.get("social_links", {})
        payload = {
            "name": data.get("trainer_name", data.get("name", "")),
            "stable_name": data.get("stable_name", data.get("trainer_name", "")),
            "location": data.get("location", "Unknown"),
            "email": "unknown@example.com",
            "phone": None,
            "nztr_license_number": None,
            "full_address": data.get("full_address"),
            "bio": data.get("bio"),
            "notable_wins": data.get("notable_wins", []),
            "website": data.get("website"),
            "x_url": social.get("x_url"),
            "instagram_url": social.get("instagram_url"),
            "facebook_url": social.get("facebook_url"),
            "profile_status": "active",
            "contact_name": data.get("contact_name"),
        }
        if not payload["name"]:
            logger.error("Trainer %s missing name — skipped", path.name)
            results[path.name] = "validation_error"
            continue

        try:
            trainer = TrainerCreate(**payload)
        except Exception as exc:
            logger.error("Validation failed for trainer %s: %s", path.name, exc)
            results[path.name] = "validation_error"
            continue

        doc_ref = collection.document(canonical_id)
        if doc_ref.get().exists:
            logger.info("Trainer %s already exists — skipped", canonical_id)
            results[path.name] = "existed"
            continue

        doc_data = trainer.model_dump()
        doc_data["id"] = canonical_id
        doc_data["created_at"] = firestore.SERVER_TIMESTAMP
        doc_data["updated_at"] = firestore.SERVER_TIMESTAMP
        doc_ref.set(doc_data)
        logger.info("Trainer %s created", canonical_id)
        results[path.name] = f"created:{canonical_id}"

    return results


def seed_hlts(db: firestore.Client) -> dict[str, str]:
    """Seed HLTs from SSOT_Build HLT JSON files (skeleton — links resolved separately)."""
    collection = _ensure_collection(db, "hlts")
    results: dict[str, str] = {}
    hlts_dir = DATA_ROOT / "hlt"
    if not hlts_dir.exists():
        logger.warning("HLT directory not found: %s", hlts_dir)
        return results

    for path in sorted(hlts_dir.glob("LSE-*.json")):
        data = _load_json(path)
        # Minimal mapping — enough to validate parsing without errors
        # Full relational linking (horse_microchip → horse doc, owner_id, trainer_id)
        # is intentionally left as a later step to avoid fragile lookups in seed script.
        payload = {
            "horse_microchip": data.get("horse_microchip", "0" * 15),
            "owner_id": data.get("owner_id", ""),
            "trainer_id": data.get("trainer_id", ""),
            "lease_period_months": data.get("lease_length_months", 12),
            "lease_start_date": data.get("lease_start_date", "2025-01-01"),
            "leasehold_stake_percentage": data.get("percentage_leased", 0.0),
            "investor_return_percentage": data.get("investor_stakes_split", 0.0),
            "syndicate_price_cents": int((data.get("total_issuance_value", 0) or 0) * 100),
            "shares_total": data.get("num_tokens", 0),
            "shares_sold": 0,
            "share_price_cents": int((data.get("token_price_nzd", 0) or 0) * 100),
            "fractional_interest_per_share": data.get("percent_per_token"),
            "currency": "NZD",
        }

        try:
            hlt = HLTCreate(**payload)
        except Exception as exc:
            logger.error("Validation failed for HLT %s: %s", path.name, exc)
            results[path.name] = "validation_error"
            continue

        doc_ref = collection.document()
        doc_data = hlt.model_dump()
        doc_data["id"] = doc_ref.id
        doc_data["created_at"] = firestore.SERVER_TIMESTAMP
        doc_data["updated_at"] = firestore.SERVER_TIMESTAMP
        doc_ref.set(doc_data)
        logger.info("HLT %s created as %s", path.name, doc_ref.id)
        results[path.name] = f"created:{doc_ref.id}"

    return results


def main() -> int:
    """Entry point."""
    db = firestore.Client()
    logger.info("Starting seed run at %s", _now_iso())

    seed_governing_bodies(db)
    seed_owners(db)
    seed_trainers(db)
    seed_hlts(db)

    logger.info("Seed run complete at %s", _now_iso())
    return 0


if __name__ == "__main__":
    sys.exit(main())
