"""
Mission Control — Admin dev server.

Flask app on port 5000 serving static SPA from static/.
SQLite auto-initialised on startup.
"""

import io
import json
import os
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

# ─── Sys Path Setup for Monorepo ──────────────────────────────────────────────
TOOLS_DIR = Path(__file__).resolve().parent
MONOREPO_ROOT = TOOLS_DIR.parents[1]
sys.path.insert(0, str(MONOREPO_ROOT / "01_evolution" / "api"))
sys.path.insert(0, str(TOOLS_DIR))

from flask import Flask, send_from_directory, send_file, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError

from admin.db import (
    init_db, SessionLocal,
    Horse as HorseORM, Owner as OwnerORM, Trainer as TrainerORM,
    Lease as LeaseORM, HLT as HLTORM, GoverningBody as GoverningBodyORM,
    Document as DocumentORM, HLT_STATUSES, normalize_hlt_status,
)
from admin.horse_lookup import lookup_microchip, lookup_horse
from admin.auth import require_auth
from core.models import HorseCreate, HorseUpdate, OwnerCreate, OwnerUpdate, TrainerCreate, TrainerUpdate, LeaseCreate
import sync_service

STATIC_DIR = TOOLS_DIR / "static" if (TOOLS_DIR / "static").exists() else TOOLS_DIR / "admin" / "static"
app = Flask(__name__, static_folder=str(STATIC_DIR))
CORS(app)

# ─── Init DB ──────────────────────────────────────────────────────────────────

init_db()

# Seed only when DB is empty (never re-seed / wipe partial DBs)
db = SessionLocal()
horse_count = db.query(HorseORM).count()
if horse_count == 0:
    print("Database empty — seeding demo horses...")
    from admin.seed_data import seed_database
    seed_database()
# Normalize legacy HLT statuses → coming_soon | list | live | closed
for hlt in db.query(HLTORM).all():
    normalized = normalize_hlt_status(hlt.status)
    if hlt.status != normalized:
        hlt.status = normalized
db.commit()
# NOTE: do NOT auto-write 02_website JSON on startup — use Sync page with confirm
db.close()


# ─── Response helpers ─────────────────────────────────────────────────────────

def _ok(data):
    return jsonify({"success": True, "data": data})


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


