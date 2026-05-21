"""
Evolution KYC API — Cloud Function Entry Point

Stripe Identity verification for investors.
Creates verification sessions and handles webhooks.

Routes:
  /create-session  — Create a Stripe Identity verification session
  /webhook         — Handle Stripe webhook for KYC result
"""

import functions_framework
from flask import Request, jsonify

from routes import create_session, webhook


@functions_framework.http
def kyc(request: Request):
    """Route requests to the appropriate handler based on path."""
    path = request.path.strip("/")
    segments = path.split("/") if path else []

    if segments and segments[0] == "create-session":
        return create_session.handle(request)
    if segments and segments[0] == "webhook":
        return webhook.handle(request)

    return jsonify({"error": "Not found", "path": path}), 404