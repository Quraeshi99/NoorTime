# project/routes/api_routes.py
from project.extensions import limiter
from flask import jsonify, request, current_app, g
import datetime
import json
from zoneinfo import ZoneInfo
import zoneinfo
from flask_smorest import Blueprint, abort
from webargs import fields
from webargs.flaskparser import use_args
from typing import Dict, Any, Optional, Tuple

from .. import db
from ..models import User, UserSettings
from ..schemas import InitialPrayerDataSchema, MessageSchema, GeocodeSchema, AutocompleteSchema, InitialPrayerDataArgsSchema
from ..services.prayer_time_service import (
    get_api_prayer_times_for_date_from_service,
    calculate_display_times_from_service,
    get_next_prayer_info_from_service,
    get_current_prayer_period_from_service,
    get_single_prayer_info
)
from ..services.geocoding_service import get_geocoded_location_with_cache, get_autocomplete_suggestions
from ..utils.auth import jwt_optional, jwt_required, has_permission
from ..utils.time_utils import get_prayer_key_for_tomorrow
from prometheus_client import generate_latest

# Import the new schedule service
from ..services.schedule_service import get_or_generate_monthly_schedule

api_bp = Blueprint('API', __name__, url_prefix='/api')

@api_bp.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; version=0.0.4; charset=utf-8'}

def get_prayer_settings_from_user(user: Optional[User], args: Dict[str, Any]) -> Tuple[float, float, int, int, int, str, str]:
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
        user_settings = user.settings if user and user.settings else UserSettings() # Ensure user_settings object exists

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
                int(user_settings.high_latitude_method_id or high_lat_id),
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
def initial_prayer_data(args: Dict[str, Any]) -> Dict[str, Any]:
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
    # TODO: User timezone should be fetched from user settings in the database.
    user_timezone_str = user.settings.timezone if user and hasattr(user, 'settings') and user.settings and hasattr(user.settings, 'timezone') else 'UTC'
    user_tz = zoneinfo.ZoneInfo(user_timezone_str)

    now_datetime = datetime.datetime.now(user_tz)
    today_date = now_datetime.date()
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
        current_app.config,
        calculation_date=today_date
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

    next_day_prayer_display = get_single_prayer_info(
        prayer_to_show_for_tomorrow_key,
        api_times_tomorrow,
        user_prayer_settings_obj,
        api_times_day_after_tomorrow,
        last_api_times,
        calculation_date=tomorrow_date
    )
    
    if next_day_prayer_display:
        next_day_prayer_display['name'] = prayer_to_show_for_tomorrow_key

    date_info = api_day_today.get('date', {})
    gregorian_info = date_info.get('gregorian', {})
    hijri_info = date_info.get('hijri', {})

    # --- New: Check for proactively generated next month's schedule ---
    next_schedule_url = None
    # Determine the year and month for the *next* month
    first_day_of_current_month = today_date.replace(day=1)
    # Adding 32 days guarantees we land in the next month
    first_day_of_next_month = first_day_of_current_month + datetime.timedelta(days=32)
    next_month_year = first_day_of_next_month.year
    next_month_month = first_day_of_next_month.month

    # Efficiently check if the next month's schedule exists in the cache
    # The owner is the user or the masjid they follow
    owner_id = default_masjid_info.id if is_following_default_masjid else user.id
    if owner_id:
        schedule_exists = db.session.query(MonthlyScheduleCache.id).filter_by(
            owner_id=owner_id,
            year=next_month_year,
            month=next_month_month
        ).first() is not None

        if schedule_exists:
            # Construct the URL for the frontend to call
            # This is not hardcoded and uses Flask's URL building
            from flask import url_for
            next_schedule_url = url_for(
                'API.get_monthly_schedule', 
                year=next_month_year, 
                month=next_month_month, 
                _external=False # Use a relative URL
            )

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
            "calculationMethod": method_id,
            "homeLatitude": lat,
            "homeLongitude": lon,
        },
        "isUserAuthenticated": is_authenticated,
        # --- New community feature fields ---
        "is_following_default_masjid": is_following_default_masjid,
        "default_masjid_info": default_masjid_info,
        "announcements": announcements,
        # --- New: URL for proactive client-side caching ---
        "next_schedule_url": next_schedule_url
    }
    current_app.logger.info(f"Response data: {response_data}")
    return response_data

@api_bp.route('/v1/schedule/monthly', methods=['GET'])
@jwt_required
def get_monthly_schedule():
    """
    API endpoint to get the pre-calculated, state-based monthly schedule
    for the currently logged-in user. This is the primary endpoint for the
    "Schedule-Based" architecture.
    """
    user = g.user if hasattr(g, 'user') else None
    if not user:
        # This should technically not be reached if @jwt_required works as expected
        return jsonify({"error": "Authentication required."}), 401

    try:
        # Get year and month from query params, default to current UTC month
        now = datetime.datetime.utcnow()
        year = request.args.get('year', default=now.year, type=int)
        month = request.args.get('month', default=now.month, type=int)

        # The service function handles all complex logic:
        # - Determines if user is individual or follower
        # - Checks for a cached schedule on the server
        # - Re-uses a Masjid's schedule for followers
        # - Generates, caches, and returns the schedule if not found
        schedule_data = get_or_generate_monthly_schedule(
            user_id=user.id,
            year=year,
            month=month
        )

        if not schedule_data:
            return jsonify({"error": "Could not generate or retrieve schedule."}), 500

        return jsonify(schedule_data), 200

    except Exception as e:
        current_app.logger.error(f"Error in /v1/schedule/monthly endpoint: {e}", exc_info=True)
        return jsonify({"error": "An unexpected server error occurred."}), 500