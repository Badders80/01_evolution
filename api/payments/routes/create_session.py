"""
Create Stripe Checkout Session for HLT Share Purchase
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
    """Create a Stripe Checkout Session for purchasing HLT shares."""
    if request.method != "POST":
        return jsonify({"error": "Method not allowed. Use POST."}), 405

    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON payload: {str(e)}"}), 400

    user_id = data.get("user_id")
    hlt_id = data.get("hlt_id")
    shares_to_buy = data.get("shares_to_buy")
    success_url = data.get("success_url")
    cancel_url = data.get("cancel_url")
    bypass_kyc = data.get("bypass_kyc", False)

    if not all([user_id, hlt_id, shares_to_buy, success_url, cancel_url]):
        return jsonify({"error": "Missing required fields (user_id, hlt_id, shares_to_buy, success_url, cancel_url)"}), 400

    try:
        shares_to_buy = int(shares_to_buy)
        if shares_to_buy <= 0:
            return jsonify({"error": "shares_to_buy must be a positive integer"}), 400
    except ValueError:
        return jsonify({"error": "shares_to_buy must be an integer"}), 400

    # 1. Fetch User and verify KYC
    user_ref = _get_db().collection("users").document(user_id)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return jsonify({"error": f"User {user_id} not found"}), 404

    user_data = user_doc.to_dict()
    kyc_status = user_data.get("kyc_status", "none")

    # KYC Verification Check (with dev bypass if stripe key is a test key)
    is_test_mode = str(stripe.api_key).startswith("sk_test_")
    if kyc_status != "verified":
        if not (bypass_kyc and is_test_mode):
            return jsonify({"error": f"User KYC status is '{kyc_status}'. Verification is required before purchase."}), 403

    # 2. Fetch HLT and verify availability
    hlt_ref = _get_db().collection("hlts").document(hlt_id)
    hlt_doc = hlt_ref.get()
    if not hlt_doc.exists:
        return jsonify({"error": f"HLT {hlt_id} not found"}), 404

    hlt_data = hlt_doc.to_dict()
    status = hlt_data.get("status", "draft")
    if status not in ["published", "publish_ready"]:
        return jsonify({"error": f"HLT is not available for purchase (status: {status})"}), 400

    shares_total = hlt_data.get("shares_total", 0)
    shares_sold = hlt_data.get("shares_sold", 0)
    shares_available = shares_total - shares_sold

    if shares_to_buy > shares_available:
        return jsonify({"error": f"Requested {shares_to_buy} shares, but only {shares_available} are available"}), 400

    share_price_cents = hlt_data.get("share_price_cents", 0)
    if share_price_cents <= 0:
        return jsonify({"error": "HLT share price is invalid"}), 400

    # Fetch horse name for checkout label
    microchip = hlt_data.get("horse_microchip")
    horse_doc = _get_db().collection("horses").document(microchip).get()
    horse_name = "Racehorse"
    if horse_doc.exists:
        horse_name = horse_doc.to_dict().get("name", "Racehorse")

    # Calculate percentages for display
    percentage_per_share = hlt_data.get("fractional_interest_per_share")
    if percentage_per_share is None:
        percentage_per_share = 100.0 / shares_total
    
    total_percentage = percentage_per_share * shares_to_buy
    total_price_cents = share_price_cents * shares_to_buy

    try:
        # Create Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "nzd",
                        "product_data": {
                            "name": f"{horse_name} - Stake Purchase",
                            "description": f"Acquisition of {shares_to_buy} unit(s) representing a {total_percentage:.2f}% stake in {horse_name}.",
                        },
                        "unit_amount": share_price_cents,
                    },
                    "quantity": shares_to_buy,
                }
            ],
            mode="payment",
            metadata={
                "user_id": user_id,
                "hlt_id": hlt_id,
                "shares_to_buy": str(shares_to_buy),
                "horse_microchip": microchip,
                "percentage_owned": str(total_percentage),
                "purchase_price_cents": str(total_price_cents),
            },
            customer_email=user_data.get("email"),
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return jsonify({
            "session_id": session.id,
            "url": session.url,
        }), 200

    except stripe.error.StripeError as e:
        return jsonify({"error": f"Stripe Checkout error: {str(e)}"}), 500
