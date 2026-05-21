"""
Asset Delete — Remove an asset from GCS + Firestore

Also unsets the entity's imageUrl if this was the primary image.
"""

from flask import Request, jsonify
from google.cloud import firestore, storage

db = firestore.Client()
storage_client = storage.Client()


def handle(request: Request):
    """Handle asset deletion."""
    if request.method != "DELETE":
        return jsonify({"error": "Method not allowed. Use DELETE."}), 405

    asset_id = request.args.get("asset_id")
    if not asset_id:
        return jsonify({"error": "asset_id is required"}), 400

    # Fetch asset metadata
    doc_ref = db.collection("assets").document(asset_id)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": f"Asset {asset_id} not found"}), 404

    asset_data = doc.to_dict()

    # Delete from GCS
    bucket_name = "evolution-horse-images" if asset_data["asset_type"] == "image" else "evolution-horse-docs"
    bucket = storage_client.bucket(bucket_name)

    # Extract blob path from GCS URL
    gcs_url = asset_data.get("gcs_url", "")
    if gcs_url:
        # gs://evolution-horse-images/horse/985125000126462/abc123.jpg → horse/985125000126462/abc123.jpg
        blob_path = "/".join(gcs_url.replace("gs://", "").split("/")[1:])
        blob = bucket.blob(blob_path)
        blob.delete()

    # Delete thumbnail if it exists
    if asset_data.get("thumbnail_url"):
        thumb_path = blob_path.rsplit(".", 1)[0] + "_thumb." + blob_path.rsplit(".", 1)[1]
        thumb_blob = bucket.blob(thumb_path)
        try:
            thumb_blob.delete()
        except Exception:
            pass  # Best-effort

    # If this was the primary image, unset the entity's imageUrl
    if asset_data.get("is_primary") and asset_data["entity_type"] == "horse":
        horse_docs = db.collection("horses").where("microchip", "==", asset_data["entity_id"]).limit(1).get()
        if horse_docs:
            horse_docs[0].reference.update({"image_url": None})

    # Delete from Firestore
    doc_ref.delete()

    return jsonify({"message": f"Asset {asset_id} deleted"}), 200