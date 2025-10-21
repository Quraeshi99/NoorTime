# project/services/prayer_time_service.py

import datetime
import math
import json
import requests
import threading
from flask import current_app, Flask
from .. import db
from ..models import PrayerZoneCalendar, GeocodingCache
from .helpers.constants import PRAYER_CONFIG_MAP

from .geocoding_service import get_admin_levels_from_coords

# --- Background Task for Grace Period ---

def _background_fetch_task(app: Flask, zone_id: str, year: int, calculation_method_key: str, latitude: float, longitude: float):
    """
    This function is executed in a background thread. It creates its own app context
    to safely interact with the database and application configuration. Its purpose is
    to fetch and cache the calendar for the given zone and year.
    
    Args:
        app (Flask): The Flask application instance.
        zone_id (str): The zone ID for which to fetch the calendar.
        year (int): The year for which to fetch the calendar.
        calculation_method_key (str): The calculation method to use.
        latitude (float): The latitude for the API call.
        longitude (float): The longitude for the API call.
    """
    with app.app_context():
        current_app.logger.info(f"[BACKGROUND] Starting background fetch for zone '{zone_id}', year {year}.")
        try:
            # We call _get_yearly_calendar_data which contains the full logic to fetch
            # from API and save to the database. force_refresh=True ensures it hits the API.
            _get_yearly_calendar_data(
                zone_id=zone_id,
                year=year,
                calculation_method_key=calculation_method_key,
                latitude=latitude,
                longitude=longitude,
                force_refresh=True
            )
            current_app.logger.info(f"[BACKGROUND] Successfully completed background fetch for zone '{zone_id}', year {year}.")
        except Exception as e:
            # Log any exceptions that occur within the thread
            current_app.logger.error(f"[BACKGROUND] Background fetch failed for zone '{zone_id}', year {year}: {e}", exc_info=True)

def _check_and_trigger_grace_period_fetch(final_zone_id: str, calculation_method_key: str, latitude: float, longitude: float):
    """
    Checks if the application is in the 'grace period' before the new year. If so,
    and if the next year's calendar is not yet cached for the given zone, it spawns
    a background thread to fetch it. This implements the "stale-while-revalidate"
    part of the Two-Layer Defense.
    
    Args:
        final_zone_id (str): The definitive zone ID for the current request.
        calculation_method_key (str): The calculation method for the request.
        latitude (float): The latitude for the API call.
        longitude (float): The longitude for the API call.
    """
    # Check if a zone was determined. No need to proceed if zone is unknown.
    if not final_zone_id:
        return

    now = datetime.datetime.utcnow()
    grace_month = current_app.config.get('CACHE_GRACE_PERIOD_START_MONTH', 12)
    grace_day = current_app.config.get('CACHE_GRACE_PERIOD_START_DAY', 15)

    # Determine if we are currently within the grace period
    is_in_grace_period = (now.month == grace_month and now.day >= grace_day) or (now.month > grace_month)

    if is_in_grace_period:
        next_year = now.year + 1
        
        # Check if the calendar for next year is already in our database cache
        next_year_calendar_exists = PrayerZoneCalendar.query.filter_by(
            zone_id=final_zone_id,
            year=next_year,
            calculation_method=calculation_method_key
        ).first()

        if not next_year_calendar_exists:
            # If it's not cached, we need to fetch it.
            # We spawn a background thread to do this so the user's current request is not blocked.
            current_app.logger.info(f"GRACE PERIOD: Next year's calendar for zone '{final_zone_id}' not found. Triggering background fetch.")
            
            app = current_app._get_current_object()
            thread = threading.Thread(
                target=_background_fetch_task,
                args=(app, final_zone_id, next_year, calculation_method_key, latitude, longitude)
            )
            thread.daemon = True
            thread.start()
        else:
            current_app.logger.debug(f"GRACE PERIOD: Next year's calendar for zone '{final_zone_id}' already exists. No fetch needed.")


from ..tasks import fetch_and_cache_yearly_calendar_task

# --- Private Helper Functions ---

def _get_daily_prayer_times_from_api(date_obj, latitude, longitude, method_id, asr_juristic_id, high_latitude_method_id):
    """
    Fetches prayer times for a single day directly from the API adapter.
    This is used for the 'instant gratification' part of the hybrid cache strategy.
    """
    adapter = get_selected_api_adapter()
    if not adapter:
        return None
    
    try:
        # Call the new daily fetch method on the adapter
        daily_data = adapter.fetch_daily_timings(
            date_obj=date_obj,
            latitude=latitude,
            longitude=longitude,
            method_id=method_id,
            asr_juristic_id=asr_juristic_id,
            high_latitude_method_id=high_latitude_method_id
        )
        return daily_data
    except Exception as e:
        current_app.logger.error(f"Exception during single-day API fetch: {e}", exc_info=True)
        return None

