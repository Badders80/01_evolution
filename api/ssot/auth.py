"""
Firebase Authentication Middleware for SSOT API

Verifies Firebase ID tokens from the Authorization header.
Uses Application Default Credentials (ADC) on Cloud Functions,
or a service account file for local development.

Usage:
  from auth import require_auth
  @require_auth
  def my_route(request):
      ...
"""

from functools import wraps
from flask import request, jsonify
import firebase_admin
from firebase_admin import credentials, auth
import os

# Initialize Firebase Admin SDK (only once)
_firebase_app = None
if not firebase_admin._apps:
    try:
        # Try service account file (local dev)
        sa_path = os.path.join(os.path.dirname(__file__), "..", "firebase_service_account.json")
        if os.path.exists(sa_path):
            cred = credentials.Certificate(sa_path)
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            # ADC (Cloud Functions / gcloud auth)
            _firebase_app = firebase_admin.initialize_app()
    except Exception as e:
        print(f"Firebase init warning: {e}")


def require_auth(f):
    """
    Decorator to require Firebase Authentication.

    Expects: Authorization: Bearer <firebase_id_token>

    On success: Attaches decoded token to request.user
    On failure: Returns 401 Unauthorized
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header. Expected: Bearer <token>"}), 401

        id_token = auth_header.split("Bearer ")[1]

        try:
            decoded_token = auth.verify_id_token(id_token)
            request.user = decoded_token
            return f(*args, **kwargs)
        except auth.ExpiredIdTokenError:
            return jsonify({"error": "Token has expired. Please log in again."}), 401
        except auth.InvalidIdTokenError:
            return jsonify({"error": "Invalid token. Please log in again."}), 401
        except Exception as e:
            return jsonify({"error": f"Authentication failed: {str(e)}"}), 401

    return decorated_function
