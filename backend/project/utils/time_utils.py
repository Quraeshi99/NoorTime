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