def _get_zone_id_from_coords(latitude, longitude):
    """
    [Fallback] Generates a grid-based zone ID for a given coordinate.
    This is the fallback safety net for remote areas where administrative
    boundaries are not available.
    """
    grid_size = current_app.config.get("PRAYER_ZONE_GRID_SIZE", 0.2)
    zone_lat = math.floor(latitude / grid_size) * grid_size
    zone_lon = math.floor(longitude / grid_size) * grid_size
    return f"grid_{round(zone_lat, 2)}_{round(zone_lon, 2)}"

def _get_zone_id_from_admin_levels(admin_levels, level="admin_2"):
    """
    Constructs a human-readable, hierarchical zone ID from administrative levels.
    The 'level' parameter determines the granularity of the zone ID.
    
    Examples:
    - level="admin_2": IN_UP_BADAUN (for an Admin Level 2 zone)
    - level="admin_3": IN_UP_BADAUN_BISAULI (for an Admin Level 3 sub-zone)
    """
    country_code = admin_levels.get('country_code', 'XX').upper()
    admin_1 = admin_levels.get('admin_1_name', '').upper().replace(' ', '_')
    admin_2 = admin_levels.get('admin_2_name', '').upper().replace(' ', '_')
    admin_3 = admin_levels.get('admin_3_name', '').upper().replace(' ', '_')

    if not (country_code and admin_1 and admin_2):
        return None # Essential parts missing for any level

    base_id = f"{country_code}_{admin_1}_{admin_2}"

    if level == "admin_2":
        return base_id
    elif level == "admin_3" and admin_3:
        return f"{base_id}_{admin_3}"
    else:
        return None # Invalid level or missing admin_3 for admin_3 level


def _compare_prayer_times(calendar1_data, calendar2_data, threshold_seconds=50):
    """
    Compares two yearly prayer time calendars and returns True if the difference
    between any corresponding prayer time (Fajr, Dhuhr, Asr, Maghrib, Isha) 
    exceeds the given threshold for any day of the year.
    
    Args:
        calendar1_data (list): List of daily prayer data for calendar 1.
        calendar2_data (list): List of daily prayer data for calendar 2.
        threshold_seconds (int): The maximum allowed difference in seconds.
        
    Returns:
        bool: True if difference exceeds threshold, False otherwise.
    """
    if not calendar1_data or not calendar2_data:
        return True # Treat as different if data is missing

    # Assuming both calendars have the same number of days and are aligned
    for day_idx in range(min(len(calendar1_data), len(calendar2_data))):
        day1_timings = calendar1_data[day_idx].get('timings', {})
        day2_timings = calendar2_data[day_idx].get('timings', {})

        for prayer_name in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
            time1_str = day1_timings.get(prayer_name)
            time2_str = day2_timings.get(prayer_name)

            if time1_str and time2_str:
                try:
                    time1_obj = datetime.datetime.strptime(time1_str.split(' ')[0], "%H:%M").time()
                    time2_obj = datetime.datetime.strptime(time2_str.split(' ')[0], "%H:%M").time()
                    
                    # Create dummy datetime objects for comparison across midnight
                    dummy_date = datetime.date(2000, 1, 1) # Arbitrary date
                    dt1 = datetime.datetime.combine(dummy_date, time1_obj)
                    dt2 = datetime.datetime.combine(dummy_date, time2_obj)

                    # Calculate absolute difference in seconds
                    diff_seconds = abs((dt1 - dt2).total_seconds())

                    if diff_seconds > threshold_seconds:
                        current_app.logger.info(f"Time difference for {prayer_name} on day {day_idx} exceeds {threshold_seconds}s: {diff_seconds}s")
                        return True # Difference found
                except ValueError:
                    current_app.logger.warning(f"Could not parse time string for comparison: {time1_str} or {time2_str}")
                    continue
    return False # No significant difference found

def _get_zone_center_coords(zone_id):
    """
    [Legacy] Calculates the center coordinates for a grid-based zone ID.
    This is only used for the fallback grid system.
    """
    if not zone_id.startswith('grid_'):
        # This function is not applicable for admin-based zones, 
        # as we use the coordinates of the location directly.
        return None, None

    grid_size = current_app.config.get("PRAYER_ZONE_GRID_SIZE", 0.2)
    parts = zone_id.split('_')
    base_lat = float(parts[1])
    base_lon = float(parts[2])
    center_lat = base_lat + (grid_size / 2)
    center_lon = base_lon + (grid_size / 2)
    return center_lat, center_lon

