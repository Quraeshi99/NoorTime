# This module handles fetching yearly prayer calendar data and saving it to the database.
import datetime
from flask import current_app
from project.models import PrayerZoneCalendar
from project import db # Assuming db is initialized in project/__init__.py
from .api_adapter import get_selected_api_adapter
from sqlalchemy.exc import SQLAlchemyError

def get_yearly_calendar_data(zone_id: str, year: int, method_id: int, asr_juristic_id: int, high_latitude_method_id: int, latitude: float, longitude: float, force_refresh: bool) -> Optional[list]:
    """
    Fetches the full yearly prayer calendar from the API and saves/updates it in the database.
    Implements upsert logic: if a record exists, it updates; otherwise, it creates a new one.
    """
    composite_method_key = f"{method_id}-{asr_juristic_id}-{high_latitude_method_id}"
    
    # 1. Fetch from API (always, due to nature of background task or initial fetch)
    adapter = get_selected_api_adapter()
    if not adapter:
        current_app.logger.error("Could not get API adapter for yearly calendar data.")
        return None

    yearly_data = adapter.fetch_yearly_calendar(year, latitude, longitude, method_id, asr_juristic_id, high_latitude_method_id)
    if not yearly_data:
        current_app.logger.error(f"No yearly data fetched from API for zone '{zone_id}', year {year}.")
        return None

    # Calculate SHA-256 hash of the calendar data for efficient comparison
    import hashlib
    import json
    # Ensure consistent JSON serialization for reproducible hash
    calendar_data_str = json.dumps(yearly_data, sort_keys=True, separators=(',', ':'))
    calendar_hash = hashlib.sha256(calendar_data_str.encode('utf-8')).hexdigest()

    # 2. Save/Update to Database (Upsert Logic)
    try:
        # Check if the record already exists
        existing_calendar = PrayerZoneCalendar.query.filter_by(
            zone_id=zone_id,
            year=year,
            calculation_method=composite_method_key
        ).first()

        if existing_calendar:
            existing_calendar.calendar_data = yearly_data
            existing_calendar.calendar_hash = calendar_hash # Save the new hash
            existing_calendar.updated_at = datetime.datetime.utcnow()
            existing_calendar.schema_version = current_app.config['CACHE_SCHEMA_VERSION']
            db.session.merge(existing_calendar) # Use merge for upsert
            current_app.logger.info(f"Updated yearly calendar for zone '{zone_id}', year {year} in DB.")
        else:
            new_calendar = PrayerZoneCalendar(
                zone_id=zone_id,
                year=year,
                calculation_method=composite_method_key,
                calendar_data=yearly_data,
                calendar_hash=calendar_hash, # Save the new hash
                schema_version=current_app.config['CACHE_SCHEMA_VERSION']
            )
            db.session.add(new_calendar)
            current_app.logger.info(f"Added new yearly calendar for zone '{zone_id}', year {year} to DB.")
        
        db.session.commit()
        return yearly_data

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"DB upsert failed for yearly calendar for zone '{zone_id}', year {year}: {e}", exc_info=True)
        return None
