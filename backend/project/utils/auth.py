# project/utils/auth.py
import requests
from functools import wraps
from flask import request, jsonify, current_app, g
import jwt
from jwt import PyJWKClient
import time
from datetime import datetime

from .. import db
from ..models import User, Permission, UserPermission, RolePermission # Import new models
from .constants import Roles # Import the new Roles class

# Simple in-memory cache for JWKS
jwks_cache = {
    "keys": None,
    "expiry": 0
}

def get_jwks_client():
    """Fetches and caches Supabase JWKS."""
    global jwks_cache
    if jwks_cache["keys"] and jwks_cache["expiry"] > time.time():
        return jwks_cache["keys"]

    try:
        supabase_url = current_app.config.get('SUPABASE_URL')
        if not supabase_url:
            current_app.logger.error("SUPABASE_URL is not configured.")
            return None
        
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        jwks_client = PyJWKClient(jwks_url)
        jwks_cache["keys"] = jwks_client
        jwks_cache["expiry"] = time.time() + 3600 # Cache for 1 hour
        current_app.logger.info("Successfully fetched and cached JWKS from Supabase.")
        return jwks_client
    except Exception as e:
        current_app.logger.error(f"Failed to fetch JWKS: {e}", exc_info=True)
        return None

def _get_or_create_user_from_jwt(payload):
    """
    Finds a user in the local DB from the JWT payload, or creates one.
    Maps Supabase roles to local application roles.
    Also updates the user's last_seen_at timestamp.
    """
    supabase_id = payload.get("sub")
    if not supabase_id:
        return None

    user = User.query.filter_by(supabase_user_id=supabase_id).first()
    if user:
        # Update last_seen_at for existing user
        user.last_seen_at = datetime.utcnow()
        # No commit here, will be committed below
    
    else:
        email = payload.get("email")
        if not email:
            return None

        user = User.query.filter_by(email=email).first()
        if user:
            user.supabase_user_id = supabase_id
            user.last_seen_at = datetime.utcnow()
        else:
            supabase_role = payload.get("role")
            app_role = Roles.SUPER_ADMIN if supabase_role == 'service_role' else Roles.CLIENT
            user = User(
                supabase_user_id=supabase_id, 
                email=email, 
                role=app_role,
                last_seen_at=datetime.utcnow() # Set on creation
            )
            db.session.add(user)
    
    try:
        db.session.commit()
        current_app.logger.info(f"Authenticated and updated last_seen for user {user.id} (Supabase ID {supabase_id})")
        return user
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"DB error creating/linking user for sub {supabase_id}: {e}", exc_info=True)
        return None

def _load_user_permissions(user):
    """
    Loads all active permissions for a given user.
    Combines role-based permissions with user-specific overrides.
    """
    active_permissions = set()

    # 1. Load permissions based on the user's role
    role_perms = db.session.query(Permission.name).join(RolePermission).filter(RolePermission.role_name == user.role).all()
    for perm_name, in role_perms:
        active_permissions.add(perm_name)

    # 2. Apply user-specific overrides
    user_overrides = db.session.query(Permission.name, UserPermission.has_permission).join(UserPermission).filter(UserPermission.user_id == user.id).all()
    for perm_name, has_perm in user_overrides:
        if has_perm:
            active_permissions.add(perm_name)
        else:
            active_permissions.discard(perm_name) # Remove if explicitly revoked
            
    return active_permissions

def _validate_token_and_get_user():
    """Helper function to validate token and set g.user and g.user_permissions. Returns True on success."""
    token = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    if not token:
        return False, ("Authentication token is missing!", 401)

    jwks_client = get_jwks_client()
    if not jwks_client:
        return False, ("Authentication service is currently unavailable.", 503)

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        supabase_url = current_app.config.get('SUPABASE_URL')
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="authenticated",
            issuer=f"{supabase_url}/auth/v1"
        )
        user = _get_or_create_user_from_jwt(payload)
        if not user:
            return False, ("Could not identify or create user profile.", 404)
        g.user = user
        g.user_permissions = _load_user_permissions(user) # Load and store permissions
        return True, None
    except jwt.ExpiredSignatureError:
        return False, ("Token has expired!", 401)
    except jwt.InvalidTokenError:
        return False, ("Invalid authentication token!", 401)
    except Exception as e:
        current_app.logger.error(f"Internal server error during token validation: {e}", exc_info=True)
        return False, ("Internal server error during authentication.", 500)

def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        success, error = _validate_token_and_get_user()
        if not success:
            message, code = error
            return jsonify({"error": message}), code
        return f(*args, **kwargs)
    return decorated_function

def jwt_optional(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.user = None
        g.user_permissions = set() # Initialize empty set for guest
        auth_header = request.headers.get("authorization")
        if auth_header:
            success, _ = _validate_token_and_get_user() # Attempt to validate, result sets g.user and g.user_permissions or not
            if not success: # If validation failed, clear g.user and g.user_permissions
                g.user = None
                g.user_permissions = set()
        return f(*args, **kwargs)
    return decorated_function

def has_permission(permission_name):
    def decorator(f):
        @wraps(f)
        @jwt_required
        def decorated_function(*args, **kwargs):
            if permission_name not in g.user_permissions:
                return jsonify({"error": f"Permission '{permission_name}' required."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator