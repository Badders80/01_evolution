"""
Asset Retrieve — Get assets for an entity

Primary use case: get all images for a horse by microchip number.
Supports filtering by asset_type and tags.
"""

from flask import Request, jsonify
from google.cloud import firestore

db = firestore.Client()


def handle(request: Request):
    """Handle asset retrieval."""
    if request.method != "GET":
        return jsonify({"error": "Method not allowed. Use GET."}), 405

    entity_type = request.args.get("entity_type", "horse")
    entity_id = request.args.get("entity_id")
    asset_type = request.args.get("asset_type")  # Optional filter
    tags = request.args.get("tags")  # Optional comma-separated filter

    if not entity_id:
        return jsonify({"error": "entity_id is required. For horses, use the microchip number."}), 400

    query = db.collection("assets").where("entity_type", "==", entity_type).where("entity_id", "==", entity_id)

    if asset_type:
        query = query.where("asset_type", "==", asset_type)

    docs = query.get()
    assets = [doc.to_dict() for doc in docs]

    # Sort: primary first, then by created_at descending
    assets.sort(key=lambda a: (not a.get("is_primary", False), a.get("created_at", "")), reverse=False)

    return jsonify({"assets": assets, "count": len(assets)}), 200