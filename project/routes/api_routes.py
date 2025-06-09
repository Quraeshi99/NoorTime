# project/routes/api_routes.py
from project.extensions import limiter
from flask import Blueprint, jsonify, request, current_app, flash
from flask_login import current_user, login_required
import datetime
import json # For logging complex objects

from .. import db, csrf # csrf for manual protection if needed on specific API routes
from ..models import User, UserSettings
from ..services.prayer_time_service import (
    get_api_prayer_times_for_date_from_service,
    calculate_display_times_from_service,
    get_next_prayer_info_from_service,
    get_current_prayer_period_from_service,
    get_geocoded_location # For city name to lat/lon
)
# Import the helper function
from ..utils.prayer_display_helper import get_tomorrow_display_for_current_prayer, get_prayer_info

api_bp = Blueprint('api', __name__) # url_prefix='/api' app फैक्ट्री में सेट होगा

# Helper to get user's effective location and calculation method
def get_user_location_and_method(user):
    if user.is_authenticated and user.default_latitude is not None and user.default_longitude is not None and user.default_calculation_method:
        lat = user.default_latitude
        lon = user.default_longitude
        method_key = user.default_calculation_method
        city_name = user.default_city_name or "User's Home"
    else: # Guest user or user hasn't set defaults
        # For guest, these might come from localStorage via request, or use app defaults
        # For simplicity now, use app defaults for guest's initial load.
        # JS can override these by passing params in subsequent API calls if needed.
        lat = float(current_app.config.get('DEFAULT_LATITUDE', 19.2183))
        lon = float(current_app.config.get('DEFAULT_LONGITUDE', 72.8493))
        method_key = current_app.config.get('DEFAULT_CALCULATION_METHOD', 'Karachi')
        city_name = "Default Location"
        
    return lat, lon, method_key, city_name

