"""
HLT CRUD — Create, Read, Update, List, Status Transitions

An HLT (Horse Lease Token) is the assembled record of horse identity + commercial lease terms.
It only exists after commercial terms are attached to a horse.

Status lifecycle:
  draft → reviewed → publish_ready → published
  Step 1 uses draft and reviewed. Step 2 adds publish_ready and published.
"""

from flask import Request, jsonify
from google.cloud import firestore
from models import HLTCreate, HLTUpdate

db = firestore.Client()

# Valid status transitions
STATUS_TRANSITIONS = {
    "draft": ["reviewed"],
    "reviewed": ["draft", "publish_ready"],
    "publish_ready": ["reviewed", "published"],
    "published": [],  # Terminal state — cannot go back
}


def _resolve_hlt_references(hlt_data):
    """Helper to resolve and embed referenced horse, owner, and trainer documents."""
    # Resolve horse
    microchip = hlt_data.get("horse_microchip")
    if microchip:
        horse_docs = db.collection("horses").where("microchip", "==", microchip).limit(1).get()
        if horse_docs:
            hlt_data["horse"] = horse_docs[0].to_dict()
        else:
            hlt_data["horse"] = None

    # Resolve owner
    owner_id = hlt_data.get("owner_id")
    if owner_id:
        owner_doc = db.collection("owners").document(owner_id).get()
        if owner_doc.exists:
            hlt_data["owner"] = owner_doc.to_dict()
        else:
            hlt_data["owner"] = None

    # Resolve trainer
    trainer_id = hlt_data.get("trainer_id")
    if trainer_id:
        trainer_doc = db.collection("trainers").document(trainer_id).get()
        if trainer_doc.exists:
            hlt_data["trainer"] = trainer_doc.to_dict()
        else:
            hlt_data["trainer"] = None
            
    return hlt_data


def handle(request: Request, hlt_id: str | None = None):
    """Route by HTTP method and presence of hlt_id."""
    if request.method == "GET" and hlt_id:
        return get_hlt(hlt_id, request)
    if request.method == "GET":
        return list_hlts(request)
    if request.method == "POST":
        return create_hlt(request)
    if request.method == "PATCH" and hlt_id:
        return update_hlt(hlt_id, request)
    if request.method == "DELETE" and hlt_id:
        return delete_hlt(hlt_id)
    return jsonify({"error": "Method not allowed"}), 405


def create_hlt(request: Request):
    """Create a new HLT record. Horse, owner, and trainer must exist."""
    try:
        data = request.get_json(force=True)
        hlt = HLTCreate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    # Validate horse exists
    horse_docs = db.collection("horses").where("microchip", "==", hlt.horse_microchip).limit(1).get()
    if not horse_docs:
        return jsonify({"error": f"Horse with microchip {hlt.horse_microchip} not found"}), 400

    # Validate owner exists
    owner_doc = db.collection("owners").document(hlt.owner_id).get()
    if not owner_doc.exists:
        return jsonify({"error": f"Owner {hlt.owner_id} not found"}), 400

    # Validate trainer exists
    trainer_doc = db.collection("trainers").document(hlt.trainer_id).get()
    if not trainer_doc.exists:
        return jsonify({"error": f"Trainer {hlt.trainer_id} not found"}), 400

    doc_ref = db.collection("hlts").document()
    doc_data = hlt.model_dump()
    doc_data["id"] = doc_ref.id
    doc_data["status"] = "draft"
    doc_data["documents"] = {
        "term_sheet": {"status": "pending", "gcs_url": None},
        "pds": {"status": "pending", "gcs_url": None},
        "sa": {"status": "pending", "gcs_url": None},
    }
    doc_data["created_at"] = firestore.SERVER_TIMESTAMP
    doc_data["updated_at"] = firestore.SERVER_TIMESTAMP

    doc_ref.set(doc_data)
    return jsonify(doc_data), 201


def get_hlt(hlt_id: str, request: Request):
    """Get an HLT by document ID."""
    doc = db.collection("hlts").document(hlt_id).get()
    if not doc.exists:
        return jsonify({"error": f"HLT {hlt_id} not found"}), 404
    
    hlt_data = doc.to_dict()
    resolve = request.args.get("resolve") == "true"
    if resolve:
        hlt_data = _resolve_hlt_references(hlt_data)
        
    return jsonify(hlt_data), 200


def list_hlts(request: Request):
    """List all HLTs, optionally filtered by status or horse microchip."""
    status = request.args.get("status")
    microchip = request.args.get("horse_microchip")
    resolve = request.args.get("resolve") == "true"
    
    query = db.collection("hlts")
    if status:
        query = query.where("status", "==", status)
    if microchip:
        query = query.where("horse_microchip", "==", microchip)
    docs = query.get()
    
    results = []
    for doc in docs:
        hlt_data = doc.to_dict()
        if resolve:
            hlt_data = _resolve_hlt_references(hlt_data)
        results.append(hlt_data)
        
    return jsonify(results), 200



def update_hlt(hlt_id: str, request: Request):
    """Update an HLT. Can also transition status."""
    try:
        data = request.get_json(force=True)
        update = HLTUpdate(**data)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    doc_ref = db.collection("hlts").document(hlt_id)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": f"HLT {hlt_id} not found"}), 404

    current_data = doc.to_dict()

    # Validate status transition
    if update.status and update.status != current_data.get("status"):
        current_status = current_data.get("status")
        if update.status not in STATUS_TRANSITIONS.get(current_status, []):
            return jsonify({
                "error": f"Cannot transition from {current_status} to {update.status}. "
                         f"Valid transitions: {STATUS_TRANSITIONS.get(current_status, [])}"
            }), 400

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data["updated_at"] = firestore.SERVER_TIMESTAMP
    doc_ref.update(update_data)
    return jsonify({"message": f"HLT {hlt_id} updated"}), 200


def delete_hlt(hlt_id: str):
    """Delete an HLT. Only if status is 'draft'."""
    doc_ref = db.collection("hlts").document(hlt_id)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": f"HLT {hlt_id} not found"}), 404

    current_data = doc.to_dict()
    if current_data.get("status") != "draft":
        return jsonify({"error": f"Cannot delete HLT in status '{current_data.get('status')}'. Only draft HLTs can be deleted."}), 400

    doc_ref.delete()
    return jsonify({"message": f"HLT {hlt_id} deleted"}), 200