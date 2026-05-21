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
from models import HorseCreate, HorseUpdate

db = firestore.Client()


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

    # Check microchip uniqueness
    existing = db.collection("horses").where("microchip", "==", horse.microchip).limit(1).get()
    if existing:
        return jsonify({"error": f"Horse with microchip {horse.microchip} already exists"}), 409

    # Compute age from foaling_date
    from datetime import date
    age = (date.today() - horse.foaling_date).days // 365

    # Compute name_slug if not provided
    name_slug = horse.name_slug or horse.name.replace(" ", "-")

    doc_ref = db.collection("horses").document()
    doc_data = horse.model_dump()
    doc_data["id"] = doc_ref.id
    doc_data["age"] = age
    doc_data["name_slug"] = name_slug
    doc_data["created_at"] = firestore.SERVER_TIMESTAMP
    doc_data["updated_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set(doc_data)
    return jsonify(doc_data), 201


def get_horse(microchip: str):
    """Get a horse by microchip number."""
    docs = db.collection("horses").where("microchip", "==", microchip).limit(1).get()
    if not docs:
        return jsonify({"error": f"Horse with microchip {microchip} not found"}), 404
    return jsonify(docs[0].to_dict()), 200


def list_horses(request: Request):
    """List all horses, optionally filtered by status."""
    status = request.args.get("status")
    query = db.collection("horses")
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

    docs = db.collection("horses").where("microchip", "==", microchip).limit(1).get()
    if not docs:
        return jsonify({"error": f"Horse with microchip {microchip} not found"}), 404

    doc_ref = docs[0].reference
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data["updated_at"] = firestore.SERVER_TIMESTAMP

    # Recompute age if foaling_date changed
    if "foaling_date" in update_data:
        from datetime import date
        foaling = update_data["foaling_date"]
        if isinstance(foaling, str):
            from datetime import datetime
            foaling = datetime.fromisoformat(foaling).date()
        update_data["age"] = (date.today() - foaling).days // 365

    doc_ref.update(update_data)
    return jsonify({"message": f"Horse {microchip} updated"}), 200


def delete_horse(microchip: str):
    """Delete a horse by microchip number. Only if no HLTs reference it."""
    # Check for HLTs referencing this horse
    hlts = db.collection("hlts").where("horse_microchip", "==", microchip).limit(1).get()
    if hlts:
        return jsonify({"error": f"Cannot delete horse {microchip}: HLTs reference it"}), 409

    docs = db.collection("horses").where("microchip", "==", microchip).limit(1).get()
    if not docs:
        return jsonify({"error": f"Horse with microchip {microchip} not found"}), 404

    docs[0].reference.delete()
    return jsonify({"message": f"Horse {microchip} deleted"}), 200