# project/routes/main_routes.py

from flask import Blueprint, current_app, jsonify, request
# from flask_login import current_user, login_required
import datetime # For API calls and date handling

# project/__init__.py से db और अन्य एक्सटेंशन इम्पोर्ट करें
from .. import db
from ..models import User, UserSettings
# from ..forms import FullSettingsForm # हम JSON का उपयोग कर रहे हैं, इसलिए WTForm आवश्यक नहीं है
# Import helper functions from services
from ..services.prayer_time_service import get_api_prayer_times_for_date_from_service
from ..utils.template_helpers import user_settings_to_dict, user_profile_to_dict

main_bp = Blueprint('main', __name__)

# Removed @main_bp.route('/') and index() function

@main_bp.route('/settings', methods=['GET'])
def settings():
    # For now, return a dummy response as authentication is being overhauled
    return jsonify({"message": "Settings API is under construction for authentication."}), 200
