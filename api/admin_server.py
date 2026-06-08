"""
HLT Mission Control — Admin dev server.

Flask app on port 5000 serving static SPA from admin/static/.
SQLite auto-initialised on startup.
"""

import os
import uuid
from datetime import date
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError

from admin.db import init_db, SessionLocal, Horse as HorseORM, Owner as OwnerORM, Trainer as TrainerORM
from admin.horse_lookup import lookup_microchip
from admin.models import HorseCreate, HorseUpdate, OwnerCreate, OwnerUpdate, TrainerCreate, TrainerUpdate

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
    return send_from_directory("admin/static", path)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "hlt-mission-control"})


# ─── Horse lookup ─────────────────────────────────────────────────────────────

@app.route("/api/horses/lookup", methods=["POST"])
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


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
