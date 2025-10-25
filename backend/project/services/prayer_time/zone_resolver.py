# This module will contain all functions related to resolving prayer time zones.
import math
import datetime
import os
import json
from flask import current_app
from .cache_layer import get_yearly_calendar_from_cache
from typing import Dict, Any, Optional, Tuple, List

def get_zone_id_from_coords(latitude: float, longitude: float) -> str:
    """
    [Fallback] Generates a grid-based zone ID for a given coordinate.
    This is the fallback safety net for remote areas where administrative
    boundaries are not available.
    """
    grid_size = current_app.config.get("PRAYER_ZONE_GRID_SIZE", 0.2)
    zone_lat = math.floor(latitude / grid_size) * grid_size
    zone_lon = math.floor(longitude / grid_size) * grid_size
    return f"grid_{round(zone_lat, 2)}_{round(zone_lon, 2)}"

def get_zone_id_from_admin_levels(admin_levels: Dict[str, Any], level: str = "admin_2") -> Optional[str]:
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

def determine_final_zone_id(year: int, latitude: float, longitude: float, admin_levels: Optional[Dict[str, Any]], composite_method_key: str, force_refresh: bool) -> Optional[str]:
    """Determines the most appropriate zone ID to use (Admin2, Admin3, or grid)."""
    if not admin_levels:
        current_app.logger.warning(f"No admin levels for ({latitude}, {longitude}). Using fallback grid.")
        return get_zone_id_from_coords(latitude, longitude)

    admin_2_zone_id = get_zone_id_from_admin_levels(admin_levels, level="admin_2")
    admin_3_zone_id = get_zone_id_from_admin_levels(admin_levels, level="admin_3")

    if not admin_3_zone_id:
        return admin_2_zone_id

    admin_2_calendar = get_yearly_calendar_from_cache(admin_2_zone_id, year, composite_method_key)
    if not admin_2_calendar:
        return admin_3_zone_id

    admin_3_calendar = get_yearly_calendar_from_cache(admin_3_zone_id, year, composite_method_key)
    if not admin_3_calendar:
        return admin_3_zone_id

    if not _compare_prayer_times(admin_2_calendar, admin_3_calendar, threshold_seconds=current_app.config['PRAYER_TIME_DIFF_THRESHOLD_SECONDS']):
        current_app.logger.info(f"Admin Level 2 ('{admin_2_zone_id}') is sufficient.")
        return admin_2_zone_id
    else:
        current_app.logger.info(f"Admin Level 3 ('{admin_3_zone_id}') is required.")
        return admin_3_zone_id

def get_zone_center_coords(zone_id: str) -> Tuple[Optional[float], Optional[float]]:
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

def _compare_prayer_times(calendar1_data: List[Dict[str, Any]], calendar2_data: List[Dict[str, Any]], threshold_seconds: Optional[int] = None) -> bool:
    """
    Compares two yearly prayer time calendars and returns True if the difference
    between any corresponding prayer time (Fajr, Dhuhr, Asr, Maghrib, Isha) 
    exceeds the given threshold for any day of the year.
    """
    if threshold_seconds is None:
        threshold_seconds = current_app.config['PRAYER_TIME_DIFF_THRESHOLD_SECONDS']

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
                    
                    dummy_date = datetime.date(2000, 1, 1)
                    dt1 = datetime.datetime.combine(dummy_date, time1_obj)
                    dt2 = datetime.datetime.combine(dummy_date, time2_obj)

                    diff_seconds = abs((dt1 - dt2).total_seconds())

                    if diff_seconds > threshold_seconds:
                        current_app.logger.info(f"Time difference for {prayer_name} on day {day_idx} exceeds {threshold_seconds}s: {diff_seconds}s")
                        return True
                except ValueError:
                    current_app.logger.warning(f"Could not parse time string for comparison: {time1_str} or {time2_str}")
                    continue
    return False

def get_method_id_for_country(country_code: str) -> int:
    """
    Determines the most common prayer time calculation method for a given country.
    It reads a mapping from a JSON file, making it easy to update and manage.
    This is the core of the "Automatic" setting.

    Args:
        country_code (str): The two-letter ISO 3166-1 alpha-2 country code.

    Returns:
        int: The ID of the recommended calculation method.
    """
    backend_root_path = os.path.dirname(current_app.root_path)
    map_file_path = os.path.join(backend_root_path, current_app.config['COUNTRY_METHOD_MAP_PATH'])
    
    try:
        with open(map_file_path, 'r') as f:
            mapping_data = json.load(f)
        
        country_map = mapping_data.get("country_map", {})
        default_id = mapping_data.get("default_method_id", 3) # Default to MWL if not specified

        method_id = country_map.get(country_code.upper(), default_id)
        current_app.logger.info(f"Automatic method selection for country '{country_code}': Chose method ID {method_id}.")
        return method_id

    except (FileNotFoundError, json.JSONDecodeError) as e:
        current_app.logger.error(f"Could not load or parse country_method_map.json: {e}")
        return 3