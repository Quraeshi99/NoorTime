# project/utils/prayer_display_helper.py

from datetime import datetime, timedelta



def get_prayer_info(prayer_name, api_times, user_settings):
    """
    Calculates Azan and Jama'at times for a specific prayer based on API times and user settings.
    This is a helper for tomorrow's Fajr display.
    """
    from .time_utils import parse_time_internal, format_time_internal, add_minutes_to_time

    azan_time = "N/A"
    jamaat_time = "N/A"

    # Get settings for the specific prayer
    is_fixed = getattr(user_settings, f"{prayer_name.lower()}_is_fixed", False)
    fixed_azan = getattr(user_settings, f"{prayer_name.lower()}_fixed_azan", "N/A")
    fixed_jamaat = getattr(user_settings, f"{prayer_name.lower()}_fixed_jamaat", "N/A")
    azan_offset = getattr(user_settings, f"{prayer_name.lower()}_azan_offset", 0)
    jamaat_offset = getattr(user_settings, f"{prayer_name.lower()}_jamaat_offset", 0)

    if is_fixed:
        azan_time = fixed_azan
        jamaat_time = fixed_jamaat
    else:
        api_start_time_str = api_times.get(prayer_name)
        api_start_time_obj = parse_time_internal(api_start_time_str)

        if api_start_time_obj:
            calculated_azan_obj = add_minutes_to_time(api_start_time_obj, azan_offset)
            if calculated_azan_obj:
                azan_time = format_time_internal(calculated_azan_obj)
                calculated_jamaat_obj = add_minutes_to_time(calculated_azan_obj, jamaat_offset)
                if calculated_jamaat_obj:
                    jamaat_time = format_time_internal(calculated_jamaat_obj)

    return {"azan": azan_time, "jamaat": jamaat_time}