def get_selected_api_adapter():
    """
    Instantiates and returns the API adapter based on configuration.
    """
    adapter_name = current_app.config.get('PRAYER_API_ADAPTER', "AlAdhanAdapter")
    base_url = current_app.config.get('PRAYER_API_BASE_URL')
    api_key = current_app.config.get('PRAYER_API_KEY')

    if adapter_name == "AlAdhanAdapter":
        if not base_url:
            current_app.logger.error("AlAdhan API base URL is not configured.")
            return None
        from .api_adapters.aladhan_adapter import AlAdhanAdapter
        return AlAdhanAdapter(base_url=base_url, api_key=api_key)
    else:
        current_app.logger.error(f"Unsupported Prayer API Adapter: {adapter_name}")
        return None

def _get_method_id_for_country(country_code):
    """
    Determines the most common prayer time calculation method for a given country.
    It reads a mapping from a JSON file, making it easy to update and manage.
    This is the core of the "Automatic" setting.

    Args:
        country_code (str): The two-letter ISO 3166-1 alpha-2 country code.

    Returns:
        int: The ID of the recommended calculation method.
    """
    # Path to the mapping file. Using a relative path is not ideal in a real app,
    # but for this context, we construct an absolute path.
    # In a real Flask app, this would use instance_path or a configured path.
    map_file_path = "/home/ubuntu/NoorTime/backend/project/static/country_method_map.json"
    
    try:
        with open(map_file_path, 'r') as f:
            mapping_data = json.load(f)
        
        country_map = mapping_data.get("country_map", {})
        default_id = mapping_data.get("default_method_id", 3) # Default to MWL if not specified

        # Look up the country code (case-insensitive)
        method_id = country_map.get(country_code.upper(), default_id)
        current_app.logger.info(f"Automatic method selection for country '{country_code}': Chose method ID {method_id}.")
        return method_id

    except (FileNotFoundError, json.JSONDecodeError) as e:
        current_app.logger.error(f"Could not load or parse country_method_map.json: {e}")
        # Fallback to a hardcoded, safe default (MWL)
        return 3

import json
from ..extensions import redis_client

# --- Main Service Function ---

def get_api_prayer_times_for_date_from_service(date_obj, latitude, longitude, method_id, asr_juristic_id, high_latitude_method_id, force_refresh=False):
    """
    The core service function, now refactored for a Redis-backed hybrid caching strategy.
    It provides an instant response even for new, uncached locations.
    """
    year = date_obj.year
    today_date_str = date_obj.strftime("%d-%m-%Y")

    # 1. Determine Zone ID
    admin_levels = get_admin_levels_from_coords(latitude, longitude)
    
    AUTOMATIC_METHOD_ID = 99
    if method_id == AUTOMATIC_METHOD_ID:
        country_code = admin_levels.get('country_code', 'XX') if admin_levels else 'XX'
        method_id = _get_method_id_for_country(country_code)

    composite_method_key = f"{method_id}-{asr_juristic_id}-{high_latitude_method_id}"

    final_zone_id = _determine_final_zone_id(year, latitude, longitude, admin_levels, composite_method_key, force_refresh)

    if not final_zone_id:
        current_app.logger.error(f"Could not determine a final zone ID for ({latitude}, {longitude}).")
        return None

    # 2. Attempt to get the full yearly calendar from cache (Redis or DB)
    yearly_calendar = _get_yearly_calendar_from_cache(final_zone_id, year, composite_method_key)

    if yearly_calendar:
        for day_data in yearly_calendar:
            if day_data.get('date', {}).get('gregorian', {}).get('date') == today_date_str:
                return day_data
        current_app.logger.error(f"Data for {today_date_str} not found in cached calendar for zone {final_zone_id}")
        return None

    # 3. Cache MISS: Hybrid approach
    else:
        current_app.logger.info(f"COMPLETE CACHE MISS for zone '{final_zone_id}'. Using Hybrid Approach.")
        
        fetch_and_cache_yearly_calendar_task.delay(
            zone_id=final_zone_id,
            year=year,
            method_id=method_id,
            asr_juristic_id=asr_juristic_id,
            high_latitude_method_id=high_latitude_method_id,
            latitude=latitude,
            longitude=longitude
        )
        current_app.logger.info(f"Triggered background task for zone '{final_zone_id}'.")

        daily_data = _get_daily_prayer_times_from_api(
            date_obj=date_obj,
            latitude=latitude,
            longitude=longitude,
            method_id=method_id,
            asr_juristic_id=asr_juristic_id,
            high_latitude_method_id=high_latitude_method_id
        )
        
        # Cache the single-day result for a short time to prevent API hammering
        if daily_data:
            redis_key = f"daily:{final_zone_id}:{today_date_str}:{composite_method_key}"
            redis_client.set(redis_key, json.dumps(daily_data), ex=3600) # Cache for 1 hour

        return daily_data

