"""
Create Stripe Identity Verification Session

Creates a Stripe Identity verification session for an investor.
Returns the session URL that the frontend redirects to.
"""

import os
import stripe
from flask import Request, jsonify
from google.cloud import firestore

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
_DB = None

def _get_db():
    global _DB
    if _DB is None:
        _DB = firestore.Client()
    return _DB


def handle(request: Request):
    """Create a Stripe Identity verification session."""
    if request.method != "POST":
        return jsonify({"error": "Method not allowed. Use POST."}), 405

    data = request.get_json(force=True)
    user_id = data.get("user_id")
    return_url = data.get("return_url")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    # Get or create user document
    user_ref = _get_db().collection("users").document(user_id)
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        # Lazy create user document
        user_data = {"email": data.get("email", ""), "created_at": firestore.SERVER_TIMESTAMP}
        user_ref.set(user_data)
    else:
        user_data = user_doc.to_dict()

    try:
        # Create Stripe Identity verification session
        session = stripe.identity.VerificationSession.create(
            type="document",
            metadata={
                "user_id": user_id,
            },
            return_url=return_url or "https://evolution.nz/auth/verify",
            provided_details={
                "email": user_data.get("email", ""),
            },
        )

        # Update user KYC status
        user_doc.reference.update({
            "kyc_status": "pending",
            "stripe_identity_session_id": session.id,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })

        # Set custom claims to pending so frontend picks it up immediately
        try:
            from auth import set_user_claims
            set_user_claims(user_id, "pending")
        except Exception as claim_err:
            print(f"Error setting pending claim for {user_id}: {claim_err}")

        return jsonify({
            "session_id": session.id,
            "url": session.url,
            "status": session.status,
        }), 200

    except stripe.error.StripeError as e:
        return jsonify({"error": f"Stripe error: {str(e)}"}), 400