@api_bp.route('/initial_prayer_data')
def initial_prayer_data():
    try:
        current_app.logger.info(f"API Request: /initial_prayer_data by user: {'Authenticated ' + current_user.email if current_user.is_authenticated else 'Guest'}")
        
        # Determine location and method based on user or defaults
        req_lat = request.args.get('lat', type=float)
        req_lon = request.args.get('lon', type=float)
        req_method = request.args.get('method') # e.g., 'Karachi', 'ISNA'
        req_city = request.args.get('city')

        if current_user.is_authenticated:
            lat, lon, method_key, city_name = get_user_location_and_method(current_user)
        elif req_lat is not None and req_lon is not None and req_method is not None:
            lat, lon, method_key, city_name = req_lat, req_lon, req_method, req_city or "Custom Location"
            current_app.logger.info(f"Guest using query params for location: Lat={lat}, Lon={lon}, Method={method_key}")
        else: # Guest, no query params, use app defaults
            lat = float(current_app.config.get('DEFAULT_LATITUDE', 19.2183))
            lon = float(current_app.config.get('DEFAULT_LONGITUDE', 72.8493))
            method_key = current_app.config.get('DEFAULT_CALCULATION_METHOD', 'Karachi')
            city_name = "Default Location (e.g., Mumbai)"
            current_app.logger.info(f"Guest using app default location: Lat={lat}, Lon={lon}, Method={method_key}")

        today_date = datetime.date.today()
        tomorrow_date = today_date + datetime.timedelta(days=1)

        api_times_today = get_api_prayer_times_for_date_from_service(today_date, lat, lon, method_key)
        api_times_tomorrow = get_api_prayer_times_for_date_from_service(tomorrow_date, lat, lon, method_key)

        if not api_times_today:
            current_app.logger.error(f"Failed to get API times for today (Lat:{lat}, Lon:{lon}, Method:{method_key}). Returning error.")
            return jsonify({"error": "Could not fetch prayer times from external API."}), 503
        
        # User specific settings for prayer times (fixed/offset)
        user_prayer_settings_obj = None
        if current_user.is_authenticated:
            user_prayer_settings_obj = UserSettings.query.filter_by(user_id=current_user.id).first()
        
        if not user_prayer_settings_obj: # Guest or user has no settings row (shouldn't happen for logged-in)
            # Create a temporary default settings object for guests or fallback
            user_prayer_settings_obj = UserSettings() # Uses model defaults
            if not current_user.is_authenticated:
                current_app.logger.info("Using default model prayer settings for Guest on initial_prayer_data.")

        display_times = calculate_display_times_from_service(user_prayer_settings_obj, api_times_today, current_app.config)
        
        # Calculate tomorrow's Fajr display details (Azan and Jamaat)
        tomorrow_fajr_display = get_prayer_info("Fajr", api_times_tomorrow, user_prayer_settings_obj)
        
        # Get user's time format preference
        time_format_pref = '12h' # Default for guest
        if current_user.is_authenticated and current_user.time_format_preference:
            time_format_pref = current_user.time_format_preference
        elif not current_user.is_authenticated and request.args.get('time_format'): # Guest temp preference
            time_format_pref = request.args.get('time_format') if request.args.get('time_format') in ['12h', '24h'] else '12h'

        data_to_send = {
            "currentLocationName": city_name, # Name of the location for which API times are fetched
            "prayerTimes": display_times, 
            "apiTimesForDisplay": { 
                "Sunrise": api_times_today.get("Sunrise"), 
                "Sunset": api_times_today.get("Sunset"),
                "Zawal_Start_Approx": api_times_today.get("Zawal_Start_Approx"),
                "Zawal_End_Approx": api_times_today.get("Dhuhr"),
                "Imsak_Sahar": api_times_today.get("Imsak"),
                "Maghrib_Iftar": api_times_today.get("Maghrib"),
                "CurrentTemperature": api_times_today.get("temperatureC", "N/A"), # Safe get with default
                "WeatherDescription": api_times_today.get("weather_description", "N/A") # Safe get with default
            },
            "dateInfo": {
                "gregorian": f"{api_times_today.get('gregorian_date', 'N/A')}, {api_times_today.get('gregorian_weekday', 'N/A')}",
                "hijri": f"{api_times_today.get('hijri_date', 'N/A')} ({api_times_today.get('hijri_month_en', 'N/A')} {api_times_today.get('hijri_year', 'N/A')} AH)"
            },
            "tomorrowFajrDisplay": tomorrow_fajr_display,
            "userPreferences": { # Send user's preferences to JS
                "timeFormat": time_format_pref,
                "calculationMethod": method_key, # The key used for API call
                "homeLatitude": lat if current_user.is_authenticated else None, # Only send if logged in and set
                "homeLongitude": lon if current_user.is_authenticated else None,
            },
            "isUserAuthenticated": current_user.is_authenticated
        }
        current_app.logger.debug(f"Sending /api/initial_prayer_data response")
        return jsonify(data_to_send)
    
    except Exception as e:
        current_app.logger.error(f"Error in initial_prayer_data: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error occurred."}), 500


