from functools import wraps
from flask import request, jsonify, g
from ..models.jwt_manager import decode_and_validate

def _bearer_token():
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    return auth.split(" ", 1)[1].strip()

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _bearer_token()
        if not token:
            return jsonify({"error": "missing bearer token"}), 401
        try:
            payload = decode_and_validate(token, expected_typ="access")
            # expõe dados úteis no request context
            g.user_id   = payload.get("uid")
            g.session_id= payload.get("sid")
            g.subject   = payload.get("sub")
            g.jwt       = payload
        except Exception as e:
            return jsonify({"error": "invalid token", "detail": str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper
