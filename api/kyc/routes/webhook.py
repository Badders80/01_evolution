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
db = firestore.Client()

# Initialize Firebase Admin (lazy, once per cold start)
_firebase_app = None

def _get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        try:
            _firebase_app = firebase_admin.get_app()
        except ValueError:
            _firebase_app = firebase_admin.initialize_app(
                credentials.ApplicationDefault(),
                {"projectId": os.environ.get("GOOGLE_CLOUD_PROJECT", "evolution-engine")},
            )
    return _firebase_app


def _set_claims(user_id: str, kyc_status: str):
    """Set Firebase custom claims for the user."""
    try:
        app = _get_firebase_app()
        current = auth.get_user(user_id)
        existing_claims = current.custom_claims or {}
        new_claims = {
            **existing_claims,
            "kyc_status": kyc_status,
            "role": "investor" if kyc_status == "verified" else existing_claims.get("role", "viewer"),
        }
        auth.set_custom_user_claims(user_id, new_claims)
    except Exception as e:
        print(f"Failed to set claims for {user_id}: {e}")


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
        user_id = session.get("metadata", {}).get("user_id")

        if user_id:
            db.collection("users").document(user_id).update({
                "kyc_status": "verified",
                "updated_at": firestore.SERVER_TIMESTAMP,
            })
            _set_claims(user_id, "verified")

    elif event_type == "identity.verification_session.requires_input":
        # KYC needs more information
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")

        if user_id:
            db.collection("users").document(user_id).update({
                "kyc_status": "requires_input",
                "updated_at": firestore.SERVER_TIMESTAMP,
            })
            _set_claims(user_id, "requires_input")

    elif event_type == "identity.verification_session.canceled":
        # KYC was canceled
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")

        if user_id:
            db.collection("users").document(user_id).update({
                "kyc_status": "canceled",
                "updated_at": firestore.SERVER_TIMESTAMP,
            })
            _set_claims(user_id, "canceled")

    return jsonify({"received": True}), 200