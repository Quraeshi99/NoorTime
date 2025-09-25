# project/routes/main_routes.py

from flask import current_app, jsonify, request
from flask_smorest import Blueprint, abort
import datetime # For API calls and date handling

# project/__init__.py से db और अन्य एक्सटेंशन इम्पोर्ट करें
from .. import db
from ..models import User, UserSettings
from ..schemas import MessageSchema
# Import helper functions from services
from ..services.prayer_time_service import get_api_prayer_times_for_date_from_service
from ..utils.template_helpers import user_settings_to_dict, user_profile_to_dict

main_bp = Blueprint('Main', __name__, url_prefix='/')

@main_bp.route('/')
@main_bp.response(200, MessageSchema)
def index():
    """
    Main endpoint for the API.
    """
    return {"message": "Welcome to the NoorTime API!"}

@main_bp.route('/settings')
@main_bp.response(200, MessageSchema)
def settings():
    """
    Get the application settings. (Under construction)
    """
    # For now, return a dummy response as authentication is being overhauled
    return {"message": "Settings API is under construction for authentication."}