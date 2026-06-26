"""
Stripe KYC Webhook Handler

Receives Stripe webhook events for Identity verification results.
Updates the user's KYC status based on the verification outcome.
Also sets Firebase custom claims so the frontend picks up changes immediately.
"""

import os
import stripe
import firebase_admin
from firebase_admin import auth, credentials
from flask import Request, jsonify
from google.cloud import firestore

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
stripe_webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
_DB = None

def _get_db():
    global _DB
    if _DB is None:
        _DB = firestore.Client()
    return _DB

from auth import set_user_claims


def handle(request: Request):
    """Handle Stripe webhook events."""
    if request.method != "POST":
        return jsonify({"error": "Method not allowed. Use POST."}), 405

    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        return jsonify({"error": f"Webhook error: {str(e)}"}), 400

    # Handle the event
    event_type = event["type"]

    if event_type == "identity.verification_session.verified":
        # KYC passed
        session = event["data"]["object"]
        user_id = session.metadata.get("user_id") if getattr(session, "metadata", None) else None

        if user_id:
            _get_db().collection("users").document(user_id).update({
                "kyc_status": "verified",
                "updated_at": firestore.SERVER_TIMESTAMP,
            })
            set_user_claims(user_id, "verified")

    elif event_type == "identity.verification_session.processing":
        # KYC is processing/under review
        session = event["data"]["object"]
        user_id = session.metadata.get("user_id") if getattr(session, "metadata", None) else None

        if user_id:
            _get_db().collection("users").document(user_id).update({
                "kyc_status": "pending",
                "updated_at": firestore.SERVER_TIMESTAMP,
            })
            set_user_claims(user_id, "pending")

    elif event_type == "identity.verification_session.requires_input":
        # KYC needs more information
        session = event["data"]["object"]
        user_id = session.metadata.get("user_id") if getattr(session, "metadata", None) else None

        if user_id:
            _get_db().collection("users").document(user_id).update({
                "kyc_status": "requires_input",
                "updated_at": firestore.SERVER_TIMESTAMP,
            })
            set_user_claims(user_id, "requires_input")

    elif event_type == "identity.verification_session.canceled":
        # KYC was canceled
        session = event["data"]["object"]
        user_id = session.metadata.get("user_id") if getattr(session, "metadata", None) else None

        if user_id:
            _get_db().collection("users").document(user_id).update({
                "kyc_status": "canceled",
                "updated_at": firestore.SERVER_TIMESTAMP,
            })
            set_user_claims(user_id, "canceled")

    return jsonify({"received": True}), 200