# ─── Static SPA catch-all ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/<path:path>")
def static_files(path):
    # Strip query params (Flask appends them as part of path sometimes)
    clean_path = path.split('?')[0]
    response = send_from_directory(str(STATIC_DIR), clean_path)
    # Disable caching for JS and HTML files during development
    if clean_path.endswith('.js') or clean_path in ('index.html', 'app.html'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


# ─── Health ───────────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "mission-control"})


# ─── Horse lookup ─────────────────────────────────────────────────────────────

@app.route("/api/horses/lookup", methods=["POST"])
@require_auth
def horses_lookup():
    """Lookup by microchip OR loveracing.nz URL. Partial results still return 200 with warning."""
    body = request.get_json(force=True, silent=True) or {}
    query = (body.get("query") or body.get("microchip") or body.get("url") or "").strip()
    if not query:
        return _err("query is required (15-digit microchip or loveracing.nz URL)")
    result = lookup_horse(query)
    payload = {
        "microchip": result.microchip or "",
        "name": result.name,
        "sex": result.sex,
        "colour": result.colour,
        "sire_name": result.sire_name,
        "dam_name": result.dam_name,
        "foaling_date": result.foaling_date,
        "breeder": result.breeder,
        "trainer_name": result.trainer_name,
        "loveracing_id": result.loveracing_id,
        "breeding_url": result.breeding_url,
        "life_number": result.life_number,
        "source": result.source,
        "warning": result.error,
    }
    # Soft-fail: still return fields so UI can open confirm/manual step
    if result.error and not result.name and not result.loveracing_id:
        return _ok(payload)  # UI shows warning + empty confirm
    return _ok(payload)


# ─── Horse CRUD ───────────────────────────────────────────────────────────────

@app.route("/api/horses", methods=["GET"])
@require_auth
def list_horses():
    db = SessionLocal()
    try:
        rows = db.query(HorseORM).order_by(HorseORM.created_at.desc()).all()
        data = [
            {
                "microchip": r.microchip,
                "name": r.name,
                "name_slug": r.name_slug,
                "foaling_date": r.foaling_date,
                "sex": r.sex,
                "colour": r.colour,
                "sire_name": r.sire_name,
                "dam_name": r.dam_name,
                "breeder": r.breeder,
                "trainer_id": r.trainer_id,
                "status": r.status,
                "loveracing_id": r.loveracing_id,
                "breeding_url": r.breeding_url,
                "story": getattr(r, "story", None) or "",
                "next_up": getattr(r, "next_up", None) or "",
                "image_path": getattr(r, "image_path", None) or getattr(r, "cover_image", None) or "",
                "cover_image": getattr(r, "cover_image", None),
                "pillar1_cat": getattr(r, "pillar1_cat", None) or "",
                "pillar1_val": getattr(r, "pillar1_val", None) or "",
                "pillar2_cat": getattr(r, "pillar2_cat", None) or "",
                "pillar2_val": getattr(r, "pillar2_val", None) or "",
                "pillar3_cat": getattr(r, "pillar3_cat", None) or "",
                "pillar3_val": getattr(r, "pillar3_val", None) or "",
                "pedigree_blurb": getattr(r, "pedigree_blurb", None) or "",
                "trainer_commentary": getattr(r, "trainer_commentary", None) or "",
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ]
        return _ok(data)
    finally:
        db.close()


@app.route("/api/horses", methods=["POST"])
@require_auth
def create_horse():
    body = request.get_json(force=True, silent=True) or {}
    try:
        payload = HorseCreate(**body)
    except ValidationError as exc:
        return _err(exc.errors())
    db = SessionLocal()
    try:
        if db.query(HorseORM).filter_by(microchip=payload.microchip).first():
            return _err("Horse with this microchip already exists.", 409)
        slug = (payload.name_slug or "").strip()
        if slug and db.query(HorseORM).filter_by(name_slug=slug).first():
            return _err("Horse with this name_slug already exists.", 409)
        orm = HorseORM(
            microchip=payload.microchip,
            name=payload.name,
            name_slug=payload.name_slug,
            foaling_date=payload.foaling_date.isoformat() if payload.foaling_date else None,
            sex=payload.sex,
            colour=payload.colour,
            sire_name=payload.sire_name,
            dam_name=payload.dam_name,
            breeder=payload.breeder,
            trainer_id=payload.trainer_id,
            status=payload.status or "active",
            loveracing_id=payload.loveracing_id,
            breeding_url=payload.breeding_url,
        )
        db.add(orm)
        db.commit()
        return _ok({"microchip": orm.microchip, "name": orm.name})
    finally:
        db.close()


@app.route("/api/horses/<microchip>", methods=["GET"])
@require_auth
def get_horse(microchip):
    db = SessionLocal()
    try:
        row = db.query(HorseORM).filter_by(microchip=microchip).first()
        if not row:
            return _err("Horse not found", 404)
        return _ok({
            "microchip": row.microchip,
            "name": row.name,
            "name_slug": row.name_slug,
            "foaling_date": row.foaling_date,
            "sex": row.sex,
            "colour": row.colour,
            "sire_name": row.sire_name,
            "dam_name": row.dam_name,
            "dam_sire_name": getattr(row, "dam_sire_name", None),
            "breeder": row.breeder,
            "trainer_id": row.trainer_id,
            "cover_image": getattr(row, "cover_image", None),
            "conformation_image": getattr(row, "conformation_image", None),
            "pedigree_image": getattr(row, "pedigree_image", None),
            "action_image": getattr(row, "action_image", None),
            "story": getattr(row, "story", None) or "",
            "next_up": getattr(row, "next_up", None) or "",
            "image_path": getattr(row, "image_path", None) or "",
            "status": row.status,
            "loveracing_id": row.loveracing_id,
            "breeding_url": row.breeding_url,
            # Performance (P1)
            "starts_count": getattr(row, "starts_count", None),
            "wins_count": getattr(row, "wins_count", None),
            "places_count": getattr(row, "places_count", None),
            "total_earnings_nzd": getattr(row, "total_earnings_nzd", None),
            "performance_profile_url": getattr(row, "performance_profile_url", None) or "",
            "race_log_json": getattr(row, "race_log_json", None) or "",
            "pillar1_cat": getattr(row, "pillar1_cat", None) or "",
            "pillar1_val": getattr(row, "pillar1_val", None) or "",
            "pillar2_cat": getattr(row, "pillar2_cat", None) or "",
            "pillar2_val": getattr(row, "pillar2_val", None) or "",
            "pillar3_cat": getattr(row, "pillar3_cat", None) or "",
            "pillar3_val": getattr(row, "pillar3_val", None) or "",
            "pedigree_blurb": getattr(row, "pedigree_blurb", None) or "",
            "trainer_commentary": getattr(row, "trainer_commentary", None) or "",
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        })
    finally:
        db.close()


@app.route("/api/horses/<microchip>", methods=["PATCH"])
@require_auth
def update_horse(microchip):
    body = request.get_json(force=True, silent=True) or {}
    try:
        payload = HorseUpdate(**body)
    except ValidationError as exc:
        return _err(exc.errors())
    db = SessionLocal()
    try:
        row = db.query(HorseORM).filter_by(microchip=microchip).first()
        if not row:
            return _err("Horse not found", 404)
        updates = payload.model_dump(exclude_unset=True)
        if "foaling_date" in updates and isinstance(updates["foaling_date"], date):
            updates["foaling_date"] = updates["foaling_date"].isoformat()
        new_slug = updates.get("name_slug")
        if new_slug is not None:
            new_slug = new_slug.strip()
            if new_slug:
                clash = db.query(HorseORM).filter_by(name_slug=new_slug).first()
                if clash and clash.microchip != microchip:
                    return _err("Horse with this name_slug already exists.", 409)
        for k, v in updates.items():
            setattr(row, k, v)
        db.commit()
        return _ok({"microchip": row.microchip, "name": row.name})
    finally:
        db.close()


@app.route("/api/horses/<microchip>", methods=["DELETE"])
@require_auth
def delete_horse(microchip):
    db = SessionLocal()
    try:
        row = db.query(HorseORM).filter_by(microchip=microchip).first()
        if not row:
            return _err("Horse not found", 404)
        db.delete(row)
        db.commit()
        return _ok({"deleted": True, "microchip": microchip})
    finally:
        db.close()


# ─── Owner CRUD ──────────────────────────────────────────────────────────────

@app.route("/api/owners", methods=["GET"])
@require_auth
def list_owners():
    db = SessionLocal()
    try:
        rows = db.query(OwnerORM).order_by(OwnerORM.created_at.desc()).all()
        data = [
            {
                "id": r.id,
                "name": r.name,
                "email": r.email,
                "phone": r.phone,
                "entity_type": r.entity_type,
                "contact_name": r.contact_name,
                "website": r.website,
                "profile_status": r.profile_status,
                "address": r.address,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ]
        return _ok(data)
    finally:
        db.close()


@app.route("/api/owners", methods=["POST"])
@require_auth
def create_owner():
    body = request.get_json(force=True, silent=True) or {}
    try:
        payload = OwnerCreate(**body)
    except ValidationError as exc:
        return _err(exc.errors())
    db = SessionLocal()
    try:
        owner_id = str(uuid.uuid4())[:8]
        orm = OwnerORM(
            id=owner_id,
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            entity_type=payload.entity_type or payload.type or "individual",
            contact_name=payload.contact_name,
            website=payload.website,
            profile_status=payload.profile_status or "active",
            address=payload.address,
        )
        db.add(orm)
        db.commit()
        return _ok({"id": orm.id, "name": orm.name})
    finally:
        db.close()


@app.route("/api/owners/<owner_id>", methods=["GET"])
@require_auth
def get_owner(owner_id):
    db = SessionLocal()
    try:
        row = db.query(OwnerORM).filter_by(id=owner_id).first()
        if not row:
            return _err("Owner not found", 404)
        return _ok({
            "id": row.id,
            "name": row.name,
            "email": row.email,
            "phone": row.phone,
            "entity_type": row.entity_type,
            "contact_name": row.contact_name,
            "website": row.website,
            "profile_status": row.profile_status,
            "address": row.address,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        })
    finally:
        db.close()


@app.route("/api/owners/<owner_id>", methods=["PATCH"])
@require_auth
def update_owner(owner_id):
    body = request.get_json(force=True, silent=True) or {}
    try:
        payload = OwnerUpdate(**body)
    except ValidationError as exc:
        return _err(exc.errors())
    db = SessionLocal()
    try:
        row = db.query(OwnerORM).filter_by(id=owner_id).first()
        if not row:
            return _err("Owner not found", 404)
        updates = payload.model_dump(exclude_unset=True)
        for k, v in updates.items():
            setattr(row, k, v)
        db.commit()
        return _ok({"id": row.id, "name": row.name})
    finally:
        db.close()


@app.route("/api/owners/<owner_id>", methods=["DELETE"])
@require_auth
def delete_owner(owner_id):
    db = SessionLocal()
    try:
        row = db.query(OwnerORM).filter_by(id=owner_id).first()
        if not row:
            return _err("Owner not found", 404)
        db.delete(row)
        db.commit()
        return _ok({"deleted": True, "id": owner_id})
    finally:
        db.close()


# ─── Trainer CRUD ──────────────────────────────────────────────────────────────

@app.route("/api/trainers", methods=["GET"])
@require_auth
def list_trainers():
    db = SessionLocal()
    try:
        rows = db.query(TrainerORM).order_by(TrainerORM.created_at.desc()).all()
        data = [
            {
                "id": r.id,
                "name": r.name,
                "stable_name": r.stable_name,
                "location": r.location,
                "email": r.email,
                "phone": r.phone,
                "nztr_license_number": r.nztr_license_number,
                "bio": r.bio,
                "profile_status": r.profile_status,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ]
        return _ok(data)
    finally:
        db.close()


@app.route("/api/trainers", methods=["POST"])
@require_auth
def create_trainer():
    body = request.get_json(force=True, silent=True) or {}
    try:
        payload = TrainerCreate(**body)
    except ValidationError as exc:
        return _err(exc.errors())
    db = SessionLocal()
    try:
        trainer_id = str(uuid.uuid4())[:8]
        orm = TrainerORM(
            id=trainer_id,
            name=payload.name,
            stable_name=payload.stable_name,
            location=payload.location,
            email=payload.email,
            phone=payload.phone,
            nztr_license_number=payload.nztr_license_number,
            bio=payload.bio,
            profile_status=payload.profile_status or "active",
        )
        db.add(orm)
        db.commit()
        return _ok({"id": orm.id, "name": orm.name})
    finally:
        db.close()


@app.route("/api/trainers/<trainer_id>", methods=["GET"])
@require_auth
def get_trainer(trainer_id):
    db = SessionLocal()
    try:
        row = db.query(TrainerORM).filter_by(id=trainer_id).first()
        if not row:
            return _err("Trainer not found", 404)
        return _ok({
            "id": row.id,
            "name": row.name,
            "stable_name": row.stable_name,
            "location": row.location,
            "email": row.email,
            "phone": row.phone,
            "nztr_license_number": row.nztr_license_number,
            "bio": row.bio,
            "profile_status": row.profile_status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        })
    finally:
        db.close()


@app.route("/api/trainers/<trainer_id>", methods=["PATCH"])
@require_auth
def update_trainer(trainer_id):
    body = request.get_json(force=True, silent=True) or {}
    try:
        payload = TrainerUpdate(**body)
    except ValidationError as exc:
        return _err(exc.errors())
    db = SessionLocal()
    try:
        row = db.query(TrainerORM).filter_by(id=trainer_id).first()
        if not row:
            return _err("Trainer not found", 404)
        updates = payload.model_dump(exclude_unset=True)
        for k, v in updates.items():
            setattr(row, k, v)
        db.commit()
        return _ok({"id": row.id, "name": row.name})
    finally:
        db.close()


@app.route("/api/trainers/<trainer_id>", methods=["DELETE"])
@require_auth
def delete_trainer(trainer_id):
    db = SessionLocal()
    try:
        row = db.query(TrainerORM).filter_by(id=trainer_id).first()
        if not row:
            return _err("Trainer not found", 404)
        db.delete(row)
        db.commit()
        return _ok({"deleted": True, "id": trainer_id})
    finally:
        db.close()


# ─── Lease CRUD ──────────────────────────────────────────────────────────────

@app.route("/api/leases", methods=["GET"])
@require_auth
def list_leases():
    db = SessionLocal()
    try:
        rows = db.query(LeaseORM).order_by(LeaseORM.created_at.desc()).all()
        data = [
            {
                "lease_id": r.lease_id,
                "horse_id": r.horse_id,
                "start_date": r.start_date,
                "end_date": r.end_date,
                "duration_months": r.duration_months,
                "percent_leased": r.percent_leased,
                "token_count": r.token_count,
                "min_unit_size": r.min_unit_size,
                "price_basis": r.price_basis,
                "price_period": r.price_period,
                "price_amount": r.price_amount,
                "price_per_1pct_per_month": r.price_per_1pct_per_month,
                "price_per_1pct_per_year": r.price_per_1pct_per_year,
                "monthly_stake_price": r.monthly_stake_price,
                "annual_stake_price": r.annual_stake_price,
                "total_issuance_value_nzd": r.total_issuance_value_nzd,
                "percent_per_token": r.percent_per_token,
                "token_price_nzd": r.token_price_nzd,
                "investor_share_percent": r.investor_share_percent,
                "owner_share_percent": r.owner_share_percent,
                "platform_fee_percent": r.platform_fee_percent,
                "lease_status": r.lease_status,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ]
        return _ok(data)
    finally:
        db.close()


@app.route("/api/leases", methods=["POST"])
@require_auth
def create_lease():
    body = request.get_json(force=True, silent=True) or {}
    try:
        payload = LeaseCreate(**body)
    except ValidationError as exc:
        return _err(exc.errors())
    db = SessionLocal()
    try:
        if db.query(LeaseORM).filter_by(lease_id=payload.lease_id).first():
            return _err("Lease with this ID already exists.", 409)
        orm = LeaseORM(
            lease_id=payload.lease_id,
            horse_id=payload.horse_id,
            start_date=payload.start_date.isoformat(),
            end_date=payload.end_date.isoformat(),
            duration_months=payload.duration_months,
            percent_leased=payload.percent_leased,
            token_count=payload.token_count,
            min_unit_size=payload.min_unit_size,
            price_basis=payload.price_basis,
            price_period=payload.price_period,
            price_amount=payload.price_amount,
            price_per_1pct_per_month=payload.price_per_1pct_per_month,
            price_per_1pct_per_year=payload.price_per_1pct_per_year,
            monthly_stake_price=payload.monthly_stake_price,
            annual_stake_price=payload.annual_stake_price,
            total_issuance_value_nzd=payload.total_issuance_value_nzd,
            percent_per_token=payload.percent_per_token,
            token_price_nzd=payload.token_price_nzd,
            investor_share_percent=payload.investor_share_percent,
            owner_share_percent=payload.owner_share_percent,
            platform_fee_percent=payload.platform_fee_percent,
            lease_status=payload.lease_status,
        )
        db.add(orm)
        db.commit()
        return _ok({"lease_id": orm.lease_id, "horse_id": orm.horse_id})
    finally:
        db.close()


@app.route("/api/leases/<lease_id>", methods=["GET"])
@require_auth
def get_lease(lease_id):
    db = SessionLocal()
    try:
        row = db.query(LeaseORM).filter_by(lease_id=lease_id).first()
        if not row:
            return _err("Lease not found", 404)
        return _ok({
            "lease_id": row.lease_id,
            "horse_id": row.horse_id,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "duration_months": row.duration_months,
            "percent_leased": row.percent_leased,
            "token_count": row.token_count,
            "min_unit_size": row.min_unit_size,
            "price_basis": row.price_basis,
            "price_period": row.price_period,
            "price_amount": row.price_amount,
            "price_per_1pct_per_month": row.price_per_1pct_per_month,
            "price_per_1pct_per_year": row.price_per_1pct_per_year,
            "monthly_stake_price": row.monthly_stake_price,
            "annual_stake_price": row.annual_stake_price,
            "total_issuance_value_nzd": row.total_issuance_value_nzd,
            "percent_per_token": row.percent_per_token,
            "token_price_nzd": row.token_price_nzd,
            "investor_share_percent": row.investor_share_percent,
            "owner_share_percent": row.owner_share_percent,
            "platform_fee_percent": row.platform_fee_percent,
            "lease_status": row.lease_status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        })
    finally:
        db.close()


# ─── HLT Workflow ──────────────────────────────────────────────────────────────

@app.route("/api/hlts/workflow", methods=["POST"])
@require_auth
def create_hlt_workflow():
    """
    Body:
      horse_microchip, owner_id, trainer_id,
      lease_id, start_date, end_date, duration_months,
      percent_leased, token_count, min_unit_size,
      price_basis, price_period, price_amount,
      investor_share_percent, owner_share_percent, platform_fee_percent
    Validates all references exist, creates Lease (calculator auto-derives),
    creates HLT linking lease, returns {lease, hlt}.
    """
    body = request.get_json(force=True, silent=True) or {}

    horse_microchip = body.get("horse_microchip", "").strip()
    owner_id = body.get("owner_id", "").strip()
    trainer_id = body.get("trainer_id", "").strip()
    governing_body_code = body.get("governing_body_code", "").strip()

    if not horse_microchip or not owner_id or not trainer_id:
        return _err("horse_microchip, owner_id, and trainer_id are required.")

    db = SessionLocal()
    try:
        horse = db.query(HorseORM).filter_by(microchip=horse_microchip).first()
        if not horse:
            return _err(f"Horse with microchip {horse_microchip} not found.", 404)
        owner = db.query(OwnerORM).filter_by(id=owner_id).first()
        if not owner:
            return _err(f"Owner {owner_id} not found.", 404)
        trainer = db.query(TrainerORM).filter_by(id=trainer_id).first()
        if not trainer:
            return _err(f"Trainer {trainer_id} not found.", 404)
        if governing_body_code:
            gb = db.query(GoverningBodyORM).filter_by(governing_body_code=governing_body_code).first()
            if not gb:
                return _err(f"Governing body {governing_body_code} not found.", 404)

        # Build lease payload from body, injecting horse_id
        lease_payload = {k: v for k, v in body.items() if k not in ("horse_microchip", "owner_id", "trainer_id", "governing_body_code")}
        lease_payload["horse_id"] = horse_microchip

        try:
            lease_data = LeaseCreate(**lease_payload)
        except ValidationError as exc:
            return _err(exc.errors())
        except ValueError as exc:
            return _err(str(exc))

        if db.query(LeaseORM).filter_by(lease_id=lease_data.lease_id).first():
            return _err("Lease with this ID already exists.", 409)

        lease_orm = LeaseORM(
            lease_id=lease_data.lease_id,
            horse_id=lease_data.horse_id,
            start_date=lease_data.start_date.isoformat(),
            end_date=lease_data.end_date.isoformat(),
            duration_months=lease_data.duration_months,
            percent_leased=lease_data.percent_leased,
            token_count=lease_data.token_count,
            min_unit_size=lease_data.min_unit_size,
            price_basis=lease_data.price_basis,
            price_period=lease_data.price_period,
            price_amount=lease_data.price_amount,
            price_per_1pct_per_month=lease_data.price_per_1pct_per_month,
            price_per_1pct_per_year=lease_data.price_per_1pct_per_year,
            monthly_stake_price=lease_data.monthly_stake_price,
            annual_stake_price=lease_data.annual_stake_price,
            total_issuance_value_nzd=lease_data.total_issuance_value_nzd,
            percent_per_token=lease_data.percent_per_token,
            token_price_nzd=lease_data.token_price_nzd,
            investor_share_percent=lease_data.investor_share_percent,
            owner_share_percent=lease_data.owner_share_percent,
            platform_fee_percent=lease_data.platform_fee_percent,
            lease_status=lease_data.lease_status,
        )
        db.add(lease_orm)
        db.flush()

        hlt_id = str(uuid.uuid4())[:8]
        hlt_orm = HLTORM(
            id=hlt_id,
            horse_microchip=horse_microchip,
            owner_id=owner_id,
            trainer_id=trainer_id,
            governing_body_code=governing_body_code or None,
            lease_id=lease_data.lease_id,
            status="coming_soon",
            term_sheet_status="pending",
            pds_status="pending",
            sa_status="pending",
        )
        db.add(hlt_orm)
        db.commit()
        # Website JSON only via Sync page (confirm) — not on create

        return _ok({
            "lease": {
                "lease_id": lease_orm.lease_id,
                "horse_id": lease_orm.horse_id,
                "start_date": lease_orm.start_date,
                "end_date": lease_orm.end_date,
                "duration_months": lease_orm.duration_months,
                "percent_leased": lease_orm.percent_leased,
                "token_count": lease_orm.token_count,
                "min_unit_size": lease_orm.min_unit_size,
                "price_basis": lease_orm.price_basis,
                "price_period": lease_orm.price_period,
                "price_amount": lease_orm.price_amount,
                "price_per_1pct_per_month": lease_orm.price_per_1pct_per_month,
                "price_per_1pct_per_year": lease_orm.price_per_1pct_per_year,
                "monthly_stake_price": lease_orm.monthly_stake_price,
                "annual_stake_price": lease_orm.annual_stake_price,
                "total_issuance_value_nzd": lease_orm.total_issuance_value_nzd,
                "percent_per_token": lease_orm.percent_per_token,
                "token_price_nzd": lease_orm.token_price_nzd,
                "investor_share_percent": lease_orm.investor_share_percent,
                "owner_share_percent": lease_orm.owner_share_percent,
                "platform_fee_percent": lease_orm.platform_fee_percent,
                "lease_status": lease_orm.lease_status,
                "created_at": lease_orm.created_at,
            },
            "hlt": {
                "id": hlt_orm.id,
                "horse_microchip": hlt_orm.horse_microchip,
                "owner_id": hlt_orm.owner_id,
                "trainer_id": hlt_orm.trainer_id,
                "lease_id": hlt_orm.lease_id,
                "status": hlt_orm.status,
                "term_sheet_status": hlt_orm.term_sheet_status,
                "pds_status": hlt_orm.pds_status,
                "sa_status": hlt_orm.sa_status,
                "created_at": hlt_orm.created_at,
            },
        })
    finally:
        db.close()


# ─── Stats (for dashboard) ────────────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
@require_auth
def get_stats():
    db = SessionLocal()
    try:
        return _ok({
            "horses": db.query(HorseORM).count(),
            "owners": db.query(OwnerORM).count(),
            "trainers": db.query(TrainerORM).count(),
            "governing_bodies": db.query(GoverningBodyORM).count(),
            "leases": db.query(LeaseORM).count(),
            "hlts": db.query(HLTORM).count(),
        })
    finally:
        db.close()


# ─── Relational Drilling (Owner/Trainer -> Horses) ───────────────────────────

@app.route("/api/owners/<owner_id>/horses", methods=["GET"])
@require_auth
def get_owner_horses(owner_id):
    db = SessionLocal()
    try:
        owner = db.query(OwnerORM).filter_by(id=owner_id).first()
        if not owner:
            return _err("Owner not found", 404)
        hlts = db.query(HLTORM).filter_by(owner_id=owner_id).all()
        result = []
        for h in hlts:
            horse = db.query(HorseORM).filter_by(microchip=h.horse_microchip).first()
            lease = db.query(LeaseORM).filter_by(lease_id=h.lease_id).first()
            result.append({
                "hlt_id": h.id,
                "status": h.status,
                "term_sheet_status": h.term_sheet_status,
                "horse": {
                    "microchip": horse.microchip,
                    "name": horse.name,
                    "name_slug": horse.name_slug,
                    "sex": horse.sex,
                    "colour": horse.colour,
                } if horse else None,
                "lease": {
                    "token_price_nzd": lease.token_price_nzd,
                    "total_issuance_value_nzd": lease.total_issuance_value_nzd,
                    "percent_leased": lease.percent_leased,
                } if lease else None
            })
        return _ok({"owner_id": owner_id, "owner_name": owner.name, "horses": result})
    finally:
        db.close()


@app.route("/api/trainers/<trainer_id>/horses", methods=["GET"])
@require_auth
def get_trainer_horses(trainer_id):
    db = SessionLocal()
    try:
        trainer = db.query(TrainerORM).filter_by(id=trainer_id).first()
        if not trainer:
            return _err("Trainer not found", 404)
        horses = db.query(HorseORM).filter_by(trainer_id=trainer_id).all()
        hlts = db.query(HLTORM).filter_by(trainer_id=trainer_id).all()
        hlt_horse_chips = {h.horse_microchip for h in hlts}
        all_chips = {h.microchip for h in horses}.union(hlt_horse_chips)

        result = []
        for chip in all_chips:
            h = db.query(HorseORM).filter_by(microchip=chip).first()
            hlt = db.query(HLTORM).filter_by(horse_microchip=chip).first()
            result.append({
                "microchip": chip,
                "name": h.name if h else "Unknown",
                "name_slug": h.name_slug if h else None,
                "status": h.status if h else "active",
                "hlt_status": hlt.status if hlt else None,
            })
        return _ok({"trainer_id": trainer_id, "trainer_name": trainer.name, "horses": result})
    finally:
        db.close()


# ─── Visual Media CRUD & Asset Management ─────────────────────────────────────

ASSETS_DIR = Path(__file__).parent.parent.parent / "_assets" / "horses"

def _resolve_horse_assets_path(microchip_or_slug: str, db) -> tuple[Path, HorseORM]:
    horse = db.query(HorseORM).filter_by(microchip=microchip_or_slug).first()
    if not horse:
        horse = db.query(HorseORM).filter_by(name_slug=microchip_or_slug).first()
    if not horse:
        raise ValueError(f"Horse {microchip_or_slug} not found")

    slug = horse.name_slug or horse.name.lower().replace(" ", "-")
    horse_dir = ASSETS_DIR / slug
    (horse_dir / "images").mkdir(parents=True, exist_ok=True)
    (horse_dir / "videos").mkdir(parents=True, exist_ok=True)
    (horse_dir / "documents").mkdir(parents=True, exist_ok=True)
    (horse_dir / "term_sheets").mkdir(parents=True, exist_ok=True)
    return horse_dir, horse


@app.route("/api/horses/<microchip_or_slug>/assets/media", methods=["GET"])
@require_auth
def get_horse_media_assets(microchip_or_slug):
    db = SessionLocal()
    try:
        try:
            horse_dir, horse = _resolve_horse_assets_path(microchip_or_slug, db)
        except ValueError as exc:
            return _err(str(exc), 404)

        images_dir = horse_dir / "images"
        videos_dir = horse_dir / "videos"

        images = []
        if images_dir.exists():
            for f in images_dir.iterdir():
                if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
                    rel_path = f"_assets/horses/{horse_dir.name}/images/{f.name}"
                    images.append({
                        "filename": f.name,
                        "path": rel_path,
                        "size_bytes": f.stat().st_size,
                    })

        videos = []
        if videos_dir.exists():
            for f in videos_dir.iterdir():
                if f.is_file() and f.suffix.lower() in ('.mp4', '.mov', '.webm'):
                    rel_path = f"_assets/horses/{horse_dir.name}/videos/{f.name}"
                    videos.append({
                        "filename": f.name,
                        "path": rel_path,
                        "size_bytes": f.stat().st_size,
                    })

        return _ok({
            "horse_slug": horse_dir.name,
            "microchip": horse.microchip,
            "images": images,
            "videos": videos,
            "slots": {
                "cover_image": getattr(horse, "cover_image", None),
                "conformation_image": getattr(horse, "conformation_image", None),
                "pedigree_image": getattr(horse, "pedigree_image", None),
                "action_image": getattr(horse, "action_image", None),
            }
        })
    finally:
        db.close()


@app.route("/api/horses/<microchip_or_slug>/assets/media/slots", methods=["PATCH"])
@require_auth
def update_horse_media_slots(microchip_or_slug):
    db = SessionLocal()
    try:
        try:
            horse_dir, horse = _resolve_horse_assets_path(microchip_or_slug, db)
        except ValueError as exc:
            return _err(str(exc), 404)

        body = request.get_json(force=True, silent=True) or {}
        valid_slots = ("cover_image", "conformation_image", "pedigree_image", "action_image")
        for key in valid_slots:
            if key in body:
                setattr(horse, key, body[key])

        db.commit()
        return _ok({
            "microchip": horse.microchip,
            "slots": {
                "cover_image": getattr(horse, "cover_image", None),
                "conformation_image": getattr(horse, "conformation_image", None),
                "pedigree_image": getattr(horse, "pedigree_image", None),
                "action_image": getattr(horse, "action_image", None),
            }
        })
    finally:
        db.close()


@app.route("/api/horses/<microchip_or_slug>/assets/media", methods=["POST"])
@require_auth
def upload_horse_media_asset(microchip_or_slug):
    db = SessionLocal()
    try:
        try:
            horse_dir, horse = _resolve_horse_assets_path(microchip_or_slug, db)
        except ValueError as exc:
            return _err(str(exc), 404)

        if 'file' not in request.files:
            return _err("No file provided in request.")

        file = request.files['file']
        if file.filename == '':
            return _err("Empty filename.")

        media_type = request.form.get("type", "image")
        target_dir = horse_dir / "videos" if media_type == "video" else horse_dir / "images"
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / file.filename
        file.save(target_path)

        rel_path = f"_assets/horses/{horse_dir.name}/{target_dir.name}/{file.filename}"
        
        # Auto-assign slot if specified in form or if cover_image is currently empty
        slot = request.form.get("slot")
        if slot in ("cover_image", "conformation_image", "pedigree_image", "action_image"):
            setattr(horse, slot, rel_path)
            db.commit()
        elif media_type == "image" and not getattr(horse, "cover_image", None):
            horse.cover_image = rel_path
            db.commit()

        return _ok({"filename": file.filename, "path": rel_path, "status": "uploaded"})
    finally:
        db.close()


@app.route("/api/horses/<microchip_or_slug>/assets/media/<filename>", methods=["DELETE"])
@require_auth
def delete_horse_media_asset(microchip_or_slug, filename):
    db = SessionLocal()
    try:
        try:
            horse_dir, horse = _resolve_horse_assets_path(microchip_or_slug, db)
        except ValueError as exc:
            return _err(str(exc), 404)

        media_type = request.args.get("type", "image")
        target_dir = horse_dir / "videos" if media_type == "video" else horse_dir / "images"
        target_file = target_dir / filename

        if not target_file.exists():
            return _err("Media file not found", 404)

        target_file.unlink()

        # Clear slot reference if deleted file was assigned
        rel_path = f"_assets/horses/{horse_dir.name}/{target_dir.name}/{filename}"
        for key in ("cover_image", "conformation_image", "pedigree_image", "action_image"):
            if getattr(horse, key, None) == rel_path:
                setattr(horse, key, None)
        db.commit()

        return _ok({"deleted": True, "filename": filename})
    finally:
        db.close()


# ─── Term Sheet Freeze Gate ───────────────────────────────────────────────────

@app.route("/api/hlts/<hlt_id>/freeze", methods=["POST"])
@require_auth
def freeze_hlt_term_sheet(hlt_id):
    db = SessionLocal()
    try:
        hlt = db.query(HLTORM).filter_by(id=hlt_id).first()
        if not hlt:
            return _err("HLT not found", 404)

        horse = db.query(HorseORM).filter_by(microchip=hlt.horse_microchip).first()
        owner = db.query(OwnerORM).filter_by(id=hlt.owner_id).first()
        trainer = db.query(TrainerORM).filter_by(id=hlt.trainer_id).first()
        lease = db.query(LeaseORM).filter_by(lease_id=hlt.lease_id).first()

        if not horse or not owner or not trainer or not lease:
            return _err("Missing linked entity records (horse, owner, trainer, or lease).")

        slug = horse.name_slug or horse.name.lower().replace(" ", "-")
        horse_dir = ASSETS_DIR / slug
        ts_dir = horse_dir / "term_sheets"
        ts_dir.mkdir(parents=True, exist_ok=True)

        snapshot_data = {
            "$schema": "https://evolutionstables.com/schemas/hlt_snapshot.v1.json",
            "snapshot_id": f"snapshot_{hlt.id}_v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "FROZEN",
            "version": 1,
            "hlt_id": hlt.id,
            "horse": {
                "microchip": horse.microchip,
                "name": horse.name,
                "slug": slug,
                "sex": horse.sex,
                "colour": horse.colour,
                "foaling_date": horse.foaling_date,
                "sire_name": horse.sire_name,
                "dam_name": horse.dam_name,
                "breeder": horse.breeder,
                "loveracing_id": horse.loveracing_id,
                "breeding_url": horse.breeding_url,
            },
            "parties": {
                "owner": {
                    "id": owner.id,
                    "name": owner.name,
                    "entity_type": owner.entity_type,
                    "contact_email": owner.email,
                    "phone": owner.phone,
                    "address": owner.address,
                },
                "trainer": {
                    "id": trainer.id,
                    "name": trainer.name,
                    "stable_name": trainer.stable_name,
                    "location": trainer.location,
                    "bio": trainer.bio,
                },
                "platform": {
                    "name": "Evolution Stables Ltd"
                }
            },
            "commercials": {
                "lease_id": lease.lease_id,
                "percent_leased": lease.percent_leased,
                "duration_months": lease.duration_months,
                "total_issuance_value_nzd": lease.total_issuance_value_nzd,
                "token_count": lease.token_count,
                "percent_per_token": lease.percent_per_token,
                "token_price_nzd": lease.token_price_nzd,
                "min_unit_size": lease.min_unit_size,
                "price_per_1pct_per_month": lease.price_per_1pct_per_month,
                "price_per_1pct_per_year": lease.price_per_1pct_per_year,
                "monthly_stake_price": lease.monthly_stake_price,
                "annual_stake_price": lease.annual_stake_price,
                "start_date": lease.start_date,
                "end_date": lease.end_date,
            },
            "media_assets": {
                "hero_image": getattr(horse, "cover_image", None) or (f"_assets/horses/{slug}/images/hero.jpg" if (horse_dir / "images" / "hero.jpg").exists() else None),
                "cover_image": getattr(horse, "cover_image", None),
                "conformation_image": getattr(horse, "conformation_image", None),
                "pedigree_image": getattr(horse, "pedigree_image", None),
                "action_image": getattr(horse, "action_image", None),
                "gallery_images": [
                    f"_assets/horses/{slug}/images/{f.name}"
                    for f in (horse_dir / "images").glob("*")
                    if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')
                ] if (horse_dir / "images").exists() else [],
                "video_links": [
                    f"_assets/horses/{slug}/videos/{f.name}"
                    for f in (horse_dir / "videos").glob("*")
                    if f.is_file() and f.suffix.lower() in ('.mp4', '.mov', '.webm')
                ] if (horse_dir / "videos").exists() else [],
            },
            "documents": {
                "term_sheet_docx": f"_assets/horses/{slug}/term_sheets/term_sheet_{hlt.id}.docx"
            }
        }

        snapshot_file = ts_dir / f"hlt_snapshot_{hlt.id}_v1.json"
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, indent=2)

        try:
            from admin.generators.term_sheet import generate_term_sheet_docx
            docx_bytes = generate_term_sheet_docx(hlt.id, db)
            docx_file = ts_dir / f"term_sheet_{hlt.id}.docx"
            with open(docx_file, "wb") as f:
                f.write(docx_bytes)
            docx_rel_path = f"_assets/horses/{slug}/term_sheets/{docx_file.name}"
        except Exception as exc:
            docx_rel_path = None

        hlt.status = "completed"
        hlt.term_sheet_status = "completed"
        db.commit()

        return _ok({
            "hlt_id": hlt.id,
            "status": "completed",
            "snapshot_path": f"_assets/horses/{slug}/term_sheets/{snapshot_file.name}",
            "docx_path": docx_rel_path,
        })
    finally:
        db.close()



# ─── Horse Media Console ──────────────────────────────────────────────────────

@app.route("/api/horses/<microchip>/media", methods=["GET"])
@require_auth
def get_horse_media(microchip):
    """Get all transcripts/media for a horse by microchip."""
    import glob
    
    db = SessionLocal()
    try:
        # Verify horse exists
        horse = db.query(HorseORM).filter_by(microchip=microchip).first()
        if not horse:
            return _err("Horse not found", 404)
        
        # Find all transcript files for this horse
        output_dir = str(MONOREPO_ROOT / "01_evolution" / "api" / "email-ingest" / "output")
        pattern = os.path.join(output_dir, f"transcript_*{horse.name}*.json")
        transcript_files = glob.glob(pattern)
        
        transcripts = []
        for filepath in sorted(transcript_files, reverse=True):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                # Extract filename for date parsing
                filename = os.path.basename(filepath)
                # Parse date from filename: transcript_{horse}_{date}.json
                date_part = filename.replace(f"transcript_{horse.name}_", "").replace(".json", "")
                transcripts.append({
                    "id": data.get("id", filename),
                    "date": date_part,
                    "duration_seconds": data.get("duration_seconds", 0),
                    "speakers": data.get("speakers", []),
                    "full_text": data.get("full_text", ""),
                    "segments": data.get("segments", []),
                    "filepath": filepath,
                })
            except Exception as e:
                logger.warning(f"Failed to load transcript {filepath}: {e}")
        
        return _ok({
            "horse": {
                "microchip": horse.microchip,
                "name": horse.name,
                "sex": horse.sex,
                "colour": horse.colour,
                "foaling_date": horse.foaling_date,
            },
            "transcripts": transcripts,
            "count": len(transcripts),
        })
    finally:
        db.close()


# ─── Governing Bodies ────────────────────────────────────────────────────────

@app.route("/api/governing-bodies", methods=["GET"])
@require_auth
def list_governing_bodies():
    db = SessionLocal()
    try:
        rows = db.query(GoverningBodyORM).order_by(GoverningBodyORM.governing_body_name).all()
        data = [
            {
                "governing_body_code": r.governing_body_code,
                "governing_body_name": r.governing_body_name,
                "website": r.website,
                "status": r.status,
                "notes": r.notes,
            }
            for r in rows
        ]
        return _ok({"items": data, "count": len(data)})
    finally:
        db.close()


@app.route("/api/governing-bodies", methods=["POST"])
@require_auth
def create_governing_body():
    body = request.get_json(force=True, silent=True) or {}
    governing_body_code = body.get("governing_body_code", "").strip()
    governing_body_name = body.get("governing_body_name", "").strip()
    if not governing_body_code or not governing_body_name:
        return _err("governing_body_code and governing_body_name are required")
    db = SessionLocal()
    try:
        if db.query(GoverningBodyORM).filter_by(governing_body_code=governing_body_code).first():
            return _err("Governing body with this code already exists.", 409)
        orm = GoverningBodyORM(
            governing_body_code=governing_body_code,
            governing_body_name=governing_body_name,
            website=body.get("website"),
            status=body.get("status", "active"),
            notes=body.get("notes"),
        )
        db.add(orm)
        db.commit()
        return _ok({"governing_body_code": orm.governing_body_code, "governing_body_name": orm.governing_body_name})
    finally:
        db.close()


# ─── HLTs ─────────────────────────────────────────────────────────────────────

@app.route("/api/hlts", methods=["GET"])
@require_auth
def list_hlts():
    db = SessionLocal()
    try:
        rows = db.query(HLTORM).order_by(HLTORM.created_at.desc()).all()
        data = []
        for r in rows:
            horse = db.query(HorseORM).filter_by(microchip=r.horse_microchip).first()
            owner = db.query(OwnerORM).filter_by(id=r.owner_id).first()
            trainer = db.query(TrainerORM).filter_by(id=r.trainer_id).first()
            lease = db.query(LeaseORM).filter_by(lease_id=r.lease_id).first()
            status = normalize_hlt_status(r.status)
            data.append({
                "id": r.id,
                "horse_name": horse.name if horse else r.horse_microchip,
                "horse_microchip": r.horse_microchip,
                "owner_name": owner.name if owner else r.owner_id,
                "owner_id": r.owner_id,
                "trainer_name": trainer.name if trainer else r.trainer_id,
                "trainer_id": r.trainer_id,
                "lease_id": r.lease_id,
                "status": status,
                "percent_leased": lease.percent_leased if lease else None,
                "duration_months": lease.duration_months if lease else None,
                "token_price_nzd": lease.token_price_nzd if lease else None,
                "start_date": lease.start_date if lease else None,
                "end_date": lease.end_date if lease else None,
                "term_sheet_status": r.term_sheet_status,
                "pds_status": r.pds_status,
                "sa_status": r.sa_status,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            })
        return _ok(data)
    finally:
        db.close()


@app.route("/api/hlts/<hlt_id>/status", methods=["PATCH"])
@require_auth
def update_hlt_status(hlt_id):
    """Set HLT lifecycle status: coming_soon | list | live | closed. Does not write website JSON."""
    body = request.get_json(force=True, silent=True) or {}
    raw = (body.get("status") or "").strip().lower()
    new_status = normalize_hlt_status(raw)
    if raw and raw not in HLT_STATUSES and new_status == "coming_soon" and raw not in ("draft", "pending", "review", "new"):
        return _err(f"Invalid status '{raw}'. Use: {', '.join(HLT_STATUSES)}")
    if raw in HLT_STATUSES:
        new_status = raw

    db = SessionLocal()
    try:
        hlt = db.query(HLTORM).filter_by(id=hlt_id).first()
        if not hlt:
            return _err("HLT not found", 404)
        hlt.status = new_status
        hlt.updated_at = datetime.now().isoformat()
        db.commit()
        return _ok({
            "id": hlt.id,
            "status": hlt.status,
            "note": "Status saved in MC only. Use Sync page to publish website JSON.",
        })
    finally:
        db.close()


@app.route("/api/sync/website", methods=["GET", "POST"])
def trigger_website_sync():
    """
    GET  → dry-run preview (no write)
    POST → requires JSON/query confirm=true to write; dry_run=true for preview
    """
    body = request.get_json(force=True, silent=True) or {}
    dry_run = (
        request.args.get("dry_run", "").lower() in ("1", "true", "yes")
        or body.get("dry_run") is True
        or request.method == "GET"
    )
    confirm = (
        request.args.get("confirm", "").lower() in ("1", "true", "yes")
        or body.get("confirm") is True
    )
    db = SessionLocal()
    try:
        res = sync_service.sync_db_to_website_json(
            db, dry_run=dry_run, confirm=confirm and not dry_run
        )
        if "gsheet" not in res:
            res["gsheet"] = sync_service.push_to_google_sheet()
        return _ok(res)
    finally:
        db.close()


@app.route("/api/hlts/<hlt_id>", methods=["GET"])
def get_hlt(hlt_id):
    db = SessionLocal()
    try:
        hlt = db.query(HLTORM).filter_by(id=hlt_id).first()
        if not hlt:
            return _err("HLT not found", 404)
        lease = db.query(LeaseORM).filter_by(lease_id=hlt.lease_id).first()
        horse = db.query(HorseORM).filter_by(microchip=hlt.horse_microchip).first()
        owner = db.query(OwnerORM).filter_by(id=hlt.owner_id).first()
        trainer = db.query(TrainerORM).filter_by(id=hlt.trainer_id).first()
        governing_body = db.query(GoverningBodyORM).filter_by(governing_body_code=hlt.governing_body_code).first()
        return _ok({
            "id": hlt.id,
            "horse_microchip": hlt.horse_microchip,
            "owner_id": hlt.owner_id,
            "trainer_id": hlt.trainer_id,
            "governing_body_code": hlt.governing_body_code,
            "governing_body_name": governing_body.governing_body_name if governing_body else None,
            "lease_id": hlt.lease_id,
            "status": normalize_hlt_status(hlt.status),
            "term_sheet_status": hlt.term_sheet_status,
            "pds_status": hlt.pds_status,
            "sa_status": hlt.sa_status,
            "created_at": hlt.created_at,
            "updated_at": hlt.updated_at,
            "lease": {
                "lease_id": lease.lease_id,
                "horse_id": lease.horse_id,
                "start_date": lease.start_date,
                "end_date": lease.end_date,
                "duration_months": lease.duration_months,
                "percent_leased": lease.percent_leased,
                "token_count": lease.token_count,
                "min_unit_size": lease.min_unit_size,
                "price_basis": lease.price_basis,
                "price_period": lease.price_period,
                "price_amount": lease.price_amount,
                "price_per_1pct_per_month": lease.price_per_1pct_per_month,
                "price_per_1pct_per_year": lease.price_per_1pct_per_year,
                "monthly_stake_price": lease.monthly_stake_price,
                "annual_stake_price": lease.annual_stake_price,
                "total_issuance_value_nzd": lease.total_issuance_value_nzd,
                "percent_per_token": lease.percent_per_token,
                "token_price_nzd": lease.token_price_nzd,
                "investor_share_percent": lease.investor_share_percent,
                "owner_share_percent": lease.owner_share_percent,
                "platform_fee_percent": lease.platform_fee_percent,
                "lease_status": lease.lease_status,
            } if lease else None,
            "horse": {
                "microchip": horse.microchip,
                "name": horse.name,
                "sex": horse.sex,
                "colour": horse.colour,
                "sire_name": horse.sire_name,
                "dam_name": horse.dam_name,
                "breeder": horse.breeder,
                "foaling_date": horse.foaling_date,
                "breeding_url": horse.breeding_url,
                "loveracing_id": horse.loveracing_id,
            } if horse else None,
            "owner": {
                "id": owner.id,
                "name": owner.name,
                "email": owner.email,
                "phone": owner.phone,
                "entity_type": owner.entity_type,
            } if owner else None,
            "trainer": {
                "id": trainer.id,
                "name": trainer.name,
                "stable_name": trainer.stable_name,
                "location": trainer.location,
                "email": trainer.email,
                "phone": trainer.phone,
            } if trainer else None,
        })
    finally:
        db.close()


# ─── Term Sheet Download ────────────────────────────────────────────────────────

@app.route("/api/hlts/<hlt_id>/term-sheet.docx", methods=["GET"])
def download_term_sheet(hlt_id):
    db = SessionLocal()
    try:
        from admin.db import HLT as HLTORM
        hlt = db.query(HLTORM).filter_by(id=hlt_id).first()
        if not hlt:
            return _err("HLT not found", 404)

        from admin.generators.term_sheet import generate_term_sheet_docx
        docx_bytes = generate_term_sheet_docx(hlt_id, db)

        # Mark term sheet status complete
        hlt.term_sheet_status = "complete"
        db.commit()

        return send_file(
            io.BytesIO(docx_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name=f"term-sheet-{hlt_id}.docx",
        )
    except Exception as e:
        db.rollback()
        return _err(f"Term sheet generation failed: {e}", 500)
    finally:
        db.close()


# ─── HLT/Lease Save (for inline editing) ────────────────────────────────────────

@app.route("/__save_hlt", methods=["POST"])
def save_hlt():
    """Save HLT/Lease updates from inline editing."""
    body = request.get_json(force=True, silent=True) or {}
    lease_id = body.get("leaseId")
    content = body.get("content")

    if not lease_id or not content:
        return _err("leaseId and content are required")

    db = SessionLocal()
    try:
        lease = db.query(LeaseORM).filter_by(lease_id=lease_id).first()
        if not lease:
            return _err(f"Lease {lease_id} not found", 404)

        # Update lease fields
        updatable = [
            "percent_leased", "token_count", "min_unit_size",
            "price_basis", "price_period", "price_amount",
            "price_per_1pct_per_month", "price_per_1pct_per_year",
            "monthly_stake_price", "annual_stake_price",
            "total_issuance_value_nzd", "percent_per_token",
            "token_price_nzd", "investor_share_percent",
            "owner_share_percent", "platform_fee_percent",
            "lease_status", "start_date", "end_date", "duration_months",
            "notes"
        ]
        for field in updatable:
            if field in content:
                setattr(lease, field, content[field])

        # Recalculate derived fields if needed
        if any(f in content for f in ["percent_leased", "token_count", "price_per_1pct_per_month", "duration_months", "price_amount"]):
            lease.price_per_1pct_per_month = content.get("price_per_1pct_per_month", lease.price_per_1pct_per_month)
            lease.price_per_1pct_per_year = lease.price_per_1pct_per_month * 12
            lease.monthly_stake_price = lease.price_per_1pct_per_month * lease.percent_leased
            lease.annual_stake_price = lease.monthly_stake_price * 12
            lease.total_issuance_value_nzd = lease.price_per_1pct_per_month * lease.duration_months * lease.percent_leased
            lease.percent_per_token = lease.percent_leased / lease.token_count if lease.token_count else 0
            lease.token_price_nzd = lease.total_issuance_value_nzd / lease.token_count if lease.token_count else 0

        db.commit()
        return _ok({"success": True, "path": f"lease_{lease_id}"})
    except Exception as e:
        db.rollback()
        return _err(f"Save failed: {e}", 500)
    finally:
        db.close()


# ─── Platform Publishing ────────────────────────────────────────────────────────

@app.route("/__publish_to_platform", methods=["POST"])
def publish_to_platform():
    """Publish a single HLT to the Evolution Platform."""
    body = request.get_json(force=True, silent=True) or {}
    lease_id = body.get("leaseId")

    if not lease_id:
        return _err("leaseId is required")

    # In a real implementation, this would call the Evolution Platform API
    # For now, return success with mock data
    return _ok({
        "success": True,
        "platformResult": {
            "upserted": 1,
            "listingId": f"PLT-{lease_id}"
        }
    })


@app.route("/__publish_marketplace", methods=["POST"])
def publish_marketplace():
    """Publish multiple HLTs to the Evolution Platform marketplace."""
    body = request.get_json(force=True, silent=True) or {}
    listings = body.get("listings", [])

    if not listings:
        return _err("No listings provided")

    # In a real implementation, this would call the Evolution Platform API
    return _ok({
        "success": True,
        "published": len(listings),
        "message": f"Published {len(listings)} listings to marketplace draft"
    })


# ─── Document Upload / Delete ─────────────────────────────────────────────────

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "admin", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "png", "jpg", "jpeg", "gif", "webp", "svg"}

def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/api/hlts/<hlt_id>/documents", methods=["GET"])
def list_documents(hlt_id):
    """List all documents attached to an HLT."""
    db = SessionLocal()
    try:
        docs = db.query(DocumentORM).filter(DocumentORM.hlt_id == hlt_id).all()
        return _ok([{
            "id": d.id,
            "hlt_id": d.hlt_id,
            "doc_type": d.doc_type,
            "file_path": d.file_path,
            "file_name": d.file_name,
            "mime_type": d.mime_type,
            "status": getattr(d, 'status', 'draft'),
            "created_at": d.created_at,
        } for d in docs])
    finally:
        db.close()


@app.route("/api/documents/<doc_id>/status", methods=["PATCH"])
def update_document_status(doc_id):
    """Update status of a document (draft, approved, locked)."""
    body = request.get_json(force=True, silent=True) or {}
    new_status = body.get("status", "draft")
    db = SessionLocal()
    try:
        doc = db.query(DocumentORM).filter(DocumentORM.id == doc_id).first()
        if not doc:
            return _err("Document not found", 404)
        if hasattr(doc, 'status'):
            doc.status = new_status
        db.commit()
        return _ok({"id": doc.id, "status": new_status})
    finally:
        db.close()



@app.route("/api/hlts/<hlt_id>/documents", methods=["POST"])
def upload_document(hlt_id):
    """Upload a document (term sheet, PDS, SA, or image) to an HLT."""
    if "file" not in request.files:
        return _err("No file provided")

    file = request.files["file"]
    doc_type = request.form.get("doc_type", "photo")

    if file.filename == "":
        return _err("No file selected")

    if not _allowed_file(file.filename):
        return _err(f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    # Save file
    ext = file.filename.rsplit(".", 1)[1].lower()
    doc_id = str(uuid.uuid4())[:8]
    safe_name = f"{hlt_id}_{doc_type}_{doc_id}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    file.save(file_path)

    # Determine MIME type
    mime_map = {
        "pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword", "png": "image/png", "jpg": "image/jpeg",
        "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml",
    }
    mime_type = mime_map.get(ext, "application/octet-stream")

    # Save to DB
    db = SessionLocal()
    try:
        doc = DocumentORM(
            id=doc_id,
            hlt_id=hlt_id,
            doc_type=doc_type,
            file_path=f"/uploads/{safe_name}",
            file_name=file.filename,
            mime_type=mime_type,
            status="draft",
            created_at=datetime.now().isoformat(),
        )
        db.add(doc)

        # Update HLT status flags
        hlt = db.query(HLTORM).filter(HLTORM.id == hlt_id).first()
        if hlt:
            if doc_type == "term_sheet":
                hlt.term_sheet_status = "complete"
            elif doc_type == "pds":
                hlt.pds_status = "complete"
            elif doc_type == "sa":
                hlt.sa_status = "complete"

        db.commit()
        return _ok({
            "id": doc.id,
            "doc_type": doc.doc_type,
            "file_path": doc.file_path,
            "file_name": doc.file_name,
            "mime_type": doc.mime_type,
        })
    except Exception as e:
        db.rollback()
        return _err(str(e), 500)
    finally:
        db.close()


@app.route("/api/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    """Delete a document by ID."""
    db = SessionLocal()
    try:
        doc = db.query(DocumentORM).filter(DocumentORM.id == doc_id).first()
        if not doc:
            return _err("Document not found", 404)

        # Delete file from disk
        file_path = os.path.join(UPLOAD_DIR, os.path.basename(doc.file_path))
        if os.path.exists(file_path):
            os.remove(file_path)

        # Update HLT status flags
        hlt = db.query(HLTORM).filter(HLTORM.id == doc.hlt_id).first()
        if hlt:
            if doc.doc_type == "term_sheet":
                hlt.term_sheet_status = "pending"
            elif doc.doc_type == "pds":
                hlt.pds_status = "pending"
            elif doc.doc_type == "sa":
                hlt.sa_status = "pending"

        db.delete(doc)
        db.commit()
        return _ok({"deleted": doc_id})
    except Exception as e:
        db.rollback()
        return _err(str(e), 500)
    finally:
        db.close()


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    """Serve uploaded files."""
    return send_from_directory(UPLOAD_DIR, filename)


# ─── Asset paths (horse docs / public images) ─────────────────────────────────

@app.route("/horse-assets/<path:filepath>")
def serve_horse_assets(filepath):
    assets_dir = str(MONOREPO_ROOT / "_assets" / "horses")
    return send_from_directory(assets_dir, filepath)


@app.route("/public-images/<path:filepath>")
def serve_public_images(filepath):
    images_dir = str(MONOREPO_ROOT / "02_website" / "public" / "images")
    return send_from_directory(images_dir, filepath)


# Wizard UI retired — pack generation lives on HLT Detail
@app.route("/01_evolution/mission-control/investor-pack-wizard/", defaults={"filename": ""})
@app.route("/01_evolution/mission-control/investor-pack-wizard/<path:filename>")
def retired_wizard_ui(filename):
    # Legacy path — wizard removed; pack generate lives on HLT Detail
    return jsonify({
        "success": False,
        "error": "Investor Pack Wizard UI retired. Use HLT Detail → Generate draft pack (PDS+SA).",
        "redirect": "/#/hlts",
    }), 410


@app.route("/api/wizard/attachments", methods=["GET"])
@app.route("/api/wizard/export-docx", methods=["POST"])
def retired_wizard_api():
    return _err(
        "Wizard API retired. POST /api/hlts/<hlt_id>/investor-pack.docx from HLT Detail.",
        410,
    )


@app.route("/api/hlts/<hlt_id>/investor-pack.docx", methods=["GET", "POST"])
@require_auth
def generate_hlt_investor_pack(hlt_id):
    """
    Generate combined PDS + SA DRAFT DOCX from HLT commercial data.
    Saves under _assets/.../investor-packs/ and registers draft docs on the HLT
    (doc_type pds + sa, same file) so upload/lock lifecycle continues in-app.
    """
    db = SessionLocal()
    try:
        hlt = db.query(HLTORM).filter_by(id=hlt_id).first()
        if not hlt:
            return _err("HLT not found", 404)

        from admin.generators.investor_pack import generate_investor_pack_docx

        docx_bytes, saved_path, payload = generate_investor_pack_docx(hlt_id, db)
        slug = (payload.get("horse") or {}).get("slug") or hlt_id
        download_name = f"Investor-Pack-{slug}-DRAFT.docx"

        # Also land a copy in admin uploads for /uploads/ serving
        pack_id = str(uuid.uuid4())[:8]
        safe_name = f"{hlt_id}_investor_pack_{pack_id}.docx"
        upload_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(upload_path, "wb") as f:
            f.write(docx_bytes)
        rel_upload = f"/uploads/{safe_name}"

        # Register / refresh draft PDS + SA rows (combined pack file)
        now = datetime.now().isoformat()
        for doc_type in ("pds", "sa"):
            existing = (
                db.query(DocumentORM)
                .filter_by(hlt_id=hlt_id, doc_type=doc_type)
                .order_by(DocumentORM.created_at.desc())
                .first()
            )
            if existing and (getattr(existing, "status", None) or "draft") in (
                "approved",
                "locked",
            ):
                # Never overwrite locked counsel docs — still return download of new draft
                continue
            if existing:
                # replace prior draft file path
                old = os.path.join(UPLOAD_DIR, os.path.basename(existing.file_path or ""))
                if old and os.path.isfile(old) and old != upload_path:
                    try:
                        os.remove(old)
                    except OSError:
                        pass
                existing.file_path = rel_upload
                existing.file_name = download_name
                existing.mime_type = (
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                existing.status = "draft"
            else:
                db.add(
                    DocumentORM(
                        id=str(uuid.uuid4())[:8],
                        hlt_id=hlt_id,
                        doc_type=doc_type,
                        file_path=rel_upload,
                        file_name=download_name,
                        mime_type=(
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        ),
                        status="draft",
                        created_at=now,
                    )
                )

        hlt.pds_status = "draft"
        hlt.sa_status = "draft"
        db.commit()

        return send_file(
            io.BytesIO(docx_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name=download_name,
        )
    except Exception as e:
        db.rollback()
        return _err(f"Investor pack generation failed: {e}", 500)
    finally:
        db.close()



# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("Mission Control")
    print(f"  root: {TOOLS_DIR}")
    print(f"  open: http://127.0.0.1:{port}/")
    print("  publish: Sync page → Preview → confirm (no silent website writes)")
    print("  do NOT run 01_evolution/api/admin_server.py (legacy shadow)")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)