@api_bp.route('/live_data')
def live_data():
    try:
        # This is called every second. Keep it very lean.
        req_lat = request.args.get('lat', type=float)
        req_lon = request.args.get('lon', type=float)
        req_method = request.args.get('method')

        user_prayer_settings_obj = None
        tomorrow_fajr_details_for_service = {"azan": "N/A", "jamaat": "N/A"} # For get_next_prayer_info

        if current_user.is_authenticated:
            lat, lon, method_key, _ = get_user_location_and_method(current_user)
            user_prayer_settings_obj = UserSettings.query.filter_by(user_id=current_user.id).first()
        elif req_lat is not None and req_lon is not None and req_method is not None:
            lat, lon, method_key = req_lat, req_lon, req_method
        else: # Guest, no query params, use app defaults
            lat = float(current_app.config.get('DEFAULT_LATITUDE', 19.2183))
            lon = float(current_app.config.get('DEFAULT_LONGITUDE', 72.8493))
            method_key = current_app.config.get('DEFAULT_CALCULATION_METHOD', 'Karachi')
        
        if not user_prayer_settings_obj: # For Guest or if settings somehow missing for logged-in user
            user_prayer_settings_obj = UserSettings() # Temporary object with model defaults

        now = datetime.datetime.now()
        today_date = now.date()
        tomorrow_date = today_date + datetime.timedelta(days=1)

        # Use cached API times if available, force_refresh=False (default in service)
        api_times_today = get_api_prayer_times_for_date_from_service(today_date, lat, lon, method_key)
        api_times_tomorrow = get_api_prayer_times_for_date_from_service(tomorrow_date, lat, lon, method_key)

        # Better error handling for API failures
        if not api_times_today:
            current_app.logger.error("API times for today not available in live_data")
            return jsonify({"error": "Prayer times temporarily unavailable"}), 503
            
        if not api_times_tomorrow:
            current_app.logger.warning("API times for tomorrow not available in live_data. Using fallback.")
            api_times_tomorrow = {"Fajr": "N/A"}

        display_times_today = calculate_display_times_from_service(user_prayer_settings_obj, api_times_today, current_app.config)
        
        # Prepare tomorrow's Fajr details for next_prayer_info service
        from ..utils.time_utils import parse_time_internal, format_time_internal, add_minutes_to_time
        
        tomorrow_fajr_api_start_live = api_times_tomorrow.get("Fajr")
        if user_prayer_settings_obj.fajr_is_fixed:
            tomorrow_fajr_details_for_service["azan"] = user_prayer_settings_obj.fajr_fixed_azan
            tomorrow_fajr_details_for_service["jamaat"] = user_prayer_settings_obj.fajr_fixed_jamaat
        elif tomorrow_fajr_api_start_live and tomorrow_fajr_api_start_live != "N/A":
            api_fajr_tmrw_obj_live = parse_time_internal(tomorrow_fajr_api_start_live)
            if api_fajr_tmrw_obj_live:
                azan_obj_live = add_minutes_to_time(api_fajr_tmrw_obj_live, user_prayer_settings_obj.fajr_azan_offset)
                tomorrow_fajr_details_for_service["azan"] = format_time_internal(azan_obj_live)
                if azan_obj_live:
                    jamaat_obj_live = add_minutes_to_time(azan_obj_live, user_prayer_settings_obj.fajr_jamaat_offset)
                    tomorrow_fajr_details_for_service["jamaat"] = format_time_internal(jamaat_obj_live)

        next_prayer = get_next_prayer_info_from_service(display_times_today, tomorrow_fajr_details_for_service, now)
        current_prayer_pd = get_current_prayer_period_from_service(api_times_today, api_times_tomorrow, now)

        time_format_pref = '12h' # Default for guest
        if current_user.is_authenticated and current_user.time_format_preference:
            time_format_pref = current_user.time_format_preference
        elif not current_user.is_authenticated and request.args.get('time_format'):
            time_format_pref = request.args.get('time_format') if request.args.get('time_format') in ['12h', '24h'] else '12h'

        live_update_data = {
            "currentTime": now.strftime("%I:%M:%S %p") if time_format_pref == '12h' else now.strftime("%H:%M:%S"),
            "currentDay": now.strftime("%A").upper(), # SUNDAY, MONDAY...
            "nextPrayer": next_prayer,
            "currentNamazPeriod": current_prayer_pd,
            "fastingTimes": {
                "sahr": api_times_today.get("Imsak"),
                "iftar": api_times_today.get("Maghrib") 
            }
        }
        return jsonify(live_update_data)
    
    except Exception as e:
        current_app.logger.error(f"Error in live_data: {str(e)}", exc_info=True)
        return jsonify({"error": "Unable to fetch live data"}), 500


