"""
Asset Bulk Upload — Upload multiple images with smart naming and auto-tagging

Accepts multiple files + context metadata (horse, location, description).
Generates meaningful filenames: {horse_slug}_{date}_{context}_{seq}.{ext}
Auto-tags with horse name, owner, trainer, location.
"""

from flask import Request, jsonify
from google.cloud import firestore, storage
from models import AssetCreate
from PIL import Image
import io
import re
import uuid
from datetime import datetime

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


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug component."""
    if not text:
        return ""
    text = text.lower().strip()
    # Remove parenthetical country codes like (NZ), (AUS)
    text = re.sub(r"\([^)]*\)", "", text)
    # Replace non-alphanumeric with hyphens
    text = re.sub(r"[^a-z0-9]+", "-", text)
    # Collapse multiple hyphens
    text = re.sub(r"-{2,}", "-", text)
    # Remove leading/trailing hyphens
    text = text.strip("-")
    return text


def generate_meaningful_filename(
    horse_name: str | None,
    upload_date: str,
    context: str | None,
    sequence: int,
    extension: str,
) -> str:
    """
    Generate a meaningful filename from context.
    Pattern: {horse-slug}_{date}_{context-slug}_{seq}.{ext}
    Example: prudentia-nz_2026-05-20_morning-training_001.jpg
    """
    parts = []

    if horse_name:
        parts.append(slugify(horse_name))
    else:
        parts.append("untitled")

    parts.append(upload_date)

    if context:
        context_slug = slugify(context)
        if context_slug:
            parts.append(context_slug)

    parts.append(f"{sequence:03d}")

    filename = "_".join(parts) + f".{extension}"
    return filename


def handle(request: Request):
    """Handle bulk upload of multiple images with context metadata."""
    if request.method != "POST":
        return jsonify({"error": "Method not allowed. Use POST."}), 405

    # ── Parse form data ────────────────────────────────────────────────────
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files provided. Use 'files' field."}), 400

    entity_type = request.form.get("entity_type", "horse")
    entity_id = request.form.get("entity_id")
    if not entity_id:
        return jsonify({"error": "entity_id is required. For horses, use the microchip number."}), 400

    # Context metadata
    context = request.form.get("context", "")  # e.g. "morning training work at Wexford"
    location = request.form.get("location", "")  # e.g. "Wexford"
    alt_prefix = request.form.get("alt_prefix", "")  # e.g. "Prudentia doing morning training"
    is_primary = request.form.get("is_primary", "false").lower() == "true"
    primary_index = int(request.form.get("primary_index", "0"))  # Which file is primary (0-based)
    uploaded_by = request.form.get("uploaded_by", "admin")

    # Custom tags from form
    extra_tags = request.form.get("tags", "").split(",") if request.form.get("tags") else []
    extra_tags = [t.strip() for t in extra_tags if t.strip()]

    # ── Resolve horse metadata for auto-tagging ──────────────────────────
    # Owner is linked through HLT (not directly on horse).
    # Trainer is linked directly on the horse record.
    horse_name = None
    owner_name = None
    trainer_name = None

    if entity_type == "horse":
        horse_doc = _get_db().collection("horses").document(entity_id).get()
        if horse_doc.exists:
            horse_data = horse_doc.to_dict()
            horse_name = horse_data.get("name", "")

            # Resolve trainer name (direct on horse)
            trainer_id = horse_data.get("trainer_id")
            if trainer_id:
                trainer_doc = _get_db().collection("trainers").document(trainer_id).get()
                if trainer_doc.exists:
                    trainer_name = trainer_doc.to_dict().get("name", "")

            # Resolve owner name through HLT (owner is on the HLT, not the horse)
            hlt_docs = _get_db().collection("hlts").where("horse_microchip", "==", entity_id).limit(1).get()
            if hlt_docs:
                hlt_data = hlt_docs[0].to_dict()
                owner_id = hlt_data.get("owner_id")
                if owner_id:
                    owner_doc = _get_db().collection("owners").document(owner_id).get()
                    if owner_doc.exists:
                        owner_name = owner_doc.to_dict().get("name", "")

    # ── Build auto-tags ───────────────────────────────────────────────────
    auto_tags = []
    if horse_name:
        auto_tags.append(slugify(horse_name))
    if owner_name:
        auto_tags.append(slugify(owner_name))
    if trainer_name:
        auto_tags.append(slugify(trainer_name))
    if location:
        auto_tags.append(slugify(location))
    if context:
        # Add context words as individual tags (e.g. "morning training" → "morning-training")
        auto_tags.append(slugify(context))

    all_tags = list(dict.fromkeys(auto_tags + extra_tags))  # Deduplicate, preserve order

    # ── Upload date for filenames ─────────────────────────────────────────
    upload_date = datetime.now().strftime("%Y-%m-%d")

    # ── Process each file ─────────────────────────────────────────────────
    bucket_name = BUCKET_MAP.get("image", "evolution-horse-images")
    bucket = storage_client.bucket(bucket_name)
    results = []
    errors = []

    for idx, file in enumerate(files):
        if file.filename == "":
            continue

        try:
            file_content = file.read()
            file_extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
            mime_type = file.mimetype or f"image/{file_extension}"

            # Generate meaningful filename
            meaningful_name = generate_meaningful_filename(
                horse_name=horse_name,
                upload_date=upload_date,
                context=context,
                sequence=idx + 1,
                extension=file_extension,
            )

            # Upload to GCS with meaningful name
            unique_id = str(uuid.uuid4())[:8]
            gcs_path = f"{entity_type}/{entity_id}/{unique_id}_{meaningful_name}"

            blob = bucket.blob(gcs_path)
            blob.upload_from_string(file_content, content_type=mime_type)

            gcs_url = f"gs://{bucket_name}/{gcs_path}"
            public_url = blob.public_url

            # Generate thumbnail
            thumbnail_url = None
            asset_type = "image" if mime_type.startswith("image/") else "document"
            if asset_type == "image":
                try:
                    img = Image.open(io.BytesIO(file_content))
                    img.thumbnail(THUMBNAIL_SIZE)
                    thumb_buffer = io.BytesIO()
                    img.save(thumb_buffer, format="JPEG", quality=85)
                    thumb_buffer.seek(0)

                    thumb_path = f"{entity_type}/{entity_id}/{unique_id}_{meaningful_name.replace(f'.{file_extension}', '_thumb.jpg')}"
                    thumb_blob = bucket.blob(thumb_path)
                    thumb_blob.upload_from_string(thumb_buffer.getvalue(), content_type="image/jpeg")
                    thumbnail_url = thumb_blob.public_url
                except Exception:
                    pass  # Thumbnail generation is best-effort

            # Determine if this file is the primary
            file_is_primary = is_primary and idx == primary_index

            # If primary, unset any existing primary
            if file_is_primary:
                existing_primary = (
                    _get_db().collection("assets")
                    .where("entity_type", "==", entity_type)
                    .where("entity_id", "==", entity_id)
                    .where("is_primary", "==", True)
                    .get()
                )
                for doc in existing_primary:
                    doc.reference.update({"is_primary": False})

            # Build alt text
            alt_text = alt_prefix or ""
            if not alt_text and horse_name:
                alt_text = horse_name
            if context and alt_text:
                alt_text = f"{alt_text} — {context}"

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
                "file_name": meaningful_name,
                "original_file_name": file.filename,
                "mime_type": mime_type,
                "file_size_bytes": len(file_content),
                "alt": alt_text,
                "tags": all_tags,
                "is_primary": file_is_primary,
                "context": context,
                "location": location,
                "uploaded_by": uploaded_by,
                "created_at": firestore.SERVER_TIMESTAMP,
            }

            doc_ref.set(asset_data)

            # Update horse imageUrl if primary
            if file_is_primary and entity_type == "horse" and asset_type == "image":
                horse_ref = _get_db().collection("horses").document(entity_id)
                if horse_ref.get().exists:
                    horse_ref.update({"image_url": public_url})

            results.append(asset_data)

        except Exception as e:
            errors.append({"file": file.filename, "error": str(e)})

    return jsonify({
        "uploaded": results,
        "count": len(results),
        "errors": errors,
        "tags_applied": all_tags,
    }), 201