def _determine_final_zone_id(year, latitude, longitude, admin_levels, composite_method_key, force_refresh):
    """Determines the most appropriate zone ID to use (Admin2, Admin3, or grid)."""
    if not admin_levels:
        current_app.logger.warning(f"No admin levels for ({latitude}, {longitude}). Using fallback grid.")
        return _get_zone_id_from_coords(latitude, longitude)

    admin_2_zone_id = _get_zone_id_from_admin_levels(admin_levels, level="admin_2")
    admin_3_zone_id = _get_zone_id_from_admin_levels(admin_levels, level="admin_3")

    if not admin_3_zone_id:
        return admin_2_zone_id

    admin_2_calendar = _get_yearly_calendar_from_cache(admin_2_zone_id, year, composite_method_key)
    if not admin_2_calendar:
        return admin_3_zone_id

    admin_3_calendar = _get_yearly_calendar_from_cache(admin_3_zone_id, year, composite_method_key)
    if not admin_3_calendar:
        return admin_3_zone_id

    if not _compare_prayer_times(admin_2_calendar, admin_3_calendar, threshold_seconds=50):
        current_app.logger.info(f"Admin Level 2 ('{admin_2_zone_id}') is sufficient.")
        return admin_2_zone_id
    else:
        current_app.logger.info(f"Admin Level 3 ('{admin_3_zone_id}') is required.")
        return admin_3_zone_id

def _get_yearly_calendar_from_cache(zone_id, year, composite_method_key):
    """
    New caching function that checks Redis first, then the database.
    If found in DB, it caches to Redis for future requests.
    """
    redis_key = f"calendar:{zone_id}:{year}:{composite_method_key}"

    # 1. Check Redis Cache first
    try:
        cached_data = redis_client.get(redis_key)
        if cached_data:
            current_app.logger.info(f"Redis Cache HIT for zone '{zone_id}', year {year}.")
            return json.loads(cached_data)
    except Exception as e:
        current_app.logger.error(f"Redis GET failed: {e}", exc_info=True)

    current_app.logger.info(f"Redis Cache MISS for zone '{zone_id}', year {year}.")

    # 2. Check Database Cache
    db_calendar = PrayerZoneCalendar.query.filter_by(
        zone_id=zone_id, 
        year=year, 
        calculation_method=composite_method_key
    ).first()

    if db_calendar:
        current_app.logger.info(f"DB Cache HIT for zone '{zone_id}', year {year}.")
        calendar_data = db_calendar.calendar_data
        
        # 3. Populate Redis Cache from DB data
        try:
            redis_client.set(redis_key, json.dumps(calendar_data), ex=2592000) # Cache for 30 days
            current_app.logger.info(f"Populated Redis cache for zone '{zone_id}', year {year}.")
        except Exception as e:
            current_app.logger.error(f"Redis SET failed: {e}", exc_info=True)
            
        return calendar_data
    
    current_app.logger.info(f"DB Cache MISS for zone '{zone_id}', year {year}.")
    return None




# --- Calculation and Formatting Helpers ---

def _parse_time_str(time_str):
    if not time_str or time_str.lower() == "n/a": return None
    try:
        return datetime.datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        current_app.logger.warning(f"Service: Invalid time string format for parsing: {time_str}")
        return None
def _format_time_obj(time_obj):
    if not time_obj: return "N/A"
    return time_obj.strftime("%H:%M")

def _add_minutes(time_obj, minutes_to_add):
    if not time_obj or minutes_to_add is None: return None
    dummy_date = datetime.date.min
    full_datetime = datetime.datetime.combine(dummy_date, time_obj)
    new_datetime = full_datetime + datetime.timedelta(minutes=int(minutes_to_add))
    return new_datetime.time()

def _add_seconds(time_obj, seconds_to_add):
    if not time_obj or seconds_to_add is None: return None
    dummy_date = datetime.date.min
    full_datetime = datetime.datetime.combine(dummy_date, time_obj)
    new_datetime = full_datetime + datetime.timedelta(seconds=int(seconds_to_add))
    return new_datetime.time()

