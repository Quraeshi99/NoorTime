# project/services/prayer_time_service.py

import datetime
import requests
import json # For logging
from flask import current_app # To access app.config and app.logger

# API Adapter imports (will be created in next step)
from .api_adapters.aladhan_adapter import AlAdhanAdapter
# from .api_adapters.another_api_adapter import AnotherAPIAdapter # Example for future

# In-memory cache for API responses (prayer times and geocoding)
_api_cache = {}
_GEOCODE_CACHE_EXPIRY_SECONDS = 24 * 60 * 60  # Cache geocode results for 1 day
_PRAYER_TIMES_CACHE_EXPIRY_SECONDS = 1 * 60 * 60  # Cache prayer times for 1 hour


# --- Helper functions (internal to this service) ---
def _parse_time_str(time_str):
    if not time_str or time_str.lower() == "n/a":
        return None
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

def _apply_5_min_step_logic(prayer_key, calculated_time_obj, api_start_time_obj_for_ref):
    """
    Applies 5-minute step rounding for Dhuhr, Asr, Isha.
    Rounds down to the nearest 5 minutes.
    A more sophisticated implementation might consider the last *displayed* time
    and only update if a 5-minute threshold from that is crossed.
    This version simply rounds the newly calculated time.
    """
    if not calculated_time_obj: return None
    
    # For now, a simple round down to nearest 5 minutes.
    # This ensures consistency but might not perfectly reflect the "don't change until 5 mins" idea
    # if API itself changes by 1 min and that 1 min crosses a 5-min boundary.
    # True "step" logic would require storing the last *displayed* time or last *API value that caused a change*.
    new_minute = (calculated_time_obj.minute // 5) * 5
    stepped_time_obj = calculated_time_obj.replace(minute=new_minute, second=0, microsecond=0)
    # current_app.logger.debug(f"5-min step for {prayer_key}: Original {format_time_obj(calculated_time_obj)}, Stepped {format_time_obj(stepped_time_obj)}")
    return stepped_time_obj

# --- Main Service Functions ---

def get_selected_api_adapter():
    """
    Instantiates and returns the API adapter based on configuration.
    """
    adapter_name = current_app.config.get('PRAYER_API_ADAPTER', "AlAdhanAdapter")
    base_url = current_app.config.get('PRAYER_API_BASE_URL')
    api_key = current_app.config.get('PRAYER_API_KEY') # May be None

    if adapter_name == "AlAdhanAdapter":
        if not base_url:
            current_app.logger.error("AlAdhan API base URL is not configured.")
            return None
        return AlAdhanAdapter(base_url=base_url, api_key=api_key)
    # elif adapter_name == "AnotherAPIAdapter":
    #     # return AnotherAPIAdapter(base_url_for_another, key_for_another)
    #     pass
    else:
        current_app.logger.error(f"Unsupported Prayer API Adapter: {adapter_name}")
        return None


def get_api_prayer_times_for_date_from_service(date_obj, latitude, longitude, calculation_method_key, force_refresh=False):
    """
    Service function to fetch prayer times. Uses caching and the selected API adapter.
    calculation_method_key is like 'Karachi', 'ISNA', etc.
    The adapter will handle mapping this key to API-specific method IDs/params.
    """
    current_app.logger.debug(f"Service: Requesting API prayer times for {date_obj}, Lat:{latitude}, Lon:{longitude}, MethodKey:{calculation_method_key}")
    
    # Normalize lat/lon to a certain precision for cache key to avoid minor floating point differences
    lat_str = f"{float(latitude):.4f}"
    lon_str = f"{float(longitude):.4f}"
    date_str_cache = date_obj.strftime("%Y-%m-%d") # Consistent date format for cache key

    cache_key = f"prayer_{date_str_cache}_{lat_str}_{lon_str}_{calculation_method_key}"
    current_timestamp = datetime.datetime.now().timestamp()

    if not force_refresh and cache_key in _api_cache:
        cached_data, fetch_time = _api_cache[cache_key]
        if current_timestamp - fetch_time < _PRAYER_TIMES_CACHE_EXPIRY_SECONDS:
            current_app.logger.info(f"Service: Using cached API prayer times for {cache_key}")
            return cached_data
        else:
            current_app.logger.info(f"Service: API prayer times cache expired for {cache_key}.")
            del _api_cache[cache_key] # Remove expired entry

    adapter = get_selected_api_adapter()
    if not adapter:
        return None # Error already logged

    try:
        api_data = adapter.fetch_prayer_times(date_obj, latitude, longitude, calculation_method_key)
        if api_data:
            _api_cache[cache_key] = (api_data, current_timestamp)
            current_app.logger.info(f"Service: Successfully fetched and cached API prayer times for {cache_key}")
            return api_data
        else:
            # Adapter should log its own errors
            current_app.logger.warning(f"Service: API adapter returned no data for {cache_key}")
            return None
    except Exception as e:
        current_app.logger.error(f"Service: Exception while fetching prayer times via adapter for {cache_key}: {e}", exc_info=True)
        return None


def calculate_display_times_from_service(user_settings, api_times_today, app_config):
    """
    Service function to calculate final Azan & Jama'at times based on user settings and API data.
    """
    if not api_times_today:
        current_app.logger.warning("Service: API times for today are N/A in calculate_display_times.")
        return {p: {"azan": "N/A", "jamaat": "N/A"} for p in ["fajr", "dhuhr", "asr", "maghrib", "isha", "jummah"]}

    calculated_times = {}
    
    prayer_details_map = { # Maps internal key to UserSettings attributes and API keys
        "fajr":    {"is_fixed_attr": "fajr_is_fixed", "fixed_azan_attr": "fajr_fixed_azan", "fixed_jamaat_attr": "fajr_fixed_jamaat", "azan_offset_attr": "fajr_azan_offset", "jamaat_offset_attr": "fajr_jamaat_offset", "api_key": "Fajr", "use_5min_step": False},
        "dhuhr":   {"is_fixed_attr": "dhuhr_is_fixed", "fixed_azan_attr": "dhuhr_fixed_azan", "fixed_jamaat_attr": "dhuhr_fixed_jamaat", "azan_offset_attr": "dhuhr_azan_offset", "jamaat_offset_attr": "dhuhr_jamaat_offset", "api_key": "Dhuhr", "use_5min_step": True},
        "asr":     {"is_fixed_attr": "asr_is_fixed", "fixed_azan_attr": "asr_fixed_azan", "fixed_jamaat_attr": "asr_fixed_jamaat", "azan_offset_attr": "asr_azan_offset", "jamaat_offset_attr": "asr_jamaat_offset", "api_key": "Asr", "use_5min_step": True},
        "maghrib": {"is_fixed_attr": "maghrib_is_fixed", "fixed_azan_attr": "maghrib_fixed_azan", "fixed_jamaat_attr": "maghrib_fixed_jamaat", "azan_offset_attr": "maghrib_azan_offset", "jamaat_offset_attr": "maghrib_jamaat_offset", "api_key": "Maghrib", "use_5min_step": False},
        "isha":    {"is_fixed_attr": "isha_is_fixed", "fixed_azan_attr": "isha_fixed_azan", "fixed_jamaat_attr": "isha_fixed_jamaat", "azan_offset_attr": "isha_azan_offset", "jamaat_offset_attr": "isha_jamaat_offset", "api_key": "Isha", "use_5min_step": True},
    }

    for p_key, config in prayer_details_map.items():
        is_fixed = getattr(user_settings, config["is_fixed_attr"])
        api_start_time_str = api_times_today.get(config["api_key"])
        
        azan_time_obj = None
        jamaat_time_obj = None

        if is_fixed:
            azan_time_obj = _parse_time_str(getattr(user_settings, config["fixed_azan_attr"]))
            jamaat_time_obj = _parse_time_str(getattr(user_settings, config["fixed_jamaat_attr"]))
        else:
            api_start_time_obj = _parse_time_str(api_start_time_str)
            if api_start_time_obj:
                azan_offset = getattr(user_settings, config["azan_offset_attr"])
                calculated_azan_obj = _add_minutes(api_start_time_obj, azan_offset)
                
                if config["use_5min_step"]:
                    azan_time_obj = _apply_5_min_step_logic(p_key, calculated_azan_obj, api_start_time_obj)
                else:
                    azan_time_obj = calculated_azan_obj
                
                if azan_time_obj:
                    jamaat_offset = getattr(user_settings, config["jamaat_offset_attr"])
                    jamaat_time_obj = _add_minutes(azan_time_obj, jamaat_offset)
            else:
                current_app.logger.warning(f"Service: API start time for {p_key} ('{config['api_key']}') is N/A or invalid: {api_start_time_str}. Azan/Jamaat will be N/A.")

        calculated_times[p_key] = {
            "azan": _format_time_obj(azan_time_obj),
            "jamaat": _format_time_obj(jamaat_time_obj)
        }
    
    # Jummah settings (includes Khutbah) - always treated as fixed
    calculated_times["jummah"] = {
        "azan": user_settings.jummah_azan_time,
        "khutbah": user_settings.jummah_khutbah_start_time, # Assuming model has this field
        "jamaat": user_settings.jummah_jamaat_time
    }
    return calculated_times


def get_next_prayer_info_from_service(display_times_today, tomorrow_fajr_display_details, now_datetime_obj):
    """
    Service function to determine the next prayer, time remaining, and countdown states.
    now_datetime_obj is the current datetime passed in for testability and consistency.
    """
    # ... (This function will be similar to `app.py - Part 2 of 3`,
    #      it will just use `parse_time_internal` and `format_time_internal`,
    #      and take `now_datetime_obj` as a parameter.)
    #      I am not repeating it here for brevity, but it is important.
    #      The main change will be that it now creates a list of prayers
    #      and finds the next prayer.
    #      (This can be copied from the previous version of `app.py` and helper functions can be updated)

    # --- BEGIN COPIED AND ADAPTED LOGIC for get_next_prayer_info_from_service ---
    now_time_obj = now_datetime_obj.time()
    is_friday = now_datetime_obj.weekday() == 4
    prayer_sequence_keys = ["fajr", "dhuhr", "asr", "maghrib", "isha"]
    today_prayer_events = []

    for p_key in prayer_sequence_keys:
        prayer_name_display = p_key.capitalize()
        actual_key_for_times = p_key
        
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
                "key": actual_key_for_times,
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
            
    details = {
        "name": "N/A", "azanTime": "N/A", "jamaatTime": "N/A",
        "timeToJamaatMinutes": 0, "isNextDayFajr": False,
        "isJamaatCountdownActive": False, "jamaatCountdownSeconds": 0,
        "isPostJamaatCountdownActive": False, "postJamaatCountdownSeconds": 0,
    }

    if next_prayer_event:
        details["name"] = next_prayer_event["name_display"]
        details["azanTime"] = next_prayer_event["azan"]
        details["jamaatTime"] = next_prayer_event["jamaat"]
        time_diff = next_prayer_event["datetime"] - now_datetime_obj
        details["timeToJamaatMinutes"] = int(time_diff.total_seconds() // 60)
        if 0 < time_diff.total_seconds() <= 120:
            details["isJamaatCountdownActive"] = True
            details["jamaatCountdownSeconds"] = int(time_diff.total_seconds())
    else: # After Isha
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
        if 0 <= time_since_last.total_seconds() < 600: # 10 mins
            if not details["isJamaatCountdownActive"]:
                details["isPostJamaatCountdownActive"] = True
                details["postJamaatCountdownSeconds"] = 600 - int(time_since_last.total_seconds())
    return details
    # --- END COPIED AND ADAPTED LOGIC ---


def get_current_prayer_period_from_service(api_times_today, api_times_tomorrow, now_datetime_obj):
    """
    Service function to determine the current prayer *period* based on API start/end times.
    now_datetime_obj is the current datetime.
    """
    # ... (This function will also be similar to `app.py - Part 3 of 3`,
    #      it will just use `parse_time_internal` and take `now_datetime_obj` as a parameter.)
    #      I am also not repeating it here for brevity.
    #      (This can be copied from the previous version of `app.py` and helper functions can be updated)
      # --- BEGIN COPIED AND ADAPTED LOGIC for get_current_prayer_period_from_service ---
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
            if start_time_obj > end_time_obj: # Overnight period
                if (now_time >= start_time_obj) or (now_time < end_time_obj):
                    return {"name": p_name.upper(), "start": start_time_str, "end": end_time_str}
            elif start_time_obj <= now_time < end_time_obj:
                return {"name": p_name.upper(), "start": start_time_str, "end": end_time_str}
    
    return {"name": "N/A", "start": "N/A", "end": "N/A"}
    # --- END COPIED AND ADAPTED LOGIC ---


def get_geocoded_location(city_name, owm_api_key):
    """
    Geocodes a city name to latitude and longitude using OpenWeatherMap API.
    Uses caching.
    """
    if not owm_api_key:
        current_app.logger.error("Service: OpenWeatherMap API key is not configured.")
        return {"error": "Geocoding service not configured."}
    if not city_name:
        return {"error": "City name is required for geocoding."}

    cache_key = f"geocode_{city_name.lower().replace(' ', '_')}"
    current_timestamp = datetime.datetime.now().timestamp()

    if cache_key in _api_cache:
        cached_data, fetch_time = _api_cache[cache_key]
        if current_timestamp - fetch_time < _GEOCODE_CACHE_EXPIRY_SECONDS:
            current_app.logger.info(f"Service: Using cached geocoding data for {city_name}")
            return cached_data
        else:
            current_app.logger.info(f"Service: Geocoding cache expired for {city_name}.")
            del _api_cache[cache_key]


    current_app.logger.info(f"Service: Geocoding city: {city_name}")
    geocode_url = f"http://api.openweathermap.org/geo/1.0/direct"
    params = {
        "q": city_name,
        "limit": 1, # We only need the top result
        "appid": owm_api_key
    }
    try:
        response = requests.get(geocode_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list) and len(data) > 0:
            location = data[0]
            result = {
                "latitude": location.get("lat"),
                "longitude": location.get("lon"),
                "city_name": location.get("name"),
                "country": location.get("country"),
                "state": location.get("state") 
            }
            _api_cache[cache_key] = (result, current_timestamp)
            current_app.logger.info(f"Service: Successfully geocoded and cached {city_name}: {result}")
            return result
        else:
            current_app.logger.warning(f"Service: No geocoding results found for {city_name}")
            return {"error": "City not found."}
    except requests.exceptions.Timeout:
        current_app.logger.error(f"Service: Timeout error during geocoding for {city_name}.")
        return {"error": "Geocoding service timeout."}
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Service: RequestException during geocoding for {city_name}: {e}", exc_info=True)
        return {"error": f"Geocoding service error: {e}"}
    except Exception as e:
        current_app.logger.error(f"Service: Unexpected error during geocoding for {city_name}: {e}", exc_info=True)
        return {"error": "An unexpected error occurred during geocoding."}