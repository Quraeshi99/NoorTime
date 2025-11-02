from typing import Dict, Any, Optional
import datetime
import zoneinfo
from flask import current_app
from .prayer_time.api_adapter import get_daily_prayer_times_from_api
from .prayer_time.cache_layer import get_yearly_calendar_from_cache, cache_daily_prayer_times
from .prayer_time.zone_resolver import determine_final_zone_id, get_method_id_for_country
from .geocoding_service import get_admin_levels_from_coords
from ..extensions import redis_client
from ..models import PrayerZoneCalendar

def _check_and_trigger_grace_period_fetch(final_zone_id: str, calculation_method_key: str, latitude: float, longitude: float) -> None:
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

    now = datetime.datetime.now(zoneinfo.ZoneInfo('UTC'))
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
            # If it's not cached, we trigger a background Celery task to fetch it.
            current_app.logger.info(f"GRACE PERIOD: Next year's calendar for zone '{final_zone_id}' not found. Triggering Celery task.")
            
            # Parse the composite key to get individual method IDs for the task
            try:
                method_id, asr_juristic_id, high_latitude_method_id = map(int, calculation_method_key.split('-'))
                
                fetch_and_cache_yearly_calendar_task.delay(
                    zone_id=final_zone_id,
                    year=next_year,
                    method_id=method_id,
                    asr_juristic_id=asr_juristic_id,
                    high_latitude_method_id=high_latitude_method_id,
                    latitude=latitude,
                    longitude=longitude
                )
            except ValueError as e:
                current_app.logger.error(f"Could not parse composite_method_key '{calculation_method_key}' to trigger background task: {e}")
        else:
            current_app.logger.debug(f"GRACE PERIOD: Next year's calendar for zone '{final_zone_id}' already exists. No fetch needed.")


from ..tasks import fetch_and_cache_yearly_calendar_task

# --- Main Service Function ---

def get_api_prayer_times_for_date_from_service(date_obj: datetime.date, latitude: float, longitude: float, method_id: int, asr_juristic_id: int, high_latitude_method_id: int, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    The core service function, now refactored for a Redis-backed hybrid caching strategy.
    It provides an instant response even for new, uncached locations.
    """
    year = date_obj.year
    today_date_str = date_obj.strftime("%d-%m-%Y")

    # 1. Determine Zone ID
    admin_levels = get_admin_levels_from_coords(latitude, longitude)
    
    if method_id == current_app.config.get('AUTOMATIC_METHOD_ID'):
        country_code = admin_levels.get('country_code', 'XX') if admin_levels else 'XX'
        method_id = get_method_id_for_country(country_code)

    composite_method_key = f"{method_id}-{asr_juristic_id}-{high_latitude_method_id}"

    final_zone_id = determine_final_zone_id(year, latitude, longitude, admin_levels, composite_method_key, force_refresh)

    if not final_zone_id:
        current_app.logger.error(f"Could not determine a final zone ID for ({latitude}, {longitude}).")
        return None

    # 2. Attempt to get the full yearly calendar from cache (Redis or DB)
    yearly_calendar_data = get_yearly_calendar_from_cache(final_zone_id, year, composite_method_key)

    if yearly_calendar_data:
        for day_data in yearly_calendar_data:
            if day_data.get('date', {}).get('gregorian', {}).get('date') == today_date_str:
                return day_data
        current_app.logger.error(f"Data for {today_date_str} not found in cached calendar for zone {final_zone_id}")
        return None

    # 3. Cache MISS: Hybrid approach
    else:
        current_app.logger.info(f"COMPLETE CACHE MISS for zone '{final_zone_id}'. Using Hybrid Approach.")
        
        # Implement Redis lock to prevent race conditions (thundering herd problem).
        # Only the first request for an uncached zone will trigger the background fetch.
        lock_key = f"lock:calendar_fetch:{final_zone_id}:{year}:{composite_method_key}"
        # Set lock with a 10-minute timeout to prevent permanent locks.
        if redis_client.set(lock_key, "1", nx=True, ex=600):
            current_app.logger.info(f"Acquired lock for {lock_key}. Triggering background task.")
            fetch_and_cache_yearly_calendar_task.delay(
                zone_id=final_zone_id,
                year=year,
                method_id=method_id,
                asr_juristic_id=asr_juristic_id,
                high_latitude_method_id=high_latitude_method_id,
                latitude=latitude,
                longitude=longitude
            )
        else:
            current_app.logger.info(f"Lock for {lock_key} is already held. Skipping background task trigger.")

        # --- Instant Gratification --- 
        # Immediately fetch and return just today's prayer times for the user.
        daily_data = get_daily_prayer_times_from_api(
            date_obj=date_obj,
            latitude=latitude,
            longitude=longitude,
            method_id=method_id,
            asr_juristic_id=asr_juristic_id,
            high_latitude_method_id=high_latitude_method_id
        )
        
        # Cache the single-day result for a short time to prevent API hammering
        cache_daily_prayer_times(final_zone_id, today_date_str, composite_method_key, daily_data)

        return daily_data