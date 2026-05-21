"""
Owner CRUD — Create, Read, Update, List

Owners are independent entities linked by ID, never inlined.
A horse can have multiple owners. An owner can own multiple horses.
The HLT record holds the owner_id reference.
"""

from flask import Request, jsonify
from google.cloud import firestore
from models import OwnerCreate, OwnerUpdate

db = firestore.Client()


def handle(request: Request, owner_id: str | None = None):
    """Route by HTTP method and presence of owner_id."""
    if request.method == "GET" and owner_id:
        return get_owner(owner_id)
    if request.method == "GET":
        return list_owners(request)
    if request.method == "POST":
        return create_owner(request)
    if request.method == "PATCH" and owner_id:
        return update_owner(owner_id, request)
    if request.method == "DELETE" and owner_id:
        return delete_owner(owner_id)
    return jsonify({"error": "Method not allowed"}), 405


def create_owner(request: Request):
    """Create a new owner record."""
    try:
        data = request.get_json(force=True)
        owner = OwnerCreate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    doc_ref = db.collection("owners").document()
    doc_data = owner.model_dump()
    doc_data["id"] = doc_ref.id
    doc_data["created_at"] = firestore.SERVER_TIMESTAMP
    doc_data["updated_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set(doc_data)
    return jsonify(doc_data), 201


def get_owner(owner_id: str):
    """Get an owner by document ID."""
    doc = db.collection("owners").document(owner_id).get()
    if not doc.exists:
        return jsonify({"error": f"Owner {owner_id} not found"}), 404
    return jsonify(doc.to_dict()), 200


def list_owners(request: Request):
    """List all owners, optionally filtered by type."""
    owner_type = request.args.get("type")
    query = db.collection("owners")
    if owner_type:
        query = query.where("type", "==", owner_type)
    docs = query.get()
    return jsonify([doc.to_dict() for doc in docs]), 200


def update_owner(owner_id: str, request: Request):
    """Update an owner by document ID."""
    try:
        data = request.get_json(force=True)
        update = OwnerUpdate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    doc_ref = db.collection("owners").document(owner_id)
    if not doc_ref.get().exists:
        return jsonify({"error": f"Owner {owner_id} not found"}), 404

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data["updated_at"] = firestore.SERVER_TIMESTAMP
    doc_ref.update(update_data)
    return jsonify({"message": f"Owner {owner_id} updated"}), 200


def delete_owner(owner_id: str):
    """Delete an owner. Only if no HLTs reference it."""
    hlts = db.collection("hlts").where("owner_id", "==", owner_id).limit(1).get()
    if hlts:
        return jsonify({"error": f"Cannot delete owner {owner_id}: HLTs reference it"}), 409

    doc_ref = db.collection("owners").document(owner_id)
    if not doc_ref.get().exists:
        return jsonify({"error": f"Owner {owner_id} not found"}), 404

    doc_ref.delete()
    return jsonify({"message": f"Owner {owner_id} deleted"}), 200