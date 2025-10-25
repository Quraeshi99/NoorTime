# This module will contain all functions related to caching prayer times.
import json
from flask import current_app
from project.models import PrayerZoneCalendar
from project.extensions import redis_client
from typing import Dict, Any, Optional, List
from project.metrics import CACHE_HITS, CACHE_MISSES
from redis import exceptions as redis_exceptions

def get_yearly_calendar_from_cache(zone_id: str, year: int, composite_method_key: str) -> Optional[List[Dict[str, Any]]]:
    """
    New caching function that checks Redis first, then the database.
    If found in DB, it caches to Redis for future requests.
    """
    schema_version = current_app.config['CACHE_SCHEMA_VERSION']
    redis_key = f"calendar:{schema_version}:{zone_id}:{year}:{composite_method_key}"

    # 1. Check Redis Cache first
    cached_data = _cache_get_json(redis_key)
    if cached_data:
        CACHE_HITS.labels(cache_type='yearly', zone_id=zone_id, year=year).inc()
        current_app.logger.info(f"Redis Cache HIT for zone '{zone_id}', year {year}.")
        return cached_data

    CACHE_MISSES.labels(cache_type='yearly', zone_id=zone_id, year=year).inc()
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
        _cache_set_json(redis_key, calendar_data, ttl=current_app.config['REDIS_TTL_YEARLY_CALENDAR'])
        current_app.logger.info(f"Populated Redis cache for zone '{zone_id}', year {year}.")
            
        return calendar_data
    
    current_app.logger.info(f"DB Cache MISS for zone '{zone_id}', year {year}.")
    return None

    def _cache_get_json(key: str) -> Optional[Dict[str, Any]]:
    """Helper function to safely get and deserialize a JSON object from Redis."""
    try:
        cached_data = redis_client.get(key)
        if cached_data:
            return json.loads(cached_data)
        return None
    except (redis_exceptions.RedisError, json.JSONDecodeError) as e:
        current_app.logger.error(f"Redis GET or JSON load failed for key {key}: {e}", exc_info=True)
        return None

def _cache_set_json(key: str, value: Any, ttl: int) -> None:
    """Helper function to safely serialize and set a JSON object in Redis."""
    try:
        redis_client.set(key, json.dumps(value), ex=ttl)
    except redis_exceptions.RedisError as e:
        current_app.logger.error(f"Redis SET failed for key {key}: {e}", exc_info=True)
def cache_daily_prayer_times(final_zone_id: str, today_date_str: str, composite_method_key: str, daily_data: Dict[str, Any]) -> None:
    """Caches the prayer times for a single day to prevent API hammering."""
    if daily_data:
        schema_version = current_app.config['CACHE_SCHEMA_VERSION']
        redis_key = f"daily:{schema_version}:{final_zone_id}:{today_date_str}:{composite_method_key}"
        _cache_set_json(redis_key, daily_data, ttl=current_app.config['REDIS_TTL_DAILY_CACHE'])    