@api_bp.route('/user/settings/update', methods=['POST'])
@login_required
def update_user_settings():
    try:
        user = current_user
        user_settings = UserSettings.query.filter_by(user_id=user.id).first()
        if not user_settings:
            # This should not happen if user registration creates settings
            user_settings = UserSettings(user_id=user.id)
            db.session.add(user_settings)

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided for update."}), 400

        current_app.logger.info(f"User {user.email} updating settings with data keys: {list(data.keys())}")

        # Update User model specific settings (profile, default location, preferences)
        if 'profile' in data and 'name' in data['profile']:
            user.name = data['profile']['name']
            
        if 'home_location' in data:
            loc_data = data['home_location']
            user.default_latitude = loc_data.get('latitude', user.default_latitude)
            user.default_longitude = loc_data.get('longitude', user.default_longitude)
            user.default_city_name = loc_data.get('city_name', user.default_city_name)
            
        if 'preferences' in data:
            pref_data = data['preferences']
            user.default_calculation_method = pref_data.get('calculation_method', user.default_calculation_method)
            user.time_format_preference = pref_data.get('time_format', user.time_format_preference)
            
            # Update UserSettings model specific settings
            user_settings.adjust_timings_with_api_location = pref_data.get('adjust_offsets_on_location_change', 
                                                                         user_settings.adjust_timings_with_api_location)
            user_settings.auto_update_api_location = pref_data.get('auto_update_location', 
                                                                  user_settings.auto_update_api_location)

        # Update prayer settings
        if 'prayer_times' in data:
            prayer_settings_data = data['prayer_times']
            for p_name in ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha', 'jummah']:
                if p_name in prayer_settings_data:
                    p_data = prayer_settings_data[p_name]
                    if p_name == "jummah": # Jummah has simpler fixed structure
                        user_settings.jummah_azan_time = p_data.get('fixed_azan', user_settings.jummah_azan_time)
                        # Only set khutbah time if the field exists in your model
                        if hasattr(user_settings, 'jummah_khutbah_start_time'):
                            user_settings.jummah_khutbah_start_time = p_data.get('fixed_khutbah', 
                                                                               user_settings.jummah_khutbah_start_time)
                        user_settings.jummah_jamaat_time = p_data.get('fixed_jamaat', user_settings.jummah_jamaat_time)
                        continue

                    # For other prayers
                    is_fixed_str = str(p_data.get('is_fixed', getattr(user_settings, f"{p_name}_is_fixed"))).lower()
                    is_fixed = is_fixed_str == 'true'
                    setattr(user_settings, f"{p_name}_is_fixed", is_fixed)

                    if is_fixed:
                        setattr(user_settings, f"{p_name}_fixed_azan", 
                               p_data.get('fixed_azan', getattr(user_settings, f"{p_name}_fixed_azan")))
                        setattr(user_settings, f"{p_name}_fixed_jamaat", 
                               p_data.get('fixed_jamaat', getattr(user_settings, f"{p_name}_fixed_jamaat")))
                    else:
                        try:
                            azan_offset = int(p_data.get('azan_offset', getattr(user_settings, f"{p_name}_azan_offset")))
                            jamaat_offset = int(p_data.get('jamaat_offset', getattr(user_settings, f"{p_name}_jamaat_offset")))
                            setattr(user_settings, f"{p_name}_azan_offset", azan_offset)
                            setattr(user_settings, f"{p_name}_jamaat_offset", jamaat_offset)
                        except (ValueError, TypeError) as e:
                            current_app.logger.warning(f"Invalid offset value for {p_name} during settings update: {e}")
                            # Keep old values

        db.session.commit()
        current_app.logger.info(f"Settings for user {user.email} updated successfully.")
        flash('Your settings have been saved successfully!', 'success')
        return jsonify({"status": "success", "message": "Settings saved successfully!"})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error updating settings for {current_user.email}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Error saving settings: {str(e)}"}), 500


@api_bp.route('/geocode', methods=['GET'])
@limiter.limit("50 per hour")  # Increased from 20 to 50
def geocode_city():
    city_name = request.args.get('city')
    if not city_name or len(city_name.strip()) < 2:
        return jsonify({"error": "Valid city name parameter is required"}), 400
    
    try:
        location_data = get_geocoded_location(city_name.strip(), current_app.config.get('OPENWEATHERMAP_API_KEY'))
        
        if location_data and "error" not in location_data:
            return jsonify(location_data)
        elif location_data and "error" in location_data:
            return jsonify({"error": location_data["error"]}), 404
        else:
            return jsonify({"error": "Failed to geocode location"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in geocode_city: {str(e)}", exc_info=True)
        return jsonify({"error": "Geocoding service temporarily unavailable"}), 503
