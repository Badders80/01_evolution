"""
Evolution Assets API — Cloud Function Entry Point

Upload, retrieve, and delete images and documents attached to entities.
Step 1 only uses entityType='horse'. The schema supports more types for later.

Routes:
  /upload    — Upload an image/document to GCS + write metadata to Firestore
  /retrieve  — Get assets for an entity (e.g., all images for a horse by microchip)
  /delete    — Remove an asset from GCS + Firestore
"""

import sys
import os

# Bootstrap to find core/ shared module from api/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import functions_framework
from flask import Request, jsonify

from routes import upload, retrieve, delete_asset, bulk_upload
from auth import require_auth

# CORS Configuration - Restrict to known domains
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:3000,http://localhost:5000,https://evolutionstables.nz"
).split(",")


def add_cors_headers(response, origin=None):
    """Add CORS headers to response."""
    if origin and origin in ALLOWED_ORIGINS:
        response.headers.add("Access-Control-Allow-Origin", origin)
        response.headers.add("Access-Control-Allow-Credentials", "true")
    else:
        # For development, allow localhost
        if origin and "localhost" in origin:
            response.headers.add("Access-Control-Allow-Origin", origin)
            response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    return response


@functions_framework.http
def assets(request: Request):
    """Route requests to the appropriate handler based on path."""
    origin = request.headers.get("Origin")
    path = request.path.strip("/")
    segments = path.split("/") if path else []

    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        return add_cors_headers(response, origin), 200

    # Verify Firebase ID token (all routes require auth)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return add_cors_headers(jsonify({"error": "Missing Authorization header. Expected: Bearer <token>"}), origin), 401

    id_token = auth_header.split("Bearer ")[1]
    try:
        from firebase_admin import auth as firebase_auth
        decoded_token = firebase_auth.verify_id_token(id_token)
        request.user = decoded_token
    except Exception as e:
        return add_cors_headers(jsonify({"error": f"Authentication failed: {str(e)}"}), origin), 401

    if segments and segments[0] == "upload":
        response = upload.handle(request)
    elif segments and segments[0] == "bulk-upload":
        response = bulk_upload.handle(request)
    elif segments and segments[0] == "retrieve":
        response = retrieve.handle(request)
    elif segments and segments[0] == "delete":
        response = delete_asset.handle(request)
    else:
        response = jsonify({"error": "Not found", "path": path}), 404

    from flask import make_response
    return make_response(add_cors_headers(response, origin))