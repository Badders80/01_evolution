"""
Holdings CRUD — Create, Read, Update, List for Digital Ownership Ledger
"""

from flask import Request, jsonify
from google.cloud import firestore
from models import HoldingCreate

_DB = None

def _get_db():
    global _DB
    if _DB is None:
        _DB = firestore.Client()
    return _DB


def handle(request: Request, holding_id: str | None = None):
    """Route by HTTP method and presence of holding_id."""
    if request.method == "GET" and holding_id:
        return get_holding(holding_id)
    if request.method == "GET":
        return list_holdings(request)
    if request.method == "POST":
        return create_holding(request)
    if request.method == "PATCH" and holding_id:
        return update_holding(holding_id, request)
    return jsonify({"error": "Method not allowed"}), 405


def create_holding(request: Request):
    """Create a new holding (ownership record)."""
    try:
        data = request.get_json(force=True)
        holding = HoldingCreate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    # Verify HLT exists
    hlt_ref = _get_db().collection("hlts").document(holding.hlt_id)
    hlt_doc = hlt_ref.get()
    if not hlt_doc.exists:
        return jsonify({"error": f"HLT {holding.hlt_id} not found"}), 400

    doc_ref = _get_db().collection("holdings").document()
    doc_data = holding.model_dump()
    doc_data["id"] = doc_ref.id
    doc_data["status"] = "pending"
    doc_data["created_at"] = firestore.SERVER_TIMESTAMP
    doc_data["updated_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set(doc_data)
    return jsonify(doc_data), 201


def get_holding(holding_id: str):
    """Get holding by document ID."""
    doc = _get_db().collection("holdings").document(holding_id).get()
    if not doc.exists:
        return jsonify({"error": f"Holding {holding_id} not found"}), 404
    return jsonify(doc.to_dict()), 200


def list_holdings(request: Request):
    """List holdings, optionally filtered by user_id or hlt_id."""
    user_id = request.args.get("user_id")
    hlt_id = request.args.get("hlt_id")
    
    query = _get_db().collection("holdings")
    if user_id:
        query = query.where("user_id", "==", user_id)
    if hlt_id:
        query = query.where("hlt_id", "==", hlt_id)
        
    docs = query.get()
    return jsonify([doc.to_dict() for doc in docs]), 200


def update_holding(holding_id: str, request: Request):
    """Update a holding (e.g. status transition)."""
    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON payload: {str(e)}"}), 400

    doc_ref = _get_db().collection("holdings").document(holding_id)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": f"Holding {holding_id} not found"}), 404

    # Whitelist fields to update
    update_data = {}
    if "status" in data:
        update_data["status"] = data["status"]
    
    if not update_data:
        return jsonify({"error": "No updateable fields provided"}), 400

    update_data["updated_at"] = firestore.SERVER_TIMESTAMP
    doc_ref.update(update_data)
    return jsonify({"message": f"Holding {holding_id} updated"}), 200
