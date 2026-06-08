"""
Trainer CRUD — Create, Read, Update, List

Trainers are independent entities linked by ID.
A horse can change trainers over time. The current trainer is stored on the horse record.
"""

from flask import Request, jsonify
from google.cloud import firestore
from models import TrainerCreate, TrainerUpdate

_DB = None

def _get_db():
    global _DB
    if _DB is None:
        _DB = firestore.Client()
    return _DB


def handle(request: Request, trainer_id: str | None = None):
    """Route by HTTP method and presence of trainer_id."""
    if request.method == "GET" and trainer_id:
        return get_trainer(trainer_id)
    if request.method == "GET":
        return list_trainers(request)
    if request.method == "POST":
        return create_trainer(request)
    if request.method == "PATCH" and trainer_id:
        return update_trainer(trainer_id, request)
    if request.method == "DELETE" and trainer_id:
        return delete_trainer(trainer_id)
    return jsonify({"error": "Method not allowed"}), 405


def create_trainer(request: Request):
    """Create a new trainer record."""
    try:
        data = request.get_json(force=True)
        trainer = TrainerCreate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    doc_ref = _get_db().collection("trainers").document()
    doc_data = trainer.model_dump()
    doc_data["id"] = doc_ref.id
    doc_data["created_at"] = firestore.SERVER_TIMESTAMP
    doc_data["updated_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set(doc_data)
    # Replace Firestore sentinel with a real timestamp for JSON response
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    doc_data["created_at"] = now_iso
    doc_data["updated_at"] = now_iso
    return jsonify(doc_data), 201


def get_trainer(trainer_id: str):
    """Get a trainer by document ID."""
    doc = _get_db().collection("trainers").document(trainer_id).get()
    if not doc.exists:
        return jsonify({"error": f"Trainer {trainer_id} not found"}), 404
    return jsonify(doc.to_dict()), 200


def list_trainers(request: Request):
    """List all trainers, optionally filtered by location or profile_status."""
    location = request.args.get("location")
    profile_status = request.args.get("profile_status")
    query = _get_db().collection("trainers")
    if location:
        query = query.where("location", "==", location)
    if profile_status:
        query = query.where("profile_status", "==", profile_status)
    docs = query.get()
    return jsonify([doc.to_dict() for doc in docs]), 200


def update_trainer(trainer_id: str, request: Request):
    """Update a trainer by document ID."""
    try:
        data = request.get_json(force=True)
        update = TrainerUpdate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    doc_ref = _get_db().collection("trainers").document(trainer_id)
    if not doc_ref.get().exists:
        return jsonify({"error": f"Trainer {trainer_id} not found"}), 404

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data["updated_at"] = firestore.SERVER_TIMESTAMP
    doc_ref.update(update_data)
    return jsonify({"message": f"Trainer {trainer_id} updated"}), 200


def delete_trainer(trainer_id: str):
    """Delete a trainer. Only if no horses reference it."""
    horses = _get_db().collection("horses").where("trainer_id", "==", trainer_id).limit(1).get()
    if horses:
        return jsonify({"error": f"Cannot delete trainer {trainer_id}: horses reference it"}), 409

    doc_ref = _get_db().collection("trainers").document(trainer_id)
    if not doc_ref.get().exists:
        return jsonify({"error": f"Trainer {trainer_id} not found"}), 404

    doc_ref.delete()
    return jsonify({"message": f"Trainer {trainer_id} deleted"}), 200