def _apply_boundary_check(time_to_check, start_boundary, end_boundary):
    if not time_to_check: return None
    start_boundary_obj = _parse_time_str(start_boundary)
    end_boundary_obj = _parse_time_str(end_boundary)
    if not start_boundary_obj or not end_boundary_obj: return time_to_check
    if start_boundary_obj > end_boundary_obj: return time_to_check
    if time_to_check < start_boundary_obj: return start_boundary_obj
    if time_to_check > end_boundary_obj: return end_boundary_obj
    return time_to_check

def _get_single_prayer_info(prayer_name, api_times, user_settings, api_times_day_after_tomorrow, last_api_times):
    config = PRAYER_CONFIG_MAP.get(prayer_name.lower())
    if not config: return {"azan": "N/A", "jamaat": "N/A"}

    is_fixed = getattr(user_settings, config["is_fixed_attr"], False)
    api_start_time_str = api_times.get(config["api_key"])
    start_boundary_str = api_start_time_str
    end_boundary_key = config["end_boundary_key"]
    end_boundary_str = api_times_day_after_tomorrow.get("Fajr") if end_boundary_key == "Fajr_Tomorrow" else api_times.get(end_boundary_key)

    azan_time_obj, jamaat_time_obj = None, None
    if is_fixed:
        azan_time_obj = _parse_time_str(getattr(user_settings, config["fixed_azan_attr"]))
        jamaat_time_obj = _parse_time_str(getattr(user_settings, config["fixed_jamaat_attr"]))
    else:
        api_time_to_use_str = api_start_time_str
        if last_api_times and user_settings.threshold_minutes > 0:
            last_time_obj = _parse_time_str(last_api_times.get(config["api_key"]))
            new_time_obj = _parse_time_str(api_start_time_str)
            if last_time_obj and new_time_obj:
                diff = abs((datetime.datetime.combine(datetime.date.today(), new_time_obj) - datetime.datetime.combine(datetime.date.today(), last_time_obj)).total_seconds() / 60)
                if diff < user_settings.threshold_minutes:
                    api_time_to_use_str = last_api_times.get(config["api_key"])

        api_start_time_obj = _parse_time_str(api_time_to_use_str)
        if api_start_time_obj:
            azan_offset = getattr(user_settings, config["azan_offset_attr"])
            calculated_azan_obj = _add_minutes(api_start_time_obj, azan_offset)
            azan_time_obj = _apply_boundary_check(calculated_azan_obj, start_boundary_str, end_boundary_str)
            if azan_time_obj:
                jamaat_offset = getattr(user_settings, config["jamaat_offset_attr"])
                calculated_jamaat_obj = _add_minutes(azan_time_obj, jamaat_offset)
                jamaat_time_obj = _apply_boundary_check(calculated_jamaat_obj, start_boundary_str, end_boundary_str)

    return {"azan": _format_time_obj(azan_time_obj), "jamaat": _format_time_obj(jamaat_time_obj)}

