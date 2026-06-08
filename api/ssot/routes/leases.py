"""
Lease CRUD — Create, Read, Update, List

A Lease holds the commercial terms (draft → review → complete).
HLT links to a lease by canonical lease_id.
"""

from flask import Request, jsonify
from google.cloud import firestore
from models import LeaseCreate, LeaseUpdate

_DB = None

def _get_db():
    global _DB
    if _DB is None:
        _DB = firestore.Client()
    return _DB


def handle(request: Request, lease_id: str | None = None):
    """Route by HTTP method and presence of lease_id."""
    if request.method == "GET" and lease_id:
        return get_lease(lease_id)
    if request.method == "GET":
        return list_leases(request)
    if request.method == "POST":
        return create_lease(request)
    if request.method == "PATCH" and lease_id:
        return update_lease(lease_id, request)
    if request.method == "DELETE" and lease_id:
        return delete_lease(lease_id)
    return jsonify({"error": "Method not allowed"}), 405


def create_lease(request: Request):
    """Create a new lease record. lease_id must be unique."""
    try:
        data = request.get_json(force=True)
        lease = LeaseCreate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    # Check lease_id uniqueness
    doc_ref = _get_db().collection("leases").document(lease.lease_id)
    if doc_ref.get().exists:
        return jsonify({"error": f"Lease with ID {lease.lease_id} already exists"}), 409

    doc_data = lease.model_dump()
    doc_data["id"] = lease.lease_id
    doc_data["created_at"] = firestore.SERVER_TIMESTAMP
    doc_data["updated_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set(doc_data)
    # Replace Firestore sentinel with a real timestamp for JSON response
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    doc_data["created_at"] = now_iso
    doc_data["updated_at"] = now_iso
    return jsonify(doc_data), 201


def get_lease(lease_id: str):
    """Get a lease by canonical ID."""
    doc = _get_db().collection("leases").document(lease_id).get()
    if not doc.exists:
        return jsonify({"error": f"Lease {lease_id} not found"}), 404
    return jsonify(doc.to_dict()), 200


def list_leases(request: Request):
    """List all leases, optionally filtered by lease_status."""
    lease_status = request.args.get("lease_status")
    query = _get_db().collection("leases")
    if lease_status:
        query = query.where("lease_status", "==", lease_status)
    docs = query.get()
    return jsonify([doc.to_dict() for doc in docs]), 200


def update_lease(lease_id: str, request: Request):
    """Update a lease by canonical ID."""
    try:
        data = request.get_json(force=True)
        update = LeaseUpdate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    doc_ref = _get_db().collection("leases").document(lease_id)
    if not doc_ref.get().exists:
        return jsonify({"error": f"Lease {lease_id} not found"}), 404

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data["updated_at"] = firestore.SERVER_TIMESTAMP
    doc_ref.update(update_data)
    return jsonify({"message": f"Lease {lease_id} updated"}), 200


def delete_lease(lease_id: str):
    """Delete a lease. Only if no HLTs reference it."""
    hlts = _get_db().collection("hlts").where("lease_id", "==", lease_id).limit(1).get()
    if hlts:
        return jsonify({"error": f"Cannot delete lease {lease_id}: HLTs reference it"}), 409

    doc_ref = _get_db().collection("leases").document(lease_id)
    if not doc_ref.get().exists:
        return jsonify({"error": f"Lease {lease_id} not found"}), 404

    doc_ref.delete()
    return jsonify({"message": f"Lease {lease_id} deleted"}), 200
