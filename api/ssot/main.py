"""
Evolution SSOT API — Cloud Function Entry Point

The single source of truth for horse, owner, trainer, and HLT data.
All reads and writes go through this function. No direct Firestore access.

Routes:
  /horses     — CRUD for horse records
  /owners     — CRUD for owner records
  /trainers   — CRUD for trainer records
  /hlts       — CRUD for HLT records + status transitions
  /docs       — Generate Term Sheet, PDS, SA from HLT
"""

import sys
import os

# Bootstrap to find core/ shared module from api/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import functions_framework
from flask import Request, jsonify

from routes import horses, owners, trainers, hlts, leases, docs, extract, content, holdings, governing_bodies
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
def ssot(request: Request):
    """Route requests to the appropriate handler based on path."""
    origin = request.headers.get("Origin")
    
    # Handle CORS preflight requests
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
    
    path = request.path.strip("/")
    segments = path.split("/") if path else []

    res = None
    # Route: /horses, /horses/{microchip}
    if segments and segments[0] == "horses":
        microchip = segments[1] if len(segments) > 1 else None
        res = horses.handle(request, microchip)

    # Route: /owners, /owners/{id}
    elif segments and segments[0] == "owners":
        owner_id = segments[1] if len(segments) > 1 else None
        res = owners.handle(request, owner_id)

    # Route: /trainers, /trainers/{id}
    elif segments and segments[0] == "trainers":
        trainer_id = segments[1] if len(segments) > 1 else None
        res = trainers.handle(request, trainer_id)

    # Route: /hlts, /hlts/{id}
    elif segments and segments[0] == "hlts":
        hlt_id = segments[1] if len(segments) > 1 else None
        res = hlts.handle(request, hlt_id)

    # Route: /leases, /leases/{id}
    elif segments and segments[0] == "leases":
        lease_id = segments[1] if len(segments) > 1 else None
        res = leases.handle(request, lease_id)

    # Route: /docs/{type}?hlt_id=...
    elif segments and segments[0] == "docs":
        doc_type = segments[1] if len(segments) > 1 else None
        res = docs.handle(request, doc_type)

    # Route: /extract
    elif segments and segments[0] == "extract":
        res = extract.handle(request)

    # Route: /holdings, /holdings/{id}
    elif segments and segments[0] == "holdings":
        holding_id = segments[1] if len(segments) > 1 else None
        res = holdings.handle(request, holding_id)

    # Route: /content, /content/{id}
    elif segments and segments[0] == "content":
        content_id = segments[1] if len(segments) > 1 else None
        res = content.handle(request, content_id)

    # Route: /governing-bodies, /governing-bodies/{code}
    elif segments and segments[0] == "governing-bodies":
        code = segments[1] if len(segments) > 1 else None
        res = governing_bodies.handle(request, code)

    else:
        res = jsonify({"error": "Not found", "path": path}), 404

    from flask import make_response
    response = make_response(res)
    return add_cors_headers(response, origin)