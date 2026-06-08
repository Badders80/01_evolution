"""
GoverningBody CRUD — Create, Read, Update, List

Governing bodies are independent entities linked by canonical code (e.g. NZTR).
Used by HLT records to reference the regulatory body for a lease.
"""

from flask import Request, jsonify
from google.cloud import firestore
from models import GoverningBodyCreate, GoverningBodyUpdate

_DB = None


def _get_db():
    global _DB
    if _DB is None:
        _DB = firestore.Client()
    return _DB


def handle(request: Request, governing_body_code: str | None = None):
    """Route by HTTP method and presence of governing_body_code."""
    if request.method == "GET" and governing_body_code:
        return get_governing_body(governing_body_code)
    if request.method == "GET":
        return list_governing_bodies(request)
    if request.method == "POST":
        return create_governing_body(request)
    if request.method == "PATCH" and governing_body_code:
        return update_governing_body(governing_body_code, request)
    if request.method == "DELETE" and governing_body_code:
        return delete_governing_body(governing_body_code)
    return jsonify({"error": "Method not allowed"}), 405


def create_governing_body(request: Request):
    """Create a new governing body record. Code must be unique."""
    try:
        data = request.get_json(force=True)
        body = GoverningBodyCreate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    doc_ref = _get_db().collection("governing_bodies").document(body.governing_body_code)
    if doc_ref.get().exists:
        return jsonify({"error": f"Governing body {body.governing_body_code} already exists"}), 409

    doc_data = body.model_dump()
    doc_data["id"] = body.governing_body_code
    doc_data["created_at"] = firestore.SERVER_TIMESTAMP
    doc_data["updated_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set(doc_data)
    # Replace Firestore sentinel with a real timestamp for JSON response
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    doc_data["created_at"] = now_iso
    doc_data["updated_at"] = now_iso
    return jsonify(doc_data), 201


def get_governing_body(governing_body_code: str):
    """Get a governing body by canonical code."""
    doc = _get_db().collection("governing_bodies").document(governing_body_code).get()
    if not doc.exists:
        return jsonify({"error": f"Governing body {governing_body_code} not found"}), 404
    return jsonify(doc.to_dict()), 200


def list_governing_bodies(request: Request):
    """List all governing bodies, optionally filtered by status."""
    status = request.args.get("status")
    query = _get_db().collection("governing_bodies")
    if status:
        query = query.where("status", "==", status)
    docs = query.get()
    return jsonify([doc.to_dict() for doc in docs]), 200


def update_governing_body(governing_body_code: str, request: Request):
    """Update a governing body by canonical code."""
    try:
        data = request.get_json(force=True)
        update = GoverningBodyUpdate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    doc_ref = _get_db().collection("governing_bodies").document(governing_body_code)
    if not doc_ref.get().exists:
        return jsonify({"error": f"Governing body {governing_body_code} not found"}), 404

    update_dict = update.model_dump(exclude_none=True)
    update_dict["updated_at"] = firestore.SERVER_TIMESTAMP
    doc_ref.update(update_dict)
    return jsonify({"updated": True, "governing_body_code": governing_body_code}), 200


def delete_governing_body(governing_body_code: str):
    """Delete a governing body. Only if no HLTs reference it."""
    hlts = (
        _get_db()
        .collection("hlts")
        .where("governing_body_code", "==", governing_body_code)
        .limit(1)
        .get()
    )
    if hlts:
        return (
            jsonify(
                {
                    "error": f"Cannot delete governing body {governing_body_code}: HLTs reference it"
                }
            ),
            409,
        )

    doc_ref = _get_db().collection("governing_bodies").document(governing_body_code)
    if not doc_ref.get().exists:
        return jsonify({"error": f"Governing body {governing_body_code} not found"}), 404

    doc_ref.delete()
    return jsonify({"deleted": True, "governing_body_code": governing_body_code}), 200
