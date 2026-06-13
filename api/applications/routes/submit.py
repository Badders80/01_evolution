"""
Submit Ownership Application

Creates a new ownership application record and sends email notification to admin.
"""

import os
from flask import Request, jsonify
from google.cloud import firestore

_DB = None

def _get_db():
    global _DB
    if _DB is None:
        _DB = firestore.Client()
    return _DB


def handle(request: Request):
    """Submit a new ownership application."""
    if request.method != "POST":
        return jsonify({"error": "Method not allowed. Use POST."}), 405

    data = request.get_json(force=True)
    user_id = data.get("user_id")
    hlt_id = data.get("hlt_id")
    email = data.get("email")
    name = data.get("name")
    units_requested = data.get("units_requested", 1)
    message = data.get("message", "")

    # Validate required fields
    required_fields = ["user_id", "hlt_id", "email", "name", "units_requested"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    try:
        # Get or create user document
        user_ref = _get_db().collection("users").document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            # Lazy create user document
            user_data = {"email": email, "created_at": firestore.SERVER_TIMESTAMP}
            user_ref.set(user_data)

        # Create application record
        application_data = {
            "user_id": user_id,
            "hlt_id": hlt_id,
            "email": email,
            "name": name,
            "units_requested": units_requested,
            "message": message,
            "status": "pending",
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }

        # Create application document
        app_ref = _get_db().collection("applications").document()
        app_ref.set(application_data)

        # Send email notification to admin
        _send_application_email(
            to_email=os.getenv("ADMIN_EMAIL", "admin@evolutionstables.nz"),
            user_name=name,
            user_email=email,
            hlt_id=hlt_id,
            units_requested=units_requested,
            message=message,
        )

        return jsonify({
            "success": True,
            "application_id": app_ref.id,
            "status": "pending",
        }), 200

    except Exception as e:
        return jsonify({"error": f"Application failed: {str(e)}"}), 500


def _send_application_email(to_email: str, user_name: str, user_email: str, hlt_id: str, units_requested: int, message: str):
    """
    Send email notification to admin when new application received.
    
    TODO: Implement actual email sending using Gmail API or SendGrid
    For now, this is a placeholder that logs the email content.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    subject = f"New Ownership Application: {hlt_id} by {user_name}"
    body = f"""
New ownership application received:

Applicant: {user_name} ({user_email})
Campaign: {hlt_id}
Units Requested: {units_requested}
Message: {message or 'None'}

Status: Pending review
"""
    
    logger.info(f"Sending email to {to_email}: {subject}")
    logger.info(f"Body: {body}")
    
    # TODO: Implement actual email sending
    # Options:
    # 1. Gmail API (using existing email-ingest infrastructure)
    # 2. SendGrid (third-party email service)
    # 3. Firebase Functions email trigger
    # 4. Simple SMTP (if Gmail SMTP is configured)
