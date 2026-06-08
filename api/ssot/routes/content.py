"""
Content CRUD — Create, Read, Update, List

Content records store transcripts, video updates, race reports, and other
ingested content tied to a horse by microchip.

Deduplication is by source_email_id (Gmail message ID).
"""

from flask import Request, jsonify
from google.cloud import firestore
from models import ContentCreate, ContentUpdate

_DB = None

def _get_db():
    global _DB
    if _DB is None:
        _DB = firestore.Client()
    return _DB


def handle(request: Request, content_id: str | None = None):
    """Route by HTTP method and presence of content_id."""
    if request.method == "GET" and content_id:
        return get_content(content_id)
    if request.method == "GET":
        return list_content(request)
    if request.method == "POST":
        return create_content(request)
    if request.method == "PATCH" and content_id:
        return update_content(content_id, request)
    if request.method == "DELETE" and content_id:
        return delete_content(content_id)
    return jsonify({"error": "Method not allowed"}), 405


def create_content(request: Request):
    """Create a new content record. Deduplicates by source_email_id."""
    try:
        data = request.get_json(force=True)
        content = ContentCreate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    # Validate horse exists
    horse_doc = _get_db().collection("horses").document(content.horse_microchip).get()
    if not horse_doc.exists:
        return jsonify({"error": f"Horse with microchip {content.horse_microchip} not found"}), 400

    # Deduplicate by source_email_id
    if content.source_email_id:
        existing = _get_db().collection("content").where("source_email_id", "==", content.source_email_id).limit(1).get()
        if existing:
            return jsonify({
                "error": "Content already exists for this email",
                "existing_id": existing[0].id,
            }), 409

    doc_ref = _get_db().collection("content").document()
    doc_data = content.model_dump()
    doc_data["id"] = doc_ref.id
    doc_data["created_at"] = firestore.SERVER_TIMESTAMP
    doc_data["updated_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set(doc_data)
    return jsonify(doc_data), 201


def get_content(content_id: str):
    """Get a content record by document ID."""
    doc = _get_db().collection("content").document(content_id).get()
    if not doc.exists:
        return jsonify({"error": f"Content {content_id} not found"}), 404
    return jsonify(doc.to_dict()), 200


def list_content(request: Request):
    """List content records, optionally filtered by horse_microchip, type, or status."""
    horse_microchip = request.args.get("horse_microchip")
    content_type = request.args.get("content_type")
    status = request.args.get("status")

    query = _get_db().collection("content")
    if horse_microchip:
        query = query.where("horse_microchip", "==", horse_microchip)
    if content_type:
        query = query.where("content_type", "==", content_type)
    if status:
        query = query.where("status", "==", status)

    docs = query.get()
    # Sort in-memory by content_date descending (avoids composite index requirement)
    results = sorted(
        [doc.to_dict() for doc in docs],
        key=lambda d: d.get("content_date", ""),
        reverse=True,
    )
    return jsonify(results), 200


def update_content(content_id: str, request: Request):
    """Update a content record by document ID."""
    try:
        data = request.get_json(force=True)
        update = ContentUpdate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    doc = _get_db().collection("content").document(content_id).get()
    if not doc.exists:
        return jsonify({"error": f"Content {content_id} not found"}), 404

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data["updated_at"] = firestore.SERVER_TIMESTAMP

    doc.reference.update(update_data)
    return jsonify(doc.reference.get().to_dict()), 200


def delete_content(content_id: str):
    """Delete a content record by document ID."""
    doc = _get_db().collection("content").document(content_id).get()
    if not doc.exists:
        return jsonify({"error": f"Content {content_id} not found"}), 404

    doc.reference.delete()
    return jsonify({"deleted": content_id}), 200
