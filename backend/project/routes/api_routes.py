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
from ..models import User, UserSettings, GuestProfile
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

def get_prayer_settings_from_user(user: Optional[User], args: Dict[str, Any]) -> Tuple[float, float, int, int, int, str, str, Optional[User]]:
    """
    Determines the correct prayer time settings (location, method, etc.) based on a hierarchy:
    1. A guest's followed Masjid.
    2. A logged-in user's followed Masjid.
    3. A custom location search from the user.
    4. The user's saved personal settings.
    5. The application's default settings.
    
    Returns a tuple including the settings and the masjid object if applicable.
    """
    # Default values from app config
    lat = float(current_app.config.get('DEFAULT_LATITUDE'))
    lon = float(current_app.config.get('DEFAULT_LONGITUDE'))
    method_id = int(current_app.config.get('DEFAULT_CALCULATION_METHOD_ID', 3)) # Default to 3 (MWL)
    asr_id = 0 # Default to 0 (Standard)
    high_lat_id = 1 # Default to 1 (Middle of the Night)
    city_name = "Default Location"
    source = "app_default"
    followed_masjid = None

    # Priority 1: Guest user with a followed Masjid
    device_id = g.device_id if hasattr(g, 'device_id') else None
    if not user and device_id:
        guest_profile = GuestProfile.query.filter_by(device_id=device_id).first()
        if guest_profile and guest_profile.followed_masjid:
            masjid = guest_profile.followed_masjid
            masjid_settings = masjid.settings if masjid.settings else UserSettings()
            return (
                masjid.default_latitude,
                masjid.default_longitude,
                int(masjid.default_calculation_method_id),
                int(masjid_settings.asr_juristic_id),
                int(masjid_settings.high_latitude_method_id),
                masjid.default_city_name or masjid.name,
                "guest_followed_masjid",
                masjid
            )

    # Priority 2: Logged-in user logic
    if user:
        user_settings = user.settings if user and user.settings else UserSettings()

        # Priority 2a: Followed Masjid
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
                "followed_masjid",
                masjid
            )

        # Priority 2b: Custom Location Search (using user's own settings)
        req_lat = args.get('lat')
        req_lon = args.get('lon')
        if req_lat is not None and req_lon is not None:
            high_lat_id_to_use = int(user_settings.high_latitude_method_id or high_lat_id) if req_lat > 48.0 else 0
            return (
                req_lat,
                req_lon,
                int(user.default_calculation_method_id or method_id),
                int(user_settings.asr_juristic_id or asr_id),
                high_lat_id_to_use,
                args.get('city', "Custom Location"),
                "custom_location_with_user_settings",
                None
            )

        # Priority 2c: User's Saved Personal Settings
        if user.default_latitude and user.default_longitude and user.default_calculation_method_id is not None:
            return (
                user.default_latitude,
                user.default_longitude,
                int(user.default_calculation_method_id),
                int(user_settings.asr_juristic_id or asr_id),
                int(user_settings.high_latitude_method_id or high_lat_id),
                user.default_city_name,
                "user_personal_settings",
                None
            )

    # Priority 3: Stateless Guest user (custom location search)
    if not user:
        req_lat = args.get('lat')
        req_lon = args.get('lon')
        if req_lat is not None and req_lon is not None:
            guest_method_id = args.get('method', method_id)
            guest_asr_id = args.get('school', asr_id)
            guest_high_lat_id = args.get('latitudeAdjustmentMethod', high_lat_id)
            return (
                req_lat, req_lon, int(guest_method_id), int(guest_asr_id), int(guest_high_lat_id),
                args.get('city', "Custom Location"),
                "guest_custom_location",
                None
            )

    # Fallback to app default for all other cases
    return lat, lon, method_id, asr_id, high_lat_id, city_name, source, None


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
    and stateful data for guests following a Masjid.
    """
    user = g.user if hasattr(g, 'user') else None
    is_authenticated = True if user else False
    
    # --- Determine the source of truth for prayer settings ---
    user_prayer_settings_obj = user.settings if user and user.settings else UserSettings()
    time_format_pref = user.time_format_preference if user else '12h'

    # This function now also returns the followed masjid object if applicable
    lat, lon, method_id, asr_id, high_lat_id, city_name, settings_source, followed_masjid = get_prayer_settings_from_user(user, args)

    # If settings came from a followed masjid (user or guest), get additional info
    is_following_masjid = settings_source in ["followed_masjid", "guest_followed_masjid"]
    announcements = followed_masjid.announcements if followed_masjid else []

    # --- Fetch and Calculate Prayer Times (Core Logic) ---
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

    # Unpack the new warnings list from the service function
    display_times, needs_db_update, warnings = calculate_display_times_from_service(
        user_prayer_settings_obj, 
        api_times_today, 
        api_times_tomorrow, 
        current_app.config,
        calculation_date=today_date
    )
    
    if needs_db_update and user and not is_following_masjid:
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
    owner_id = None
    if is_following_masjid:
        owner_id = followed_masjid.id
    elif user:
        owner_id = user.id

    if owner_id:
        first_day_of_current_month = today_date.replace(day=1)
        first_day_of_next_month = first_day_of_current_month + datetime.timedelta(days=32)
        next_month_year = first_day_of_next_month.year
        next_month_month = first_day_of_next_month.month

        schedule_exists = db.session.query(MonthlyScheduleCache.id).filter_by(
            owner_id=owner_id,
            year=next_month_year,
            month=next_month_month
        ).first() is not None

        if schedule_exists:
            from flask import url_for
            next_schedule_url = url_for(
                'API.get_monthly_schedule', 
                owner_id=owner_id, 
                year=next_month_year, 
                month=next_month_month, 
                _external=False
            )

    response_data = {
        "currentLocationName": city_name,
        "currentPrayerPeriod": current_period_info,
        "prayerTimes": display_times,
        "dateInfo": {
            "gregorian": f"{gregorian_info.get('date')}, {gregorian_info.get('weekday', {}).get('en')}",
            "hijri": f"{hijri_info.get('date')} ({hijri_info.get('month', {}).get('en')})} {hijri_info.get('year')} AH)"
        },
        "nextDayPrayerDisplay": next_day_prayer_display,
        "userPreferences": {
            "timeFormat": time_format_pref,
            "calculationMethod": method_id,
            "homeLatitude": lat,
            "homeLongitude": lon,
        },
        "isUserAuthenticated": is_authenticated,
        "warnings": warnings, # Add warnings to the response
        # --- New community feature fields ---
        "is_following_default_masjid": is_following_masjid,
        "default_masjid_info": followed_masjid,
        "announcements": announcements,
        # --- New: URL for proactive client-side caching ---
        "next_schedule_url": next_schedule_url
    }
    current_app.logger.info(f"Response data: {response_data}")
    return response_data


@api_bp.route('/guest/follow_masjid', methods=['POST'])
@jwt_optional
def guest_follow_masjid():
    """
    Allows a guest user (identified by a device ID) to follow a masjid.
    This creates or updates the guest's profile with their chosen masjid.
    """
    device_id = g.device_id if hasattr(g, 'device_id') else None
    if not device_id:
        abort(400, message="Device ID is missing. Please include it in the 'X-Device-ID' header.")

    data = request.get_json()
    if not data:
        abort(400, message="Invalid JSON body.")
        
    masjid_id = data.get('masjid_id')
    if not masjid_id:
        abort(400, message="masjid_id is required in the request body.")

    # Validate that the masjid_id corresponds to a real Masjid
    masjid = User.query.filter_by(id=masjid_id, role='Masjid').first()
    if not masjid:
        abort(404, message=f"Masjid with ID {masjid_id} not found.")

    # Find existing guest profile or create a new one
    guest_profile = GuestProfile.query.filter_by(device_id=device_id).first()
    if guest_profile:
        guest_profile.followed_masjid_id = masjid_id
        guest_profile.updated_at = datetime.utcnow()
        current_app.logger.info(f"Updated GuestProfile for device {device_id} to follow Masjid {masjid_id}.")
    else:
        guest_profile = GuestProfile(
            device_id=device_id,
            followed_masjid_id=masjid_id
        )
        db.session.add(guest_profile)
        current_app.logger.info(f"Created new GuestProfile for device {device_id} to follow Masjid {masjid_id}.")

    try:
        db.session.commit()
        return jsonify({"success": True, "message": f"Guest device {device_id} is now following Masjid {masjid_id}."}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating GuestProfile for device {device_id}: {e}", exc_info=True)
        abort(500, message="Could not update guest session.")


@api_bp.route('/v1/schedule/monthly', methods=['GET'])
@jwt_optional
def get_monthly_schedule():
    """
    API endpoint to get the pre-calculated, state-based monthly schedule.
    This works for both authenticated users and stateful guest users.
    """
    owner_id = None
    user = g.user if hasattr(g, 'user') else None
    device_id = g.device_id if hasattr(g, 'device_id') else None

    if user:
        # For a logged-in user, they are the owner.
        # The service will handle if they follow a masjid or use personal settings.
        owner_id = user.id
    elif device_id:
        # For a guest, find their profile and the masjid they follow.
        guest_profile = GuestProfile.query.filter_by(device_id=device_id).first()
        if guest_profile and guest_profile.followed_masjid_id:
            owner_id = guest_profile.followed_masjid_id
        else:
            # A guest trying to access this without following a masjid is an error.
            abort(404, message="Guest profile not found or no masjid is being followed.")
    else:
        # If there is no user and no device_id, access is denied.
        abort(401, message="Authentication credentials or a valid Device ID are required.")

    try:
        now = datetime.datetime.utcnow()
        year = request.args.get('year', default=now.year, type=int)
        month = request.args.get('month', default=now.month, type=int)

        # The service function needs the primary user_id for context,
        # but the actual schedule generation might be based on a different owner (the masjid).
        # We need to refactor get_or_generate_monthly_schedule to accept an owner_id directly.
        # For now, let's pass the user_id if it exists, and handle it in the service.
        # A better approach would be to pass the determined owner_id.
        schedule_data = get_or_generate_monthly_schedule(
            user_id=owner_id, # The service knows how to handle a user_id that is a Masjid.
            year=year,
            month=month
        )

        if not schedule_data:
            return jsonify({"error": "Could not generate or retrieve schedule."}), 500

        return jsonify(schedule_data), 200

    except Exception as e:
        current_app.logger.error(f"Error in /v1/schedule/monthly endpoint: {e}", exc_info=True)
        return jsonify({"error": "An unexpected server error occurred."}), 500