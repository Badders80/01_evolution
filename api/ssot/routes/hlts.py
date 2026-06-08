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

_DB = None

def _get_db():
    global _DB
    if _DB is None:
        _DB = firestore.Client()
    return _DB

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
        horse_doc = _get_db().collection("horses").document(microchip).get()
        if horse_doc.exists:
            hlt_data["horse"] = horse_doc.to_dict()
        else:
            hlt_data["horse"] = None

    # Resolve owner
    owner_id = hlt_data.get("owner_id")
    if owner_id:
        owner_doc = _get_db().collection("owners").document(owner_id).get()
        if owner_doc.exists:
            hlt_data["owner"] = owner_doc.to_dict()
        else:
            hlt_data["owner"] = None

    # Resolve trainer
    trainer_id = hlt_data.get("trainer_id")
    if trainer_id:
        trainer_doc = _get_db().collection("trainers").document(trainer_id).get()
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
    if request.method == "POST" and hlt_id == "workflow":
        return create_hlt_workflow(request)
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
    horse_doc = _get_db().collection("horses").document(hlt.horse_microchip).get()
    if not horse_doc.exists:
        return jsonify({"error": f"Horse with microchip {hlt.horse_microchip} not found"}), 400

    # Validate owner exists
    owner_doc = _get_db().collection("owners").document(hlt.owner_id).get()
    if not owner_doc.exists:
        return jsonify({"error": f"Owner {hlt.owner_id} not found"}), 400

    # Validate trainer exists
    trainer_doc = _get_db().collection("trainers").document(hlt.trainer_id).get()
    if not trainer_doc.exists:
        return jsonify({"error": f"Trainer {hlt.trainer_id} not found"}), 400

    doc_ref = _get_db().collection("hlts").document()
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
    doc = _get_db().collection("hlts").document(hlt_id).get()
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
    
    query = _get_db().collection("hlts")
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

    doc_ref = _get_db().collection("hlts").document(hlt_id)
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
    doc_ref = _get_db().collection("hlts").document(hlt_id)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": f"HLT {hlt_id} not found"}), 404

    current_data = doc.to_dict()
    if current_data.get("status") != "draft":
        return jsonify({"error": f"Cannot delete HLT in status '{current_data.get('status')}'. Only draft HLTs can be deleted."}), 400

    doc_ref.delete()
    return jsonify({"message": f"HLT {hlt_id} deleted"}), 200


def create_hlt_workflow(request: Request):
    """HLT Workflow — Create Lease + HLT in one transaction.

    User provides: horse_microchip, owner_id, trainer_id
    Plus lease pricing: percent_leased, duration_months, token_count, min_unit_size,
    price_basis, price_period, price_amount, investor_share_percent, owner_share_percent

    System:
      1. Validates horse/owner/trainer exist
      2. Creates Lease (auto-derived pricing)
      3. Creates HLT linking to the new lease_id
      4. Returns {lease, hlt}
    """
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    # ─── Validate references ─────────────────────────────────────────
    horse_microchip = data.get("horse_microchip")
    owner_id = data.get("owner_id")
    trainer_id = data.get("trainer_id")

    if not all([horse_microchip, owner_id, trainer_id]):
        return jsonify({"error": "horse_microchip, owner_id, trainer_id are required"}), 400

    horse_doc = _get_db().collection("horses").document(horse_microchip).get()
    if not horse_doc.exists:
        return jsonify({"error": f"Horse {horse_microchip} not found"}), 400

    owner_doc = _get_db().collection("owners").document(owner_id).get()
    if not owner_doc.exists:
        return jsonify({"error": f"Owner {owner_id} not found"}), 400

    trainer_doc = _get_db().collection("trainers").document(trainer_id).get()
    if not trainer_doc.exists:
        return jsonify({"error": f"Trainer {trainer_id} not found"}), 400

    # ─── Extract lease fields ──────────────────────────────────────
    from models import LeaseCreate
    lease_fields = [
        "lease_id", "start_date", "end_date", "duration_months",
        "percent_leased", "token_count", "min_unit_size",
        "price_basis", "price_period", "price_amount",
        "investor_share_percent", "owner_share_percent",
    ]
    lease_data = {k: data.get(k) for k in lease_fields if data.get(k) is not None}
    lease_data["horse_id"] = horse_microchip
    lease_data.setdefault("platform_fee_percent", 0)
    lease_data.setdefault("lease_status", "draft")

    try:
        lease = LeaseCreate(**lease_data)
    except Exception as e:
        return jsonify({"error": f"Lease validation error: {str(e)}"}), 400

    # Check lease_id uniqueness
    doc_ref = _get_db().collection("leases").document(lease.lease_id)
    if doc_ref.get().exists:
        return jsonify({"error": f"Lease {lease.lease_id} already exists"}), 409

    # ─── Create Lease ──────────────────────────────────────────────
    lease_doc = lease.model_dump()
    lease_doc["id"] = lease.lease_id
    lease_doc["created_at"] = firestore.SERVER_TIMESTAMP
    lease_doc["updated_at"] = firestore.SERVER_TIMESTAMP
    doc_ref.set(lease_doc)

    # ─── Create HLT ───────────────────────────────────────────────
    from models import HLTCreate
    hlt_create = HLTCreate(
        horse_microchip=horse_microchip,
        owner_id=owner_id,
        trainer_id=trainer_id,
        lease_id=lease.lease_id,
    )

    hlt_ref = _get_db().collection("hlts").document()
    hlt_doc = hlt_create.model_dump()
    hlt_doc["id"] = hlt_ref.id
    hlt_doc["status"] = "draft"
    hlt_doc["documents"] = {
        "term_sheet": {"status": "pending", "gcs_url": None},
        "pds": {"status": "pending", "gcs_url": None},
        "sa": {"status": "pending", "gcs_url": None},
    }
    hlt_doc["created_at"] = firestore.SERVER_TIMESTAMP
    hlt_doc["updated_at"] = firestore.SERVER_TIMESTAMP
    hlt_ref.set(hlt_doc)

    # ─── Replace timestamps for JSON response ────────────────────
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    lease_doc["created_at"] = now_iso
    lease_doc["updated_at"] = now_iso
    hlt_doc["created_at"] = now_iso
    hlt_doc["updated_at"] = now_iso

    return jsonify({"lease": lease_doc, "hlt": hlt_doc}), 201