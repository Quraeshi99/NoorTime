#!/usr/bin/env python
# scripts/precache_next_year.py

import os
import sys
import time
import random
from datetime import datetime

# This script is intended to be run from the command line.
# It needs access to the main Flask application context.
# We add the project's root directory to the Python path to allow imports.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project import create_app, db
from project.models import PrayerZoneCalendar
from project.services.prayer_time_service import _get_yearly_calendar_data, _get_zone_center_coords

def precache_next_year_calendars():
    """
    Proactively fetches and caches prayer time calendars for the upcoming year.

    This script is the primary component of the "Two-Layer Defense" system.
    It is designed to be run via a scheduler (e.g., a cron job) during the
    last quarter of the year (e.g., October, November, December) to prevent
    a "Thundering Herd" problem on January 1st.

    Workflow:
    1. It gets a list of all unique zones (zone_id, calculation_method)
       that have been used in the current year.
    2. For each unique zone, it checks if a calendar for the *next* year
       already exists in the database.
    3. If the calendar does not exist, it fetches the data from the prayer
       time API and saves it to the database.
    4. A random sleep interval is added between API calls to avoid
       overwhelming the external API service (to be a good API citizen).
    """
    # Create a Flask app instance to work within its context
    app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    with app.app_context():
        print("--- Starting the Pre-caching Script for Next Year's Calendars ---")
        
        now = datetime.utcnow()
        current_year = now.year
        next_year = current_year + 1

        # This script is designed to run towards the end of the year.
        # This check can be removed if you want to run it at any time.
        if now.month < 10:
            print(f"INFO: Script run on {now.strftime('%Y-%m-%d')}. It's not the last quarter of the year. This is usually run in Oct-Dec. Exiting.")
            return

        print(f"INFO: Running for current year: {current_year}. Pre-caching for: {next_year}.")

        # 1. Get all unique zone/method combinations for the current year.
        try:
            zones_to_precache = db.session.query(
                PrayerZoneCalendar.zone_id,
                PrayerZoneCalendar.calculation_method
            ).filter(PrayerZoneCalendar.year == current_year).distinct().all()
        except Exception as e:
            print(f"ERROR: Could not query existing zones from the database. Aborting. Details: {e}")
            return
            
        if not zones_to_precache:
            print("INFO: No existing zones found for the current year. Nothing to precache. Exiting.")
            return

        print(f"INFO: Found {len(zones_to_precache)} unique zone/method combinations to check for pre-caching.")

        # --- Loop through each zone and process ---
        for i, (zone_id, method) in enumerate(zones_to_precache):
            print(f"\n--- Processing {i+1}/{len(zones_to_precache)}: Zone='{zone_id}', Method='{method}' ---")

            # 2. Check if the calendar for next year already exists.
            try:
                exists = PrayerZoneCalendar.query.filter_by(
                    zone_id=zone_id,
                    year=next_year,
                    calculation_method=method
                ).first()
            except Exception as e:
                print(f"  ERROR: Could not query for next year's calendar. Skipping. Details: {e}")
                continue

            if exists:
                print(f"  STATUS: SKIPPING. Calendar for {next_year} already exists in the database.")
                continue

            # 3. If it doesn't exist, fetch and cache it.
            print(f"  STATUS: PENDING. Calendar for {next_year} not found. Attempting to fetch from API...")
            
            # --- Get Latitude/Longitude for the API call ---
            # This is a critical step. The service function needs coordinates to fetch data.
            # Since we only have the zone_id, we need a way to get the coordinates back.
            # TODO: The best long-term solution is a dedicated `Zones` table that stores
            # the canonical lat/lon for each zone_id. The current implementation is a workaround.
            
            latitude, longitude = None, None
            if zone_id.startswith('grid_'):
                # For grid-based zones, we can calculate the center coordinates.
                latitude, longitude = _get_zone_center_coords(zone_id)
            else:
                # For admin-based zones, this is harder. We are making a pragmatic choice
                # to use the application's default coordinates as a fallback for the fetch.
                # This works because the prayer times within a large zone don't change drastically.
                latitude = app.config.get('DEFAULT_LATITUDE')
                longitude = app.config.get('DEFAULT_LONGITUDE')
                print(f"  WARN: Could not determine exact lat/lon for admin zone '{zone_id}'. Using default coordinates for API call.")

            if not latitude or not longitude:
                print(f"  ERROR: Could not determine latitude/longitude for zone '{zone_id}'. Skipping.")
                continue

            # 4. Call the service function to fetch and cache the data.
            try:
                _get_yearly_calendar_data(
                    zone_id=zone_id,
                    year=next_year,
                    calculation_method_key=method,
                    latitude=float(latitude),
                    longitude=float(longitude),
                    force_refresh=True # We always force a fresh fetch from the API
                )
                print(f"  SUCCESS: Successfully fetched and cached calendar for {next_year}.")
            except Exception as e:
                print(f"  ERROR: The fetch and cache process failed for zone '{zone_id}'. Details: {e}")

            # 5. Sleep for a random interval to be a good API citizen.
            sleep_time = random.uniform(1, 3) # Sleep for 1 to 3 seconds
            print(f"  INFO: Sleeping for {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
            
        print("\n--- Pre-caching script finished. ---")

if __name__ == '__main__':
    # This allows the script to be run directly from the command line.
    precache_next_year_calendars()
