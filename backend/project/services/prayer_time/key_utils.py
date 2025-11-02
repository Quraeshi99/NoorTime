# project/services/prayer_time/key_utils.py

from flask import current_app

def generate_calendar_redis_key(zone_id: str, year: int, composite_method_key: str) -> str:
    """Generates a consistent Redis key for yearly prayer time calendars."""
    schema_version = current_app.config.get('CACHE_SCHEMA_VERSION', 'v1')
    return f"calendar:{schema_version}:{zone_id}:{year}:{composite_method_key}"

def generate_daily_redis_key(zone_id: str, date_str: str, composite_method_key: str) -> str:
    """Generates a consistent Redis key for daily prayer time data."""
    schema_version = current_app.config.get('CACHE_SCHEMA_VERSION', 'v1')
    return f"daily:{schema_version}:{zone_id}:{date_str}:{composite_method_key}"

def generate_alias_redis_key(source_zone_id: str, composite_method_key: str) -> str:
    """Generates a consistent Redis key for zone alias pointers."""
    # Alias keys don't need schema_version as they point to other calendar keys
    return f"alias:{source_zone_id}:{composite_method_key}"