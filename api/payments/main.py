"""
Evolution Payments API — Cloud Function Entry Point

Stripe Checkout sessions and payment webhooks.

Routes:
  /create-session  — Create a Stripe Checkout session for HLT purchase
  /webhook         — Handle Stripe webhook for successful payment (checkout.session.completed)
"""

import functions_framework
from flask import Request, jsonify

from routes import create_session, webhook


@functions_framework.http
def payments(request: Request):
    """Route requests to the appropriate handler based on path."""
    # Handle CORS preflight requests
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        return response, 200

    path = request.path.strip("/")
    segments = path.split("/") if path else []

    if segments and segments[0] == "create-session":
        return create_session.handle(request)
    if segments and segments[0] == "webhook":
        return webhook.handle(request)

    return jsonify({"error": "Not found", "path": path}), 404
