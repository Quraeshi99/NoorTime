#!/usr/bin/env python
# scripts/cleanup_old_calendars.py

import os
import sys
from datetime import datetime

# This script is intended to be run from the command line.
# It needs access to the main Flask application context.
# We add the project's root directory to the Python path to allow imports.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project import create_app, db
from project.models import PrayerZoneCalendar

def cleanup_old_calendars():
    """
    Deletes expired prayer time calendars from the database.

    This script is the final part of the "Two-Layer Defense" system's
    housekeeping. It is designed to be run via a scheduler (e.g., a cron job)
    once a year, at the beginning of the new year (e.g., on January 3rd),
    as per the user's refined deletion strategy.

    Workflow:
    1. It gets the current year.
    2. It deletes all records from the `PrayerZoneCalendar` table where the `year`
       is less than the current year.
    3. This ensures the database does not get bloated with old, unused data and
       keeps a backup of the previous year until the new year has safely started.
    """
    # Create a Flask app instance to work within its context
    app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    with app.app_context():
        print("--- Starting the Old Calendar Cleanup Script ---")
        
        current_year = datetime.utcnow().year
        print(f"Current year is {current_year}. Deleting all calendars from before this year.")

        try:
            # This is the core deletion query. It finds all rows with a 'year'
            # column less than the current year.
            # The `synchronize_session=False` is an efficiency optimization for bulk deletes.
            num_deleted = db.session.query(PrayerZoneCalendar).filter(
                PrayerZoneCalendar.year < current_year
            ).delete(synchronize_session=False)

            # Commit the transaction to make the deletion permanent
            db.session.commit()

            if num_deleted > 0:
                print(f"SUCCESS: Successfully deleted {num_deleted} old calendar entries.")
            else:
                print("INFO: No old calendar entries found to delete.")

        except Exception as e:
            print(f"ERROR: An error occurred during the deletion process. Rolling back. Details: {e}")
            db.session.rollback()
            
        print("--- Cleanup script finished. ---")

if __name__ == '__main__':
    # This allows the script to be run directly from the command line, e.g., by a cron job.
    cleanup_old_calendars()
