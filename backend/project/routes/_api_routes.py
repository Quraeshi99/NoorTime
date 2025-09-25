# project/routes/api_routes.py
import pdb
from project.extensions import limiter
from flask import jsonify, request, current_app, g
import datetime
import json
from flask_smorest import Blueprint, abort
from webargs import fields
from webargs.flaskparser import use_args

from .. import db
from ..models import User, UserSettings
from ..schemas import InitialPrayerDataSchema, MessageSchema, GeocodeSchema, AutocompleteSchema, InitialPrayerDataArgsSchema
from ..services.prayer_time_service import (
    get_api_prayer_times_for_date_from_service,
    calculate_display_times_from_service,
    get_next_prayer_info_from_service,
    get_current_prayer_period_from_service,
    _get_single_prayer_info
)
from ..services.geocoding_service import get_geocoded_location_with_cache, get_autocomplete_suggestions
from ..utils.auth import jwt_optional, jwt_required, has_permission
from ..utils.time_utils import get_prayer_key_for_tomorrow

api_bp = Blueprint('API', __name__, url_prefix='/api')

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
@api_bp.arguments(InitialPrayerDataArgsSchema, location='query')
@api_bp.response(200, InitialPrayerDataSchema, description="Prayer data retrieved successfully.")
@api_bp.response(503, MessageSchema, description="Service Unavailable - Could not fetch data from the external prayer time API.")
@api_bp.response(500, MessageSchema, description="Internal Server Error.")
def initial_prayer_data(args):
    """
    Get all initial data for the prayer times screen.
    This is the main endpoint. It provides personalized data for logged-in users,
    especially if they are following a default Masjid.
    """
    pdb.set_trace()
    try:
        user = g.user if hasattr(g, 'user') else None
        is_authenticated = True if user else False
        
        # --- Initialize variables for the new community feature ---
        is_following_default_masjid = False
        default_masjid_info = None
        announcements = []

        # --- Determine the source of truth for prayer settings ---
        user_prayer_settings_obj = UserSettings() # Default empty settings
        time_format_pref = '12h'

        # 1. Check for a default followed Masjid first (highest priority for logged-in users)
        if user:
            time_format_pref = user.time_format_preference
            default_masjid_follow = user.default_masjid_follow
            if default_masjid_follow:
                is_following_default_masjid = True
                default_masjid = default_masjid_follow.masjid
                default_masjid_info = default_masjid
                announcements = default_masjid.announcements
                
                # Use Masjid's location and settings
                lat = default_masjid.default_latitude
                lon = default_masjid.default_longitude
                method_key = default_masjid.default_calculation_method
                city_name = default_masjid.default_city_name or default_masjid.name
                user_prayer_settings_obj = default_masjid.settings if default_masjid.settings else UserSettings()
            else:
                # 2. If not following a default, use request arguments
                req_lat = args.get('lat')
                req_lon = args.get('lon')
                if req_lat is not None and req_lon is not None:
                    lat, lon, method_key, city_name = req_lat, req_lon, args.get('method', 'Karachi'), args.get('city', "Custom Location")
                    user_prayer_settings_obj = user.settings if user.settings else UserSettings()
                # 3. Fallback to user's personal saved settings
                elif user.default_latitude and user.default_longitude:
                    lat, lon, method_key, city_name = user.default_latitude, user.default_longitude, user.default_calculation_method, user.default_city_name
                    user_prayer_settings_obj = user.settings if user.settings else UserSettings()
                # 4. Fallback to app default settings
                else:
                                    lat, lon, method_key, city_name = float(current_app.config['DEFAULT_LATITUDE']), float(current_app.config['DEFAULT_LONGITUDE']), current_app.config['DEFAULT_CALCULATION_METHOD'], "Default Location"
        else:
            # Guest user logic (same as before)
            req_lat = args.get('lat')
            req_lon = args.get('lon')
            if req_lat is not None and req_lon is not None:
                lat, lon, method_key, city_name = req_lat, req_lon, args.get('method', 'Karachi'), args.get('city', "Custom Location")
            else:
                                lat, lon, method_key, city_name = float(current_app.config['DEFAULT_LATITUDE']), float(current_app.config['DEFAULT_LONGITUDE']), current_app.config['DEFAULT_CALCULATION_METHOD'], "Default Location"

        # --- Fetch and Calculate Prayer Times (Core Logic) ---
        today_date = datetime.date.today()
        now_datetime = datetime.datetime.now()
        tomorrow_date = today_date + datetime.timedelta(days=1)
        day_after_tomorrow_date = today_date + datetime.timedelta(days=2)

        api_day_today = get_api_prayer_times_for_date_from_service(today_date, lat, lon, method_key)
        api_day_tomorrow = get_api_prayer_times_for_date_from_service(tomorrow_date, lat, lon, method_key)
        api_day_day_after_tomorrow = get_api_prayer_times_for_date_from_service(day_after_tomorrow_date, lat, lon, method_key)

        if not api_day_today or not api_day_tomorrow or not api_day_day_after_tomorrow:
            abort(503, message="Could not fetch prayer times from the prayer time service.")
        
        api_times_today = api_day_today.get('timings', {})
        api_times_tomorrow = api_day_tomorrow.get('timings', {})
        api_times_day_after_tomorrow = api_day_day_after_tomorrow.get('timings', {})

        display_times, needs_db_update = calculate_display_times_from_service(
            user_prayer_settings_obj, 
            api_times_today, 
            api_times_tomorrow, 
            current_app.config
        )
        
        if needs_db_update and user and not is_following_default_masjid:
            try:
                user.settings.last_api_times_for_threshold = json.dumps(api_times_today)
                db.session.commit()
            except Exception as e:
                db.session.rollback()

        last_api_times = json.loads(user_prayer_settings_obj.last_api_times_for_threshold) if user_prayer_settings_obj and user_prayer_settings_obj.last_api_times_for_threshold else {}

        current_period_info = get_current_prayer_period_from_service(api_times_today, api_times_tomorrow, now_datetime)
        current_prayer_name = current_period_info.get("name", "ISHA").upper()
        prayer_to_show_for_tomorrow_key = get_prayer_key_for_tomorrow(current_prayer_name, today_date)

        next_day_prayer_display = _get_single_prayer_info(
            prayer_to_show_for_tomorrow_key,
            api_times_tomorrow,
            user_prayer_settings_obj,
            api_times_day_after_tomorrow,
            last_api_times
        )
        
        if next_day_prayer_display:
            next_day_prayer_display['name'] = prayer_to_show_for_tomorrow_key

        date_info = api_day_today.get('date', {})
        gregorian_info = date_info.get('gregorian', {})
        hijri_info = date_info.get('hijri', {})

        response_data = {
            "currentLocationName": city_name,
            "currentPrayerPeriod": current_period_info,
            "prayerTimes": display_times,
            "dateInfo": {
                "gregorian": f"{gregorian_info.get('date')}, {gregorian_info.get('weekday', {}).get('en')}",
                "hijri": f"{hijri_info.get('date')} ({hijri_info.get('month', {}).get('en')} {hijri_info.get('year')} AH)"
            },
            "nextDayPrayerDisplay": next_day_prayer_display,
            "userPreferences": {
                "timeFormat": time_format_pref,
                "calculationMethod": method_key,
                "homeLatitude": lat,
                "homeLongitude": lon,
            },
            "isUserAuthenticated": is_authenticated,
            # --- New community feature fields ---
            "is_following_default_masjid": is_following_default_masjid,
            "default_masjid_info": default_masjid_info,
            "announcements": announcements
        }
        
        return response_data
    
    except Exception as e:
        current_app.logger.error(f"Error in initial_prayer_data: {str(e)}", exc_info=True)
        abort(500, message="Internal server error occurred.")