def calculate_display_times_from_service(user_settings, api_times_today, api_times_tomorrow, app_config):
    """
    Calculates final Azan & Jama'at times based on raw API data and user preferences.
    This function is the core of the personalization logic.
    
    Args:
        user_settings (UserSettings): The user's personal settings object.
        api_times_today (dict): Raw prayer times for the current day from the API/cache.
        api_times_tomorrow (dict): Raw prayer times for the next day for boundary checks.
        app_config (dict): The Flask app's configuration.

    Returns:
        tuple: A tuple containing (calculated_times, needs_db_update).
               - calculated_times (dict): The final, display-ready prayer times.
               - needs_db_update (bool): A flag indicating if user settings need to be persisted.
    """
    calculated_times = {}
    needs_db_update = False

    # If raw API times are not available, use empty dicts to prevent errors.
    # The function will still attempt to calculate fixed times.
    if not api_times_today:
        api_times_today = {}
    if not api_times_tomorrow:
        api_times_tomorrow = {}

    # --- Last API Times for Thresholding Logic (Restored) ---
    # This logic prevents small, insignificant changes in raw API times from causing
    # frequent updates on the user's screen, ensuring a more stable display.
    last_api_times = {}
    if user_settings.last_api_times_for_threshold:
        try:
            last_api_times = json.loads(user_settings.last_api_times_for_threshold)
        except (json.JSONDecodeError, TypeError):
            current_app.logger.warning("Could not parse last_api_times_for_threshold JSON. Resetting.")
            needs_db_update = True # Force update if parsing fails

    # --- 1. Main Prayer Calculation Loop (Fajr, Dhuhr, Asr, Maghrib, Isha) ---
    # This loop iterates through the 5 main prayers using a configuration map
    # that defines the keys and attributes for each prayer.
    for p_key, config in PRAYER_CONFIG_MAP.items():
        # For each prayer, check if the user has set it to a fixed time.
        is_fixed = getattr(user_settings, config["is_fixed_attr"], False)
        
        azan_time_obj, jamaat_time_obj = None, None

        # --- Logic for Fixed Times ---
        if is_fixed:
            # If the time is fixed, we directly parse the user-defined string time.
            # This works even if the API data is unavailable.
            azan_time_obj = _parse_time_str(getattr(user_settings, config["fixed_azan_attr"]))
            jamaat_time_obj = _parse_time_str(getattr(user_settings, config["fixed_jamaat_attr"]))
        
        # --- Logic for Offset-based Times ---
        else:
            # If not fixed, we calculate the time based on the raw API time plus a user-defined offset.
            api_start_time_str = api_times_today.get(config["api_key"])
            
            if api_start_time_str:
                # Determine the end boundary for the prayer (usually the start of the next prayer).
                start_boundary_str = api_start_time_str
                end_boundary_key = config["end_boundary_key"]
                end_boundary_str = api_times_tomorrow.get("Fajr") if end_boundary_key == "Fajr_Tomorrow" else api_times_today.get(end_boundary_key)

                # Apply thresholding logic to prevent small, frequent changes.
                api_time_to_use_str = api_start_time_str
                last_api_time_str = last_api_times.get(config["api_key"])
                
                if last_api_time_str and user_settings.threshold_minutes > 0:
                    last_time_obj = _parse_time_str(last_api_time_str)
                    new_time_obj = _parse_time_str(api_start_time_str)
                    if last_time_obj and new_time_obj:
                        # Calculate difference in minutes
                        diff = abs((datetime.datetime.combine(datetime.date.today(), new_time_obj) - datetime.datetime.combine(datetime.date.today(), last_time_obj)).total_seconds() / 60)
                        if diff < user_settings.threshold_minutes:
                            # If difference is below threshold, use the last known stable time.
                            api_time_to_use_str = last_api_time_str
                        else:
                            # If difference exceeds threshold, update to the new time and flag for DB update.
                            needs_db_update = True
                    else:
                        # If parsing fails, assume update is needed.
                        needs_db_update = True
                else:
                    # If no last time is stored or threshold is 0, always update.
                    needs_db_update = True

                api_start_time_obj = _parse_time_str(api_time_to_use_str)
                if api_start_time_obj:
                    # Calculate Azan time by adding the user's offset to the raw API time.
                    azan_offset = getattr(user_settings, config["azan_offset_attr"])
                    calculated_azan_obj = _add_minutes(api_start_time_obj, azan_offset)
                    # Ensure the calculated time does not cross into the next prayer's time.
                    azan_time_obj = _apply_boundary_check(calculated_azan_obj, start_boundary_str, end_boundary_str)
                    
                    if azan_time_obj:
                        # Calculate Jamaat time by adding the user's offset to the calculated Azan time.
                        jamaat_offset = getattr(user_settings, config["jamaat_offset_attr"])
                        calculated_jamaat_obj = _add_minutes(azan_time_obj, jamaat_offset)
                        jamaat_time_obj = _apply_boundary_check(calculated_jamaat_obj, start_boundary_str, end_boundary_str)

        # Store the final, formatted times for the current prayer.
        calculated_times[p_key] = {"azan": _format_time_obj(azan_time_obj), "jamaat": _format_time_obj(jamaat_time_obj)}
    
    # --- 2. Special Time Calculations (Iftari, Sehri, Jummah, Chasht) ---

    # Iftari time is always the same as the raw Maghrib start time.
    maghrib_time_str = api_times_today.get("Maghrib")
    calculated_times["iftari"] = {"time": _format_time_obj(_parse_time_str(maghrib_time_str))}

    # Sehri End time is always the same as the raw Imsak time.
    imsak_time_str = api_times_today.get("Imsak")
    calculated_times["sehri_end"] = {"time": _format_time_obj(_parse_time_str(imsak_time_str))}

    # --- New, Flexible Jummah Calculation ---
    # This block calculates Jummah time, respecting the user's choice for it to be fixed or offset-based.
    if user_settings.jummah_is_fixed:
        # If Jummah is fixed, use the user-defined times directly.
        jummah_azan_obj = _parse_time_str(user_settings.jummah_azan_time)
        jummah_khutbah_obj = _parse_time_str(user_settings.jummah_khutbah_start_time)
        jummah_jamaat_obj = _parse_time_str(user_settings.jummah_jamaat_time)
    else:
        # If not fixed, calculate based on Dhuhr's raw time.
        dhuhr_raw_time_str = api_times_today.get("Dhuhr")
        dhuhr_raw_time_obj = _parse_time_str(dhuhr_raw_time_str)
        
        jummah_azan_obj, jummah_khutbah_obj, jummah_jamaat_obj = None, None, None

        if dhuhr_raw_time_obj:
            # Calculate Jummah Azan based on Dhuhr raw time + offset.
            jummah_azan_obj = _add_minutes(dhuhr_raw_time_obj, user_settings.jummah_azan_offset)
            
            if jummah_azan_obj:
                # Khutbah and Jamaat are calculated relative to the calculated Azan time.
                jummah_khutbah_obj = _add_minutes(jummah_azan_obj, user_settings.jummah_khutbah_offset)
                jummah_jamaat_obj = _add_minutes(jummah_azan_obj, user_settings.jummah_jamaat_offset)

    calculated_times["jummah"] = {
        "azan": _format_time_obj(jummah_azan_obj),
        "khutbah": _format_time_obj(jummah_khutbah_obj),
        "jamaat": _format_time_obj(jummah_jamaat_obj)
    }

    # Chasht (Duha) prayer time is calculated as 20 minutes and 30 seconds after Sunrise.
    sunrise_time_str = api_times_today.get("Sunrise")
    if sunrise_time_str:
        sunrise_time_obj = _parse_time_str(sunrise_time_str)
        if sunrise_time_obj:
            chasht_time_obj = _add_minutes(sunrise_time_obj, 20)
            chasht_time_obj = _add_seconds(chasht_time_obj, 30)
            calculated_times["chasht"] = {"azan": _format_time_obj(chasht_time_obj), "jamaat": "N/A"}
        else:
            calculated_times["chasht"] = {"azan": "N/A", "jamaat": "N/A"}
    else:
        calculated_times["chasht"] = {"azan": "N/A", "jamaat": "N/A"}

    # --- Zohwa-e-Kubra Calculation ---
    fajr_time_str = api_times_today.get("Fajr")
    sunrise_time_str = api_times_today.get("Sunrise")
    sunset_time_str = api_times_today.get("Sunset")

    zohwa_kubra_start_obj = None
    fajr_obj = _parse_time_str(fajr_time_str)
    sunset_obj = _parse_time_str(sunset_time_str)
    if fajr_obj and sunset_obj:
        dummy_date = datetime.date.today()
        fajr_dt = datetime.datetime.combine(dummy_date, fajr_obj)
        sunset_dt = datetime.datetime.combine(dummy_date, sunset_obj)
        if sunset_dt < fajr_dt:
            sunset_dt += datetime.timedelta(days=1)
        duration = sunset_dt - fajr_dt
        midpoint_dt = fajr_dt + duration / 2
        zohwa_kubra_start_obj = midpoint_dt.time()

    zohwa_kubra_end_obj = None
    sunrise_obj = _parse_time_str(sunrise_time_str)
    if sunrise_obj and sunset_obj:
        dummy_date = datetime.date.today()
        sunrise_dt = datetime.datetime.combine(dummy_date, sunrise_obj)
        sunset_dt = datetime.datetime.combine(dummy_date, sunset_obj)
        if sunset_dt < sunrise_dt:
            sunset_dt += datetime.timedelta(days=1)
        duration = sunset_dt - sunrise_dt
        midpoint_dt = sunrise_dt + duration / 2
        zohwa_kubra_end_obj = midpoint_dt.time()

    calculated_times["zohwa_kubra"] = {
        "start": _format_time_obj(zohwa_kubra_start_obj),
        "end": _format_time_obj(zohwa_kubra_end_obj)
    }

    # The needs_db_update flag is used to signal if the last_api_times_for_threshold
    # in user settings needs to be updated in the database.
    return calculated_times, needs_db_update

