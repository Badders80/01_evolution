"""
Evolution Assets API — Cloud Function Entry Point

Upload, retrieve, and delete images and documents attached to entities.
Step 1 only uses entityType='horse'. The schema supports more types for later.

Routes:
  /upload    — Upload an image/document to GCS + write metadata to Firestore
  /retrieve  — Get assets for an entity (e.g., all images for a horse by microchip)
  /delete    — Remove an asset from GCS + Firestore
"""

import functions_framework
from flask import Request, jsonify

from routes import upload, retrieve, delete_asset, bulk_upload


@functions_framework.http
def assets(request: Request):
    """Route requests to the appropriate handler based on path."""
    path = request.path.strip("/")
    segments = path.split("/") if path else []

    if segments and segments[0] == "upload":
        return upload.handle(request)
    if segments and segments[0] == "bulk-upload":
        return bulk_upload.handle(request)
    if segments and segments[0] == "retrieve":
        return retrieve.handle(request)
    if segments and segments[0] == "delete":
        return delete_asset.handle(request)

    return jsonify({"error": "Not found", "path": path}), 404