# project/routes/api_routes.py
from project.extensions import limiter
from flask import Blueprint, jsonify, request, current_app, g
import datetime

from .. import db
from ..models import User, UserSettings
from ..services.prayer_time_service import (
    get_api_prayer_times_for_date_from_service,
    calculate_display_times_from_service,
    get_next_prayer_info_from_service,
    get_current_prayer_period_from_service,
    get_geocoded_location
)
from ..utils.prayer_display_helper import get_prayer_info
from ..utils.auth import jwt_optional, has_permission # Import new decorators

api_bp = Blueprint('api', __name__)

def get_request_location_and_method(user=None):
    """Helper to get location and method from request args, user profile, or app defaults."""
    req_lat = request.args.get('lat', type=float)
    req_lon = request.args.get('lon', type=float)
    req_method = request.args.get('method')
    req_city = request.args.get('city')

    if req_lat is not None and req_lon is not None and req_method is not None:
        return req_lat, req_lon, req_method, req_city or "Custom Location"
    
    if user and user.default_latitude and user.default_longitude and user.default_calculation_method:
        return user.default_latitude, user.default_longitude, user.default_calculation_method, user.default_city_name or "Saved Location"

    lat = float(current_app.config.get('DEFAULT_LATITUDE'))
    lon = float(current_app.config.get('DEFAULT_LONGITUDE'))
    method_key = current_app.config.get('DEFAULT_CALCULATION_METHOD')
    city_name = "Default Location"
    return lat, lon, method_key, city_name

@api_bp.route('/initial_prayer_data')
@jwt_optional
def initial_prayer_data():
    """Public endpoint for prayer data, enhanced for authenticated users."""
    try:
        user = g.user if hasattr(g, 'user') else None
        lat, lon, method_key, city_name = get_request_location_and_method(user)
        
        user_prayer_settings_obj = user.settings if user and user.settings else UserSettings()
        time_format_pref = user.time_format_preference if user else '12h'
        is_authenticated = True if user else False

        today_date = datetime.date.today()
        tomorrow_date = today_date + datetime.timedelta(days=1)

        api_times_today = get_api_prayer_times_for_date_from_service(today_date, lat, lon, method_key)
        api_times_tomorrow = get_api_prayer_times_for_date_from_service(tomorrow_date, lat, lon, method_key)

        if not api_times_today:
            return jsonify({"error": "Could not fetch prayer times from external API."}), 503
        
        display_times = calculate_display_times_from_service(user_prayer_settings_obj, api_times_today, current_app.config)
        tomorrow_fajr_display = get_prayer_info("Fajr", api_times_tomorrow, user_prayer_settings_obj)
        
        return jsonify({
            "currentLocationName": city_name,
            "prayerTimes": display_times,
            "dateInfo": {
                "gregorian": f"{api_times_today.get('gregorian_date')}, {api_times_today.get('gregorian_weekday')}",
                "hijri": f"{api_times_today.get('hijri_date')} ({api_times_today.get('hijri_month_en')} {api_times_today.get('hijri_year')} AH)"
            },
            "tomorrowFajrDisplay": tomorrow_fajr_display,
            "userPreferences": {
                "timeFormat": time_format_pref,
                "calculationMethod": method_key,
                "homeLatitude": lat,
                "homeLongitude": lon,
            },
            "isUserAuthenticated": is_authenticated
        })
    
    except Exception as e:
        current_app.logger.error(f"Error in initial_prayer_data: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error occurred."}), 500

@api_bp.route('/client/settings', methods=['POST'])
@has_permission('can_update_own_settings') # Now requires specific permission
def update_client_settings():
    """
    Allows an authenticated Client to update their personal settings.
    """
    user = g.user # g.user is set by the @jwt_required decorator
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Update fields in the User (Client) model
    user_fields = ['name', 'default_latitude', 'default_longitude', 'default_city_name', 'default_calculation_method', 'time_format_preference']
    for field in user_fields:
        if field in data:
            setattr(user, field, data[field])

    # Update fields in the UserSettings model
    if 'settings' in data and isinstance(data['settings'], dict):
        if not user.settings:
            user.settings = UserSettings(user_id=user.id)
            db.session.add(user.settings)
        
        settings_fields = [
            'fajr_is_fixed', 'fajr_fixed_azan', 'fajr_fixed_jamaat', 'fajr_azan_offset', 'fajr_jamaat_offset',
            'dhuhr_is_fixed', 'dhuhr_fixed_azan', 'dhuhr_fixed_jamaat', 'dhuhr_azan_offset', 'dhuhr_jamaat_offset',
            'asr_is_fixed', 'asr_fixed_azan', 'asr_fixed_jamaat', 'asr_azan_offset', 'asr_jamaat_offset',
            'maghrib_is_fixed', 'maghrib_fixed_azan', 'maghrib_fixed_jamaat', 'maghrib_azan_offset', 'maghrib_jamaat_offset',
            'isha_is_fixed', 'isha_fixed_azan', 'isha_fixed_jamaat', 'isha_azan_offset', 'isha_jamaat_offset',
            'jummah_azan_time', 'jummah_khutbah_start_time', 'jummah_jamaat_time'
        ]
        for field in data['settings']:
            if field in data['settings']:
                setattr(user.settings, field, data['settings'][field])

    try:
        db.session.commit()
        return jsonify({"message": "Settings updated successfully."}), 200
    except Exception as e:
        current_app.logger.error(f"Error updating settings for user {user.email}: {e}", exc_info=True)
        return jsonify({"error": "Failed to update settings due to a server error."}), 500

@api_bp.route('/geocode', methods=['GET'])
@limiter.limit("50 per hour")
def geocode_city():
    # This remains a public endpoint
    city_name = request.args.get('city')
    if not city_name or len(city_name.strip()) < 2:
        return jsonify({"error": "Valid city name parameter is required"}), 400
    
    try:
        location_data = get_geocoded_location(city_name.strip(), current_app.config.get('OPENWEATHERMAP_API_KEY'))
        if location_data and "error" not in location_data:
            return jsonify(location_data)
        else:
            return jsonify({"error": location_data.get("error", "Failed to geocode location")}), 404
    except Exception as e:
        current_app.logger.error(f"Error in geocode_city: {str(e)}", exc_info=True)
        return jsonify({"error": "Geocoding service temporarily unavailable"}), 503
