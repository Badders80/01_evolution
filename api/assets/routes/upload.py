"""
Asset Upload — Upload an image/document to GCS + write metadata to Firestore

Supports multipart/form-data uploads. Generates thumbnails for images.
Organizes files by entity type and ID (e.g., horse/985125000126462/).
"""

from flask import Request, jsonify
from google.cloud import firestore, storage
from models import AssetCreate
from PIL import Image
import io
import uuid

_DB = None

def _get_db():
    global _DB
    if _DB is None:
        _DB = firestore.Client()
    return _DB

storage_client = storage.Client()

BUCKET_MAP = {
    "image": "evolution-horse-images",
    "document": "evolution-horse-docs",
}

THUMBNAIL_SIZE = (400, 400)


def handle(request: Request):
    """Handle image/document upload."""
    if request.method != "POST":
        return jsonify({"error": "Method not allowed. Use POST."}), 405

    # Parse multipart form data
    if "file" not in request.files:
        return jsonify({"error": "No file provided. Use 'file' field."}), 400

    file = request.files["file"]
    entity_type = request.form.get("entity_type", "horse")
    entity_id = request.form.get("entity_id")
    alt = request.form.get("alt", "")
    tags = request.form.get("tags", "").split(",") if request.form.get("tags") else []
    is_primary = request.form.get("is_primary", "false").lower() == "true"
    uploaded_by = request.form.get("uploaded_by", "anonymous")

    if not entity_id:
        return jsonify({"error": "entity_id is required. For horses, use the microchip number."}), 400

    # Determine bucket
    asset_type = "image" if file.mimetype.startswith("image/") else "document"
    bucket_name = BUCKET_MAP.get(asset_type, "evolution-horse-images")
    bucket = storage_client.bucket(bucket_name)

    # Generate unique filename
    file_extension = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    unique_id = str(uuid.uuid4())[:8]
    gcs_path = f"{entity_type}/{entity_id}/{unique_id}.{file_extension}"

    # Upload to GCS
    blob = bucket.blob(gcs_path)
    file_content = file.read()
    blob.upload_from_string(file_content, content_type=file.mimetype)

    gcs_url = f"gs://{bucket_name}/{gcs_path}"
    public_url = blob.public_url

    # Generate thumbnail for images
    thumbnail_url = None
    if asset_type == "image":
        try:
            img = Image.open(io.BytesIO(file_content))
            img.thumbnail(THUMBNAIL_SIZE)
            thumb_buffer = io.BytesIO()
            img.save(thumb_buffer, format="JPEG", quality=85)
            thumb_buffer.seek(0)

            thumb_path = f"{entity_type}/{entity_id}/{unique_id}_thumb.{file_extension}"
            thumb_blob = bucket.blob(thumb_path)
            thumb_blob.upload_from_string(thumb_buffer.getvalue(), content_type="image/jpeg")
            thumbnail_url = thumb_blob.public_url
        except Exception:
            pass  # Thumbnail generation is best-effort

    # If is_primary, unset any existing primary for this entity
    if is_primary:
        existing_primary = _get_db().collection("assets").where("entity_type", "==", entity_type).where("entity_id", "==", entity_id).where("is_primary", "==", True).get()
        for doc in existing_primary:
            doc.reference.update({"is_primary": False})

    # Write metadata to Firestore
    doc_ref = _get_db().collection("assets").document()
    asset_data = {
        "id": doc_ref.id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "asset_type": asset_type,
        "gcs_url": gcs_url,
        "public_url": public_url,
        "thumbnail_url": thumbnail_url,
        "file_name": file.filename,
        "original_file_name": file.filename,
        "mime_type": file.mimetype,
        "file_size_bytes": len(file_content),
        "alt": alt,
        "tags": tags,
        "is_primary": is_primary,
        "context": "",
        "location": "",
        "uploaded_by": uploaded_by,
        "created_at": firestore.SERVER_TIMESTAMP,
    }

    doc_ref.set(asset_data)

    # Convert Sentinel to ISO string for JSON serialization response
    import datetime
    asset_data["created_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Update the entity's imageUrl if it's a primary horse image
    if is_primary and entity_type == "horse" and asset_type == "image":
        horse_ref = _get_db().collection("horses").document(entity_id)
        if horse_ref.get().exists:
            horse_ref.update({"image_url": public_url})

    return jsonify(asset_data), 201