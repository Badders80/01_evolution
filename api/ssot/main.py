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

import functions_framework
from flask import Request, jsonify

from routes import horses, owners, trainers, hlts, docs, extract, content


@functions_framework.http
def ssot(request: Request):
    """Route requests to the appropriate handler based on path."""
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        return response, 200
    
    path = request.path.strip("/")
    segments = path.split("/") if path else []

    # Route: /horses, /horses/{microchip}
    if segments and segments[0] == "horses":
        microchip = segments[1] if len(segments) > 1 else None
        return horses.handle(request, microchip)

    # Route: /owners, /owners/{id}
    if segments and segments[0] == "owners":
        owner_id = segments[1] if len(segments) > 1 else None
        return owners.handle(request, owner_id)

    # Route: /trainers, /trainers/{id}
    if segments and segments[0] == "trainers":
        trainer_id = segments[1] if len(segments) > 1 else None
        return trainers.handle(request, trainer_id)

    # Route: /hlts, /hlts/{id}
    if segments and segments[0] == "hlts":
        hlt_id = segments[1] if len(segments) > 1 else None
        return hlts.handle(request, hlt_id)

    # Route: /docs/{type}?hlt_id=...
    if segments and segments[0] == "docs":
        doc_type = segments[1] if len(segments) > 1 else None
        return docs.handle(request, doc_type)

    # Route: /extract
    if segments and segments[0] == "extract":
        return extract.handle(request)

    # Route: /content, /content/{id}
    if segments and segments[0] == "content":
        content_id = segments[1] if len(segments) > 1 else None
        return content.handle(request, content_id)

    return jsonify({"error": "Not found", "path": path}), 404