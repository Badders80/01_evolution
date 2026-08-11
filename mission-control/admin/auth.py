"""
Admin Authentication — Firebase Auth Middleware

Protects admin API endpoints with Firebase Authentication.
All /api/* routes require a valid Firebase ID token.
"""

from pathlib import Path
from functools import wraps
from flask import request, jsonify, current_app
import firebase_admin
from firebase_admin import credentials, auth

# Initialize Firebase Admin SDK (only once)
if not firebase_admin._apps:
    try:
        # Try to load from service account file (co-located in mission-control/credentials/)
        _cred_path = Path(__file__).resolve().parent / "credentials" / "firebase_service_account.json"
        cred = credentials.Certificate(str(_cred_path))
        firebase_admin.initialize_app(cred)
    except FileNotFoundError:
        # Fallback: use Application Default Credentials (for local dev with gcloud auth)
        firebase_admin.initialize_app()


def require_auth(f):
    """
    Decorator to require Firebase Authentication on admin endpoints.
    
    Expects: Authorization: Bearer <firebase_id_token>
    
    On success: Adds decoded token to request.user
    On failure: Returns 401 Unauthorized
    
    In TEST mode (app.config["TESTING"] = True), auth is bypassed.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth in test/debug mode or local requests
        if current_app.config.get("TESTING") or current_app.config.get("DEBUG") or request.remote_addr in ("127.0.0.1", "localhost", "::1"):
            return f(*args, **kwargs)

        
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid Authorization header. Expected: Bearer <token>"}), 401
        
        id_token = auth_header.split('Bearer ')[1]
        
        try:
            # Verify the ID token
            decoded_token = auth.verify_id_token(id_token)
            # Attach user info to request for downstream use
            request.user = decoded_token
            return f(*args, **kwargs)
        except auth.ExpiredIdTokenError:
            return jsonify({"error": "Token has expired. Please log in again."}), 401
        except auth.InvalidIdTokenError:
            return jsonify({"error": "Invalid token. Please log in again."}), 401
        except Exception as e:
            return jsonify({"error": f"Authentication failed: {str(e)}"}), 401
    
    return decorated_function


def get_current_user():
    """Get the current authenticated user from the request."""
    if not hasattr(request, 'user'):
        return None
    return request.user


def require_admin(f):
    """
    Decorator to require admin role (future enhancement).
    For now, just requires authentication.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user has admin claim (future)
        # user = get_current_user()
        # if not user or not user.get('admin', False):
        #     return jsonify({"error": "Admin access required"}), 403
        return require_auth(f)(*args, **kwargs)
    
    return decorated_function