@api_bp.route('/client/settings', methods=['POST'])
@jwt_required
@has_permission('can_update_own_settings')
@api_bp.arguments({
    'name': fields.String(),
    'default_latitude': fields.Float(),
    'default_longitude': fields.Float(),
    'default_city_name': fields.String(),
    'default_calculation_method': fields.String(),
    'time_format_preference': fields.String(),
    'settings': fields.Dict(),
}, location='json')
@api_bp.response(200, MessageSchema, description="Settings updated successfully.")
@api_bp.response(400, MessageSchema, description="Bad Request - No data provided.")
@api_bp.response(403, MessageSchema, description="Forbidden to update prayer settings while following a default Masjid.")
@api_bp.response(500, MessageSchema, description="Failed to update settings due to a server error.")
@api_bp.doc(security=[{"Bearer": []}])
def update_client_settings(args):
    """
    Update settings for the authenticated user.
    This protected endpoint allows a logged-in user to update their general profile and detailed prayer time settings.
    Prayer time settings cannot be updated if the user is following a default Masjid.
    """
    user = g.user
    data = args
    if not data:
        abort(400, message="No data provided")

    # Check if user is trying to update prayer-specific settings while following a masjid
    is_following = user.default_masjid_follow is not None
    prayer_settings_keys = ['settings', 'default_latitude', 'default_longitude', 'default_city_name', 'default_calculation_method']
    is_updating_prayer_settings = any(key in data for key in prayer_settings_keys)

    if is_following and is_updating_prayer_settings:
        abort(403, message="You cannot update prayer settings while following a default Masjid. Please unfollow first.")

    # Update general fields
    general_fields = ['name', 'time_format_preference']
    for field in general_fields:
        if field in data:
            setattr(user, field, data[field])

    # Update prayer-related fields only if not following
    for field in prayer_settings_keys:
        if field in data and field != 'settings':
            setattr(user, field, data[field])

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
            'jummah_azan_time', 'jummah_khutbah_start_time', 'jummah_jamaat_time',
            'threshold_minutes'
        ]
        for field in settings_fields:
            if field in data['settings']:
                setattr(user.settings, field, data['settings'][field])

    try:
        db.session.commit()
        if user.settings and is_updating_prayer_settings:
            user.settings.last_api_times_for_threshold = None
            db.session.commit()

        return {"message": "Settings updated successfully."}
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating settings for user {user.email}: {e}", exc_info=True)
        abort(500, message="Failed to update settings due to a server error.")

