# project/routes/main_routes.py

from flask import Blueprint, render_template, current_app, jsonify, request, flash, redirect, url_for
from flask_login import current_user, login_required
import datetime # For API calls and date handling

# project/__init__.py से db और अन्य एक्सटेंशन इम्पोर्ट करें
from .. import db
from ..models import User, UserSettings
# from ..forms import FullSettingsForm # हम JSON का उपयोग कर रहे हैं, इसलिए WTForm आवश्यक नहीं है
# Import helper functions from services
from ..services.prayer_time_service import get_api_prayer_times_for_date_from_service
from ..utils.template_helpers import user_settings_to_dict, user_profile_to_dict

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html', title="Prayer Times")

@main_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_settings:
        current_app.logger.warning(f"UserSettings not found for user {current_user.id}, creating defaults.")
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating default UserSettings for user {current_user.id}: {e}", exc_info=True)
            flash("Error loading settings. Please try again.", "danger")
            return redirect(url_for('main.index'))

    user_lat = current_user.default_latitude if current_user.default_latitude is not None else float(current_app.config.get('DEFAULT_LATITUDE'))
    user_lon = current_user.default_longitude if current_user.default_longitude is not None else float(current_app.config.get('DEFAULT_LONGITUDE'))
    user_calc_method_key = current_user.default_calculation_method or current_app.config.get('DEFAULT_CALCULATION_METHOD')
    
    today_api_times = get_api_prayer_times_for_date_from_service(
        date_obj=datetime.date.today(),
        latitude=user_lat,
        longitude=user_lon,
        calculation_method_key=user_calc_method_key,
        force_refresh=True
    )

    if not today_api_times:
        today_api_times = {}
        flash("Could not fetch reference API prayer times.", "warning")

    calculation_method_choices_for_template = current_app.config.get('CALCULATION_METHOD_CHOICES', [])

    return render_template('settings.html', 
                           title="Settings", 
                           user_settings=user_settings_to_dict(user_settings),
                           user_profile=user_profile_to_dict(current_user),
                           api_times_for_reference=today_api_times,
                           calculation_method_choices=calculation_method_choices_for_template)
