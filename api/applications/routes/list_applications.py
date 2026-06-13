"""
List Applications (Admin Only)

Returns all ownership applications for admin review.
"""

import os
from flask import Request, jsonify
from google.cloud import firestore


def handle(request: Request):
    """List all applications (admin only)."""
    if request.method != "GET":
        return jsonify({"error": "Method not allowed. Use GET."}), 405

    # Check if user is admin
    if not hasattr(request, "user"):
        return jsonify({"error": "Authentication required"}), 401

    user_email = request.user.get("email", "")
    admin_emails = os.getenv("ADMIN_EMAILS", "admin@evolutionstables.nz").split(",")

    if user_email not in admin_emails:
        return jsonify({"error": "Admin access required"}), 403

    try:
        db = firestore.Client()
        apps_ref = db.collection("applications")
        apps = apps_ref.order_by("created_at", direction="DESCENDING").stream()

        applications = []
        for app in apps:
            app_data = app.to_dict()
            app_data["id"] = app.id
            applications.append(app_data)

        return jsonify({
            "success": True,
            "applications": applications,
            "count": len(applications),
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch applications: {str(e)}"}), 500
