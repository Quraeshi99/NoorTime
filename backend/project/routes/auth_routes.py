# project/routes/auth_routes.py

from flask_smorest import Blueprint
# We will keep current_user and login_required for future JWT validation
from flask_login import login_required, current_user

# The auth_bp blueprint will remain, but its routes will be removed.
# Later, we might add a route here for JWT validation if needed.
auth_bp = Blueprint('auth', __name__)

# All authentication routes (register, login, logout) are now handled by Supabase on the frontend.
# This file will be empty for now, or can be used for JWT validation endpoints later.
