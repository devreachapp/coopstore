# auth/routes.py

import bcrypt

from flask import Blueprint, request, jsonify, current_app, session
from datetime import datetime, timedelta
from functools import wraps
import jwt,requests
from app.models import db,Tenant
from app.auth import bp as auth_bp



SECRET_KEY = 'naso'

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", None)
        print("Authorization header:", auth_header)

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        print("Token received:", token)

        if not token:
            return jsonify({"message": "Token is missing"}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            print("Decoded JWT data:", data)
            current_user = Tenant.query.get(data["user_id"])
            if not current_user:
                return jsonify({"message": "User not found"}), 404
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 401
        except Exception as e:
            import traceback; traceback.print_exc()
            return jsonify({"message": "Token verification failed"}), 500

        return f(current_user, *args, **kwargs)
    return decorated


import jwt
import datetime
from datetime import timezone
# --- On CoopMart Backend ---
def create_coopmart_jwt(tenant_id: int) -> str:
    """
    Generates a session JWT for CoopMart matching your token_required decorator.
    """
    payload = {
        "user_id": tenant_id,  # Matches: data["user_id"] in token_required
        "iat": datetime.datetime.now(timezone.utc),
        "exp": datetime.datetime.now(timezone.utc) + datetime.timedelta(days=7)
    }
    
    # Use the same SECRET_KEY imported in your auth module
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

