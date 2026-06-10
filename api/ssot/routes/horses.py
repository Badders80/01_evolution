"""
Horse CRUD — Create, Read, Update, List

The horse record is anchored by microchip number.
Every NZ thoroughbred has a unique 15-digit microchip that never changes.
The loveracing.nz Stud Book page is the rosetta stone for each horse.

URL pattern: https://loveracing.nz/Breeding/{loveracingId}/{nameSlug}.aspx
Example:     https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx
"""

from flask import Request, jsonify
from google.cloud import firestore
from core.models import HorseCreate, HorseUpdate

_DB = None

def _get_db():
    global _DB
    if _DB is None:
        _DB = firestore.Client()
    return _DB


def handle(request: Request, microchip: str | None = None):
    """Route by HTTP method and presence of microchip."""
    if request.method == "GET" and microchip:
        return get_horse(microchip)
    if request.method == "GET":
        return list_horses(request)
    if request.method == "POST":
        return create_horse(request)
    if request.method == "PATCH" and microchip:
        return update_horse(microchip, request)
    if request.method == "DELETE" and microchip:
        return delete_horse(microchip)
    return jsonify({"error": "Method not allowed"}), 405


def create_horse(request: Request):
    """Create a new horse record. Microchip must be unique."""
    try:
        data = request.get_json(force=True)
        horse = HorseCreate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    # Check microchip uniqueness (direct document get)
    doc_ref = _get_db().collection("horses").document(horse.microchip)
    if doc_ref.get().exists:
        return jsonify({"error": f"Horse with microchip {horse.microchip} already exists"}), 409

    # Compute age from foaling_date
    from datetime import date
    age = (date.today() - horse.foaling_date).days // 365

    # Compute name_slug if not provided
    name_slug = horse.name_slug or horse.name.replace(" ", "-")

    doc_data = horse.model_dump()
    doc_data["id"] = horse.microchip
    doc_data["age"] = age
    doc_data["name_slug"] = name_slug
    doc_data["created_at"] = firestore.SERVER_TIMESTAMP
    doc_data["updated_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set(doc_data)
    # Replace Firestore sentinel with a real timestamp for JSON response
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    doc_data["created_at"] = now_iso
    doc_data["updated_at"] = now_iso
    return jsonify(doc_data), 201


def get_horse(microchip: str):
    """Get a horse by microchip number."""
    doc = _get_db().collection("horses").document(microchip).get()
    if not doc.exists:
        return jsonify({"error": f"Horse with microchip {microchip} not found"}), 404
    data = doc.to_dict()
    data["id"] = doc.id
    return jsonify(data), 200


def list_horses(request: Request):
    """List all horses, optionally filtered by status."""
    status = request.args.get("status")
    query = _get_db().collection("horses")
    if status:
        query = query.where("status", "==", status)
    docs = query.get()
    return jsonify([doc.to_dict() for doc in docs]), 200


def update_horse(microchip: str, request: Request):
    """Update a horse by microchip number."""
    try:
        data = request.get_json(force=True)
        update = HorseUpdate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    doc_ref = _get_db().collection("horses").document(microchip)
    if not doc_ref.get().exists:
        return jsonify({"error": f"Horse with microchip {microchip} not found"}), 404

    update_dict = update.model_dump(exclude_none=True)
    update_dict["updated_at"] = firestore.SERVER_TIMESTAMP

    # Recompute age if foaling_date changed
    if "foaling_date" in update_dict:
        from datetime import date, datetime
        foaling = update_dict["foaling_date"]
        if isinstance(foaling, str):
            foaling = datetime.fromisoformat(foaling).date()
        update_dict["age"] = (date.today() - foaling).days // 365

    doc_ref.update(update_dict)
    return jsonify({"updated": True, "microchip": microchip}), 200


def delete_horse(microchip: str):
    """Delete a horse by microchip number. Only if no HLTs reference it."""
    # Check for HLTs referencing this horse
    hlts = _get_db().collection("hlts").where("horse_microchip", "==", microchip).limit(1).get()
    if hlts:
        return jsonify({"error": f"Cannot delete horse {microchip}: HLTs reference it"}), 409

    doc_ref = _get_db().collection("horses").document(microchip)
    if not doc_ref.get().exists:
        return jsonify({"error": f"Horse with microchip {microchip} not found"}), 404

    doc_ref.delete()
    return jsonify({"deleted": True, "microchip": microchip}), 200