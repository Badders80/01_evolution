"""
Mission Control — Admin dev server.

Flask app on port 5000 serving static SPA from admin/static/.
SQLite auto-initialised on startup.
"""

import io
import os
import uuid
from datetime import date, datetime

from flask import Flask, send_from_directory, send_file, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError

from admin.db import init_db, SessionLocal, Horse as HorseORM, Owner as OwnerORM, Trainer as TrainerORM, Lease as LeaseORM, HLT as HLTORM, GoverningBody as GoverningBodyORM
from admin.horse_lookup import lookup_microchip
from admin.auth import require_auth
from core.models import HorseCreate, HorseUpdate, OwnerCreate, OwnerUpdate, TrainerCreate, TrainerUpdate, LeaseCreate

app = Flask(__name__, static_folder="admin/static")
CORS(app)

# ─── Init DB ──────────────────────────────────────────────────────────────────

init_db()


# ─── Response helpers ─────────────────────────────────────────────────────────

def _ok(data):
    return jsonify({"success": True, "data": data})


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


# ─── Static SPA catch-all ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("admin/static", "index.html")


@app.route("/<path:path>")
def static_files(path):
    # Strip query params (Flask appends them as part of path sometimes)
    clean_path = path.split('?')[0]
    response = send_from_directory("admin/static", clean_path)
    # Disable caching for JS and HTML files during development
    if clean_path.endswith('.js') or clean_path in ('index.html', 'app.html'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


# ─── Health ───────────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "hlt-mission-control"})


# ─── Horse lookup ─────────────────────────────────────────────────────────────

@app.route("/api/horses/lookup", methods=["POST"])
@require_auth
def horses_lookup():
    body = request.get_json(force=True, silent=True) or {}
    microchip = body.get("microchip", "").strip()
    if not microchip:
        return _err("microchip is required")
    result = lookup_microchip(microchip)
    if result.error:
        return _err(result.error)
    return _ok({
        "microchip": result.microchip,
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
        "source": result.source,
    })


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
            "breeder": row.breeder,
            "trainer_id": row.trainer_id,
            "status": row.status,
            "loveracing_id": row.loveracing_id,
            "breeding_url": row.breeding_url,
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
            status="draft",
            term_sheet_status="pending",
            pds_status="pending",
            sa_status="pending",
        )
        db.add(hlt_orm)
        db.commit()

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
        output_dir = "/home/evo/evo_01/01_evolution/api/email-ingest/output"
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
            data.append({
                "id": r.id,
                "horse_name": horse.name if horse else r.horse_microchip,
                "horse_microchip": r.horse_microchip,
                "owner_name": owner.name if owner else r.owner_id,
                "owner_id": r.owner_id,
                "trainer_name": trainer.name if trainer else r.trainer_id,
                "trainer_id": r.trainer_id,
                "lease_id": r.lease_id,
                "status": r.status,
                "term_sheet_status": r.term_sheet_status,
                "pds_status": r.pds_status,
                "sa_status": r.sa_status,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            })
        return _ok(data)
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
            "status": hlt.status,
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


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True, use_reloader=False)
