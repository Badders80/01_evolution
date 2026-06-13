"""
Evolution Applications API — Cloud Function Entry Point

Handles ownership applications from the marketplace.
Creates application records and sends email notifications to admin.

Routes:
  /submit  — Submit a new ownership application
  /list    — List applications (admin only)
"""

import sys
import os

# Bootstrap to find core/ shared module from api/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import functions_framework
from flask import Request, jsonify

# CORS Configuration - Restrict to known domains
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:3000,http://localhost:5000,https://evolutionstables.nz,https://evolution.2.0.vercel.app,https://02website-pearl.vercel.app"
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
def applications(request: Request):
    """Route requests to the appropriate handler based on path."""
    origin = request.headers.get("Origin")
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        response.status_code = 200
        return add_cors_headers(response, origin), 200
    
    # Simple health check
    if request.path == "/":
        response = jsonify({"status": "healthy", "service": "applications"})
        response.status_code = 200
        return add_cors_headers(response, origin), 200
    
    # Return 404 for other paths
    response = jsonify({"error": "Not found", "path": request.path})
    response.status_code = 404
    return add_cors_headers(response, origin), 404
