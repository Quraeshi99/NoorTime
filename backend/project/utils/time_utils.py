import datetime

def parse_time_internal(time_str):
    """
    Parses a time string (HH:MM) into a datetime.time object.
    Returns None if parsing fails.
    """
    if not time_str or time_str.lower() == "n/a":
        return None
    try:
        return datetime.datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return None

def format_time_internal(time_obj):
    """
    Formats a datetime.time object into a HH:MM string.
    Returns "N/A" if time_obj is None.
    """
    if not time_obj: return "N/A"
    return time_obj.strftime("%H:%M")

def add_minutes_to_time(time_obj, minutes_to_add):
    """
    Adds minutes to a datetime.time object. Handles crossing midnight.
    Returns None if inputs are invalid.
    """
    if not time_obj or minutes_to_add is None: return None
    dummy_date = datetime.date.min # Use a dummy date to create a datetime object
    full_datetime = datetime.datetime.combine(dummy_date, time_obj)
    new_datetime = full_datetime + datetime.timedelta(minutes=int(minutes_to_add))
    return new_datetime.time()

def add_seconds_to_time(time_obj, seconds_to_add):
    """

    Adds seconds to a datetime.time object. Handles crossing midnight.
    Returns None if inputs are invalid.
    """
    if not time_obj or seconds_to_add is None: return None
    dummy_date = datetime.date.min
    full_datetime = datetime.datetime.combine(dummy_date, time_obj)
    new_datetime = full_datetime + datetime.timedelta(seconds=int(seconds_to_add))
    return new_datetime.time()

def get_prayer_key_for_tomorrow(current_prayer_name, today_date):
    """
    Determines the key for the prayer to be displayed for the next day,
    with special handling for Jummah.

    Args:
        current_prayer_name (str): The name of the current prayer period (e.g., 'DHUHR').
        today_date (datetime.date): The current date.

    Returns:
        str: The key for the prayer to be shown for tomorrow (e.g., 'Jummah', 'Dhuhr').
    """
    # The key for get_prayer_info needs to be capitalized e.g. 'Fajr', 'Dhuhr'
    prayer_to_show_for_tomorrow_key = current_prayer_name.capitalize()

    # Handle non-prayer periods by defaulting to Fajr
    main_prayer_keys = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
    if prayer_to_show_for_tomorrow_key not in main_prayer_keys:
        prayer_to_show_for_tomorrow_key = 'Fajr'

    today_weekday = today_date.weekday()  # Monday is 0, Thursday is 3, Friday is 4

    if today_weekday == 3:  # If it's Thursday
        if current_prayer_name.upper() == 'DHUHR':
            prayer_to_show_for_tomorrow_key = 'Jummah'
    elif today_weekday == 4:  # If it's Friday
        if current_prayer_name.upper() == 'DHUHR':  # The Dhuhr period on Friday is effectively Jummah
            prayer_to_show_for_tomorrow_key = 'Dhuhr'  # For Saturday, we show Dhuhr

    return prayer_to_show_for_tomorrow_key
