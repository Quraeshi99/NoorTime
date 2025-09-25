# project/routes/api_routes.py
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

def get_prayer_settings_from_user(user, args):
    """
    Determines the correct prayer time settings (location, method, etc.) based on a hierarchy:
    1. A followed Masjid's settings.
    2. A custom location search from the user.
    3. The user's saved personal settings.
    4. The application's default settings.
    """
    # Default values from app config
    lat = float(current_app.config.get('DEFAULT_LATITUDE'))
    lon = float(current_app.config.get('DEFAULT_LONGITUDE'))
    method_id = int(current_app.config.get('DEFAULT_CALCULATION_METHOD_ID', 3)) # Default to 3 (MWL)
    asr_id = 0 # Default to 0 (Standard)
    high_lat_id = 1 # Default to 1 (Middle of the Night)
    city_name = "Default Location"
    source = "app_default"

    # 1. Logged-in user logic
    if user:
        user_settings = user.settings if user.settings else UserSettings() # Ensure user_settings object exists

        # Priority 1: Followed Masjid
        default_masjid_follow = user.default_masjid_follow
        if default_masjid_follow:
            masjid = default_masjid_follow.masjid
            masjid_settings = masjid.settings if masjid.settings else UserSettings()
            return (
                masjid.default_latitude,
                masjid.default_longitude,
                int(masjid.default_calculation_method_id),
                int(masjid_settings.asr_juristic_id),
                int(masjid_settings.high_latitude_method_id),
                masjid.default_city_name or masjid.name,
                "followed_masjid"
            )

        # Priority 2: Custom Location Search (using user's own settings)
        req_lat = args.get('lat')
        req_lon = args.get('lon')
        if req_lat is not None and req_lon is not None:
            # IMPORTANT: Only apply high-latitude method if the *searched* location is in a high latitude.
            # The user's own location is irrelevant for this calculation.
            high_lat_id_to_use = int(user_settings.high_latitude_method_id or high_lat_id) if req_lat > 48.0 else 0

            return (
                req_lat,
                req_lon,
                int(user.default_calculation_method_id or method_id),
                int(user_settings.asr_juristic_id or asr_id),
                high_lat_id_to_use,
                args.get('city', "Custom Location"),
                "custom_location_with_user_settings"
            )

        # Priority 3: User's Saved Personal Settings
        if user.default_latitude and user.default_longitude and user.default_calculation_method_id is not None:
            return (
                user.default_latitude,
                user.default_longitude,
                int(user.default_calculation_method_id),
                int(user_settings.asr_juristic_id or asr_id),
                int(user_settings.high_latitude_method_id or high_lat_id),
                user.default_city_name,
                "user_personal_settings"
            )

    # 4. Guest user or user with no settings (custom location search)
    else:
        req_lat = args.get('lat')
        req_lon = args.get('lon')
        if req_lat is not None and req_lon is not None:
            # For guests, we can't use saved settings, so we take method from args or use app default
            guest_method_id = args.get('method', method_id)
            guest_asr_id = args.get('school', asr_id)
            guest_high_lat_id = args.get('latitudeAdjustmentMethod', high_lat_id)
            return (
                req_lat, req_lon, int(guest_method_id), int(guest_asr_id), int(guest_high_lat_id),
                args.get('city', "Custom Location"),
                "guest_custom_location"
            )

    # Fallback to app default for all other cases
    return lat, lon, method_id, asr_id, high_lat_id, city_name, source

@api_bp.route('/initial_prayer_data')
@jwt_optional
@api_bp.arguments(InitialPrayerDataArgsSchema, location='query')
#@api_bp.response(200, InitialPrayerDataSchema, description="Prayer data retrieved successfully.")
@api_bp.response(503, MessageSchema, description="Service Unavailable - Could not fetch data from the external prayer time API.")
@api_bp.response(500, MessageSchema, description="Internal Server Error.")
def initial_prayer_data(args):
    """
    Get all initial data for the prayer times screen.
    This is the main endpoint. It provides personalized data for logged-in users,
    especially if they are following a default Masjid.
    """
    user = g.user if hasattr(g, 'user') else None
    is_authenticated = True if user else False
    
    # --- Determine the source of truth for prayer settings ---
    user_prayer_settings_obj = user.settings if user and user.settings else UserSettings()
    time_format_pref = user.time_format_preference if user else '12h'

    lat, lon, method_id, asr_id, high_lat_id, city_name, settings_source = get_prayer_settings_from_user(user, args)

    # If settings came from a followed masjid, get additional info
    is_following_default_masjid = (settings_source == "followed_masjid")
    default_masjid_info = user.default_masjid_follow.masjid if is_following_default_masjid else None
    announcements = default_masjid_info.announcements if default_masjid_info else []

    # --- Fetch and Calculate Prayer Times (Core Logic) ---
    today_date = datetime.date.today()
    now_datetime = datetime.datetime.now()
    tomorrow_date = today_date + datetime.timedelta(days=1)
    day_after_tomorrow_date = today_date + datetime.timedelta(days=2)

    api_day_today = get_api_prayer_times_for_date_from_service(today_date, lat, lon, method_id, asr_id, high_lat_id)
    api_day_tomorrow = get_api_prayer_times_for_date_from_service(tomorrow_date, lat, lon, method_id, asr_id, high_lat_id)
    api_day_day_after_tomorrow = get_api_prayer_times_for_date_from_service(day_after_tomorrow_date, lat, lon, method_id, asr_id, high_lat_id)

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
    current_app.logger.info(f"Response data: {response_data}")
    return response_data