@api_bp.route('/geocode', methods=['GET'])
@limiter.limit("50 per hour")
@api_bp.arguments(GeocodeSchema, location='query')
@api_bp.response(200, MessageSchema, description="Geocoding successful.") # Assuming a generic message schema for success
@api_bp.response(400, MessageSchema, description="Bad Request - City parameter is missing.")
@api_bp.response(404, MessageSchema, description="Not Found - The city could not be geocoded.")
@api_bp.response(503, MessageSchema, description="Service Unavailable - The geocoding service is temporarily down.")
def geocode_city(args):
    print("ENTERING geocode_city")
    """
    Geocode a city to get its latitude and longitude.
    This endpoint takes a city name and returns its geographic coordinates.
    """
    city_name = args.get('city')
    if not city_name or len(city_name.strip()) < 2:
        abort(400, message="Valid city name parameter is required")
    
    try:
        print("ENTERING try block in geocode_city")
        location_data = get_geocoded_location_with_cache(city_name.strip())
        if location_data and "error" not in location_data:
            return location_data # Return dict for Smorest
        else:
            abort(404, message=location_data.get("error", "Failed to geocode location"))
    except Exception as e:
        current_app.logger.error(f"Error in geocode_city: {str(e)}", exc_info=True)
        abort(503, message="Geocoding service temporarily unavailable")

@api_bp.route('/geocode/autocomplete', methods=['GET'])
@limiter.limit("100 per hour")
@api_bp.arguments(AutocompleteSchema, location='query')
@api_bp.response(200, MessageSchema, description="Suggestions retrieved successfully.") # Assuming a generic message schema for success
@api_bp.response(400, MessageSchema, description="Bad Request - Query parameter is missing or too short.")
@api_bp.response(500, MessageSchema, description="Failed to fetch autocomplete suggestions.")
@api_bp.response(503, MessageSchema, description="Autocomplete service temporarily unavailable.")
def autocomplete_city(args):
    """
    Get city autocomplete suggestions.
    Provides a list of potential city names based on a partial query.
    """
    query = args.get('query')
    if not query or len(query.strip()) < 2:
        abort(400, message="Valid query parameter with at least 2 characters is required")
    
    try:
        suggestions = get_autocomplete_suggestions(query.strip())
        if suggestions and "error" not in suggestions:
            return suggestions # Return dict for Smorest
        else:
            abort(500, message=suggestions.get("error", "Failed to fetch autocomplete suggestions"))
    except Exception as e:
        current_app.logger.error(f"Error in autocomplete_city: {str(e)}", exc_info=True)
        abort(503, message="Autocomplete service temporarily unavailable")