def get_next_prayer_info_from_service(display_times_today, tomorrow_fajr_display_details, now_datetime_obj):
    # This function's logic remains correct and does not need changes.
    now_time_obj = now_datetime_obj.time()
    is_friday = now_datetime_obj.weekday() == 4
    prayer_sequence_keys = ["fajr", "dhuhr", "asr", "maghrib", "isha"]
    today_prayer_events = []
    for p_key in prayer_sequence_keys:
        prayer_name_display = p_key.capitalize()
        if is_friday and p_key == "dhuhr":
            prayer_name_display = "Jummah"
            jamaat_time_str = display_times_today.get("jummah", {}).get("jamaat")
            azan_time_str = display_times_today.get("jummah", {}).get("azan")
        else:
            jamaat_time_str = display_times_today.get(p_key, {}).get("jamaat")
            azan_time_str = display_times_today.get(p_key, {}).get("azan")
        jamaat_time_obj = _parse_time_str(jamaat_time_str)
        if jamaat_time_obj:
            today_prayer_events.append({
                "key": p_key,
                "name_display": prayer_name_display,
                "datetime": datetime.datetime.combine(now_datetime_obj.date(), jamaat_time_obj),
                "azan": azan_time_str,
                "jamaat": jamaat_time_str
            })
    today_prayer_events.sort(key=lambda x: x["datetime"])
    next_prayer_event = None
    for event in today_prayer_events:
        if now_datetime_obj < event["datetime"]:
            next_prayer_event = event
            break
    details = { "name": "N/A", "azanTime": "N/A", "jamaatTime": "N/A", "timeToJamaatMinutes": 0, "isNextDayFajr": False, "isJamaatCountdownActive": False, "jamaatCountdownSeconds": 0, "isPostJamaatCountdownActive": False, "postJamaatCountdownSeconds": 0, }
    if next_prayer_event:
        details["name"] = next_prayer_event["name_display"]
        details["azanTime"] = next_prayer_event["azan"]
        details["jamaatTime"] = next_prayer_event["jamaat"]
        time_diff = next_prayer_event["datetime"] - now_datetime_obj
        details["timeToJamaatMinutes"] = int(time_diff.total_seconds() // 60)
        if 0 < time_diff.total_seconds() <= 120:
            details["isJamaatCountdownActive"] = True
            details["jamaatCountdownSeconds"] = int(time_diff.total_seconds())
    else:
        details["name"] = "Fajr (Tomorrow)"
        details["isNextDayFajr"] = True
        if tomorrow_fajr_display_details:
            details["azanTime"] = tomorrow_fajr_display_details["azan"]
            details["jamaatTime"] = tomorrow_fajr_display_details["jamaat"]
            fajr_tmrw_time_obj = _parse_time_str(tomorrow_fajr_display_details["jamaat"])
            if fajr_tmrw_time_obj:
                tmrw_date = now_datetime_obj.date() + datetime.timedelta(days=1)
                fajr_tmrw_dt = datetime.datetime.combine(tmrw_date, fajr_tmrw_time_obj)
                time_diff_fajr = fajr_tmrw_dt - now_datetime_obj
                if time_diff_fajr.total_seconds() > 0:
                    details["timeToJamaatMinutes"] = int(time_diff_fajr.total_seconds() // 60)
                    if 0 < time_diff_fajr.total_seconds() <= 120:
                        details["isJamaatCountdownActive"] = True
                        details["jamaatCountdownSeconds"] = int(time_diff_fajr.total_seconds())
    last_jamaat_passed = None
    for event in reversed(today_prayer_events):
        if now_datetime_obj >= event["datetime"]:
            last_jamaat_passed = event
            break
    if last_jamaat_passed:
        time_since_last = now_datetime_obj - last_jamaat_passed["datetime"]
        if 0 <= time_since_last.total_seconds() < 600:
            if not details["isJamaatCountdownActive"]:
                details["isPostJamaatCountdownActive"] = True
                details["postJamaatCountdownSeconds"] = 600 - int(time_since_last.total_seconds())
    return details

def get_current_prayer_period_from_service(api_times_today, api_times_tomorrow, now_datetime_obj):
    if not api_times_today: return {"name": "N/A", "start": "N/A", "end": "N/A"}
    now_time = now_datetime_obj.time()
    periods_config = [
        ("Fajr", "Fajr", "Sunrise"), ("Post-Sunrise", "Sunrise", "Dhuhr"),
        ("Dhuhr", "Dhuhr", "Asr"), ("Asr", "Asr", "Maghrib"),
        ("Maghrib", "Maghrib", "Isha"), ("Isha", "Isha", "Fajr_Tomorrow")
    ]
    for p_name, start_key, end_key in periods_config:
        start_time_str = api_times_today.get(start_key)
        end_time_str = api_times_tomorrow.get("Fajr") if end_key == "Fajr_Tomorrow" and api_times_tomorrow else api_times_today.get(end_key)
        start_time_obj = _parse_time_str(start_time_str)
        end_time_obj = _parse_time_str(end_time_str)
        if start_time_obj and end_time_obj:
            if start_time_obj > end_time_obj:
                if (now_time >= start_time_obj) or (now_time < end_time_obj):
                    return {"name": p_name.upper(), "start": start_time_str, "end": end_time_str}
            elif start_time_obj <= now_time < end_time_obj:
                return {"name": p_name.upper(), "start": start_time_str, "end": end_time_str}
    return {"name": "N/A", "start": "N/A", "end": "N/A"}


