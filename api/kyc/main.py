"""
Evolution KYC API — Cloud Function Entry Point

Stripe Identity verification for investors.
Creates verification sessions and handles webhooks.

Routes:
  /create-session  — Create a Stripe Identity verification session
  /webhook         — Handle Stripe webhook for KYC result
"""

import sys
import os

# Bootstrap to find core/ shared module from api/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import functions_framework
from flask import Request, jsonify

from routes import create_session, webhook
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
def kyc(request: Request):
    """Route requests to the appropriate handler based on path."""
    origin = request.headers.get("Origin")
    path = request.path.strip("/")
    segments = path.split("/") if path else []

    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        return add_cors_headers(response, origin), 200

    # Verify Firebase ID token (all routes require auth)
    # Check x-firebase-token first (from proxy), then Authorization header
    id_token = request.headers.get("X-Firebase-Token", "")
    if not id_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            id_token = auth_header.split("Bearer ")[1]
    
    if not id_token:
        return add_cors_headers(jsonify({"error": "Missing Firebase token. Expected: X-Firebase-Token or Authorization: Bearer <token>"}), origin), 401

    try:
        from firebase_admin import auth as firebase_auth
        decoded_token = firebase_auth.verify_id_token(id_token)
        request.user = decoded_token
    except Exception as e:
        return add_cors_headers(jsonify({"error": f"Authentication failed: {str(e)}"}), origin), 401

    if segments and segments[0] == "create-session":
        res = create_session.handle(request)
    elif segments and segments[0] == "webhook":
        res = webhook.handle(request)
    else:
        res = jsonify({"error": "Not found", "path": path}), 404

    from flask import make_response
    response = make_response(res)
    return add_cors_headers(response, origin)