from ..helpers.constants import PRAYER_CONFIG_MAP
from typing import Dict, Any, Optional, List, Tuple
import datetime
from flask import current_app

def parse_time_str(time_str: str) -> Optional[datetime.time]:
    if not time_str or time_str.lower() == "n/a": 
        return None
    
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.datetime.strptime(time_str.strip(), fmt).time()
        except ValueError:
            continue
            
    current_app.logger.warning(f"Service: Invalid or unrecognized time string format for parsing: {time_str}")
    return None

def format_time_obj(time_obj: Optional[datetime.time]) -> str:
    if not time_obj: return "N/A"
    return time_obj.strftime("%H:%M")

def add_minutes(time_obj: Optional[datetime.time], minutes_to_add: Optional[int]) -> Optional[datetime.time]:
    if not time_obj or minutes_to_add is None: return None
    dummy_date = datetime.date.min
    full_datetime = datetime.datetime.combine(dummy_date, time_obj)
    new_datetime = full_datetime + datetime.timedelta(minutes=int(minutes_to_add))
    return new_datetime.time()

def apply_boundary_check(
    time_to_check: Optional[datetime.time], 
    start_boundary_str: Optional[str], 
    end_boundary_str: Optional[str],
    prayer_name: str,
    time_type: str # "Azan" or "Jamaat"
) -> Tuple[Optional[datetime.time], Optional[str]]:
    """
    Checks if a time falls within its valid boundaries. Auto-corrects and returns a warning if it doesn't.
    Includes an 8-minute buffer for the end boundary as per business logic.
    """
    if not time_to_check: 
        return None, None

    start_boundary_obj = parse_time_str(start_boundary_str)
    end_boundary_obj = parse_time_str(end_boundary_str)
    warning = None

    if not start_boundary_obj or not end_boundary_obj:
        return time_to_check, None
    
    # Business Logic: Jamaat time must be at least 8 minutes before the prayer period ends.
    buffer_minutes = 8
    end_boundary_with_buffer_obj = add_minutes(end_boundary_obj, -buffer_minutes)

    original_time_str = format_time_obj(time_to_check)

    # Check 1: Time must not be before the prayer period starts.
    if time_to_check < start_boundary_obj:
        warning = (
            f"Your {time_type} time for {prayer_name} ({original_time_str}) was before the prayer's start time "
            f"({format_time_obj(start_boundary_obj)}) and has been auto-corrected."
        )
        time_to_check = start_boundary_obj
        current_app.logger.warning(f"Boundary Check Triggered: {warning}")

    # Check 2: Time must not be after the (buffered) prayer period ends.
    if time_to_check > end_boundary_with_buffer_obj:
        warning = (
            f"Your {time_type} time for {prayer_name} ({original_time_str}) was too close to the prayer's end time "
            f"and has been auto-corrected to {format_time_obj(end_boundary_with_buffer_obj)}."
        )
        time_to_check = end_boundary_with_buffer_obj
        current_app.logger.warning(f"Boundary Check Triggered: {warning}")

    return time_to_check, warning

def calculate_display_times_from_service(user_settings: Any, api_times_today: Dict[str, Any], api_times_tomorrow: Dict[str, Any], app_config: Dict[str, Any], calculation_date: datetime.date) -> Tuple[Dict[str, Any], bool, List[str]]:
    calculated_times = {}
    needs_db_update = False
    warnings = []

    if not api_times_today: api_times_today = {}
    if not api_times_tomorrow: api_times_tomorrow = {}

    last_api_times = {}
    if user_settings.last_api_times_for_threshold:
        try:
            last_api_times = json.loads(user_settings.last_api_times_for_threshold)
        except (json.JSONDecodeError, TypeError):
            current_app.logger.warning("Could not parse last_api_times_for_threshold JSON. Resetting.")
            needs_db_update = True

    for p_key, config in PRAYER_CONFIG_MAP.items():
        is_fixed = getattr(user_settings, config["is_fixed_attr"], False)
        prayer_display_name = p_key.capitalize()
        
        azan_time_obj, jamaat_time_obj = None, None
        
        api_start_time_str = api_times_today.get(config["api_key"])
        start_boundary_str = api_start_time_str
        end_boundary_key = config["end_boundary_key"]
        end_boundary_str = api_times_tomorrow.get("Fajr") if end_boundary_key == "Fajr_Tomorrow" else api_times_today.get(end_boundary_key)

        if is_fixed:
            azan_time_obj = parse_time_str(getattr(user_settings, config["fixed_azan_attr"]))
            jamaat_time_obj = parse_time_str(getattr(user_settings, config["fixed_jamaat_attr"]))

            # --- BUG FIX: Apply boundary check for fixed times ---
            azan_time_obj, azan_warning = apply_boundary_check(azan_time_obj, start_boundary_str, end_boundary_str, prayer_display_name, "Azan")
            if azan_warning: warnings.append(azan_warning)
            
            jamaat_time_obj, jamaat_warning = apply_boundary_check(jamaat_time_obj, start_boundary_str, end_boundary_str, prayer_display_name, "Jamaat")
            if jamaat_warning: warnings.append(jamaat_warning)

        else: # Offset logic
            if api_start_time_str:
                api_time_to_use_str = api_start_time_str
                last_api_time_str = last_api_times.get(config["api_key"])
                
                # Threshold logic
                if last_api_time_str and user_settings.threshold_minutes > 0:
                    # ... (threshold logic remains the same)
                    pass # Simplified for brevity

                api_start_time_obj = parse_time_str(api_time_to_use_str)
                if api_start_time_obj:
                    # Calculate Azan with offset
                    azan_offset = getattr(user_settings, config["azan_offset_attr"])
                    calculated_azan_obj = add_minutes(api_start_time_obj, azan_offset)
                    azan_time_obj, azan_warning = apply_boundary_check(calculated_azan_obj, start_boundary_str, end_boundary_str, prayer_display_name, "Azan")
                    if azan_warning: warnings.append(azan_warning)
                    
                    # Calculate Jamaat with offset
                    if azan_time_obj:
                        jamaat_offset = getattr(user_settings, config["jamaat_offset_attr"])
                        # User wants Jamaat offset relative to the (now corrected) Azan time
                        calculated_jamaat_obj = add_minutes(azan_time_obj, jamaat_offset)
                        jamaat_time_obj, jamaat_warning = apply_boundary_check(calculated_jamaat_obj, start_boundary_str, end_boundary_str, prayer_display_name, "Jamaat")
                        if jamaat_warning: warnings.append(jamaat_warning)

        calculated_times[p_key] = {"azan": format_time_obj(azan_time_obj), "jamaat": format_time_obj(jamaat_time_obj)}
    
    # ... (rest of the function for Jummah, Iftari, etc. remains the same) ...
    # This part is simplified as it's not the focus of the bug fix.
    
    maghrib_time_str = api_times_today.get("Maghrib")
    calculated_times["iftari"] = {"time": format_time_obj(parse_time_str(maghrib_time_str))}
    imsak_time_str = api_times_today.get("Imsak")
    calculated_times["sehri_end"] = {"time": format_time_obj(parse_time_str(imsak_time_str))}
    # ... and so on for Jummah, Sunrise, etc.

    return calculated_times, needs_db_update, warnings

# ... (rest of the file: get_next_prayer_info_from_service, get_current_prayer_period_from_service) ...
# These functions do not need changes for this bug fix.