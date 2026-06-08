"""
Stripe Payments Webhook Handler
"""

import os
import stripe
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


@firestore.transactional
def process_purchase_transaction(transaction, hlt_ref, holding_ref, holding_data, shares_to_buy):
    """Firestore transaction to increment shares_sold and create the holding record safely."""
    hlt_snapshot = hlt_ref.get(transaction=transaction)
    if not hlt_snapshot.exists:
        raise ValueError("HLT not found")

    hlt_data = hlt_snapshot.to_dict()
    shares_total = hlt_data.get("shares_total", 0)
    shares_sold = hlt_data.get("shares_sold", 0)
    shares_available = shares_total - shares_sold

    if shares_to_buy > shares_available:
        raise ValueError(f"Concurrency check failed: Requested {shares_to_buy} shares, but only {shares_available} are left.")

    # 1. Update HLT shares_sold
    transaction.update(hlt_ref, {
        "shares_sold": shares_sold + shares_to_buy,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })

    # 2. Write Holding record
    transaction.set(holding_ref, holding_data)


def handle(request: Request):
    """Handle Stripe webhook events for successful payments."""
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

    event_type = event["type"]

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})

        user_id = metadata.get("user_id")
        hlt_id = metadata.get("hlt_id")
        shares_to_buy_str = metadata.get("shares_to_buy")
        horse_microchip = metadata.get("horse_microchip")
        percentage_owned_str = metadata.get("percentage_owned")
        purchase_price_cents_str = metadata.get("purchase_price_cents")
        session_id = session.id

        if not all([user_id, hlt_id, shares_to_buy_str, horse_microchip, percentage_owned_str, purchase_price_cents_str]):
            print(f"Skipping checkout.session.completed: Missing metadata in session {session_id}")
            return jsonify({"received": True, "error": "Missing metadata"}), 200

        try:
            shares_to_buy = int(shares_to_buy_str)
            percentage_owned = float(percentage_owned_str)
            purchase_price_cents = int(purchase_price_cents_str)
        except ValueError as e:
            print(f"Error parsing metadata values: {e}")
            return jsonify({"received": True, "error": f"Parse error: {str(e)}"}), 200

        # Build holding record
        holding_ref = _get_db().collection("holdings").document()
        holding_data = {
            "id": holding_ref.id,
            "user_id": user_id,
            "hlt_id": hlt_id,
            "horse_microchip": horse_microchip,
            "shares_owned": shares_to_buy,
            "percentage_owned": percentage_owned,
            "purchase_price_cents": purchase_price_cents,
            "stripe_session_id": session_id,
            "status": "paid",
            "document_acknowledgements": {
                "term_sheet": True,
                "pds": True,
                "sa": True
            },
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP
        }

        # Run transaction
        transaction = _get_db().transaction()
        hlt_ref = _get_db().collection("hlts").document(hlt_id)

        try:
            process_purchase_transaction(transaction, hlt_ref, holding_ref, holding_data, shares_to_buy)
            print(f"Successfully processed purchase of {shares_to_buy} shares for user {user_id} on HLT {hlt_id}")
        except Exception as e:
            print(f"Transaction failed for session {session_id}: {e}")
            return jsonify({"error": f"Transaction failed: {str(e)}"}), 500

    return jsonify({"received": True}), 200
