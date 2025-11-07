"""
This module contains all the Celery tasks for the NoorTime application.
These tasks run in the background and handle long-running or periodic jobs.
"""
from .celery_utils import celery
from flask import current_app
from project.metrics import BACKGROUND_TASK_RUNS_TOTAL, BACKGROUND_TASK_DURATION_SECONDS

# To avoid circular imports, we will import the service function inside the task.
# This is a common pattern in larger Flask applications.

@celery.task(name='tasks.fetch_and_cache_yearly_calendar')
def fetch_and_cache_yearly_calendar_task(zone_id, year, method_id, asr_juristic_id, high_latitude_method_id, latitude, longitude):
    """
    Celery task to fetch a yearly prayer calendar from an external API
    and cache it in the database. This is a background job.
    """
    with BACKGROUND_TASK_DURATION_SECONDS.labels(task_name='fetch_and_cache_yearly_calendar').time():
        current_app.logger.info(f"[CELERY TASK] Starting background fetch for zone '{zone_id}', year {year}.")
        try:
            from .services.prayer_time.data_processor import get_yearly_calendar_data

            get_yearly_calendar_data(
                zone_id=zone_id,
                year=year,
                method_id=method_id,
                asr_juristic_id=asr_juristic_id,
                high_latitude_method_id=high_latitude_method_id,
                latitude=latitude,
                longitude=longitude,
                force_refresh=True
            )
            result_message = f"Successfully cached calendar for {zone_id} - {year}."
            current_app.logger.info(f"[CELERY TASK] {result_message}")
            BACKGROUND_TASK_RUNS_TOTAL.labels(task_name='fetch_and_cache_yearly_calendar', status='success').inc()
            return result_message
        except Exception as e:
            error_message = f"Background fetch failed for zone '{zone_id}', year {year}: {e}"
            current_app.logger.error(f"[CELERY TASK] {error_message}", exc_info=True)
            BACKGROUND_TASK_RUNS_TOTAL.labels(task_name='fetch_and_cache_yearly_calendar', status='failure').inc()
            raise

# --- Scalable Schedule Generation Tasks (Rolling Wave) ---

@celery.task(name='tasks.generate_schedule_for_single_user')
def generate_schedule_for_single_user(user_id, year, month):
    """
    Atomic Celery task to generate and cache the monthly schedule for a single user.
    This task is dispatched by the master_schedule_generator.
    
    Args:
        user_id (int): The ID of the user for whom to generate the schedule.
        year (int): The year of the schedule.
        month (int): The month of the schedule.
    """
    with BACKGROUND_TASK_DURATION_SECONDS.labels(task_name='generate_schedule_for_single_user').time():
        current_app.logger.info(f"[CELERY TASK] Starting schedule generation for User ID: {user_id} for {year}-{month}.")
        try:
            # Import service here to avoid circular dependencies
            from .services.schedule_service import get_or_generate_monthly_schedule

            # The service function handles all logic: caching, generation, and saving.
            # We call it with force_regenerate=True to ensure it runs the generation logic.
            get_or_generate_monthly_schedule(
                user_id=user_id,
                year=year,
                month=month,
                force_regenerate=True
            )
            result_message = f"Successfully generated schedule for User ID: {user_id} for {year}-{month}."
            current_app.logger.info(f"[CELERY TASK] {result_message}")
            BACKGROUND_TASK_RUNS_TOTAL.labels(task_name='generate_schedule_for_single_user', status='success').inc()
            return result_message
        except Exception as e:
            error_message = f"Schedule generation failed for User ID: {user_id} for {year}-{month}: {e}"
            current_app.logger.error(f"[CELERY TASK] {error_message}", exc_info=True)
            BACKGROUND_TASK_RUNS_TOTAL.labels(task_name='generate_schedule_for_single_user', status='failure').inc()
            # We don't re-raise the exception to prevent the master task from failing if one sub-task fails.
            return error_message # Return error message for logging

@celery.task(name='tasks.master_schedule_generator')
def master_schedule_generator():
    """
    This is the master Celery Beat task that runs daily.
    It implements the "Rolling Wave Generation" by assigning each day a subset of users
    for whom to proactively generate the *next* month's schedule.
    This distributes the server load evenly throughout the month.
    """
    from .models import User, MonthlyScheduleCache
    from . import db
    import datetime

    current_app.logger.info("[CELERY BEAT] Master Schedule Generator starting.")

    # --- Determine Target Date and Users ---
    # Get the configuration for generation days
    generation_days = current_app.config.get('SCHEDULE_GENERATION_DAYS', 28)

    # Determine which day's "bucket" of users to process.
    # We use day-1 so on the 1st of the month, we get mod 0; on 28th, we get mod 27.
    day_of_month_for_mod = datetime.datetime.utcnow().day
    modulo_value = (day_of_month_for_mod - 1) % generation_days

    # Calculate the year and month for which we need to generate schedules (i.e., next month)
    today = datetime.date.today()
    first_day_of_current_month = today.replace(day=1)
    first_day_of_next_month = first_day_of_current_month + datetime.timedelta(days=32)
    year_to_generate = first_day_of_next_month.year
    month_to_generate = first_day_of_next_month.month

    current_app.logger.info(f"Processing bucket {modulo_value} for {year_to_generate}-{month_to_generate}.")

    # --- Query for Target Users ---
    # Find all users who belong to today's modulo bucket.
    # We also LEFT JOIN the MonthlyScheduleCache to find users who *don't* have a schedule
    # for the target month yet, to avoid redundant work.
    # Note: This query can be further optimized for very large datasets.
    
    # Subquery to find owner_ids that already have a schedule for the target month
    subquery = db.session.query(MonthlyScheduleCache.owner_id).filter(
        MonthlyScheduleCache.year == year_to_generate,
        MonthlyScheduleCache.month == month_to_generate
    ).subquery()

    # Main query to find users in the bucket who are not in the subquery
    # We use the modulo operator directly in the query for DB-level filtering.
    target_users = db.session.query(User).filter(
        (User.id % generation_days) == modulo_value,
        User.id.notin_(db.session.query(subquery))
    ).all()

    if not target_users:
        current_app.logger.info("No users found in this bucket needing a schedule. Task complete.")
        return "No users found in this bucket."

    current_app.logger.info(f"Found {len(target_users)} users in bucket {modulo_value} to process.")

    # --- Dispatch Atomic Tasks ---
    # For each target user, dispatch a small, individual task to the queue.
    # This allows for massive parallel processing by Celery workers.
    for user in target_users:
        generate_schedule_for_single_user.delay(user.id, year_to_generate, month_to_generate)
    
        success_message = f"Dispatched schedule generation tasks for {len(target_users)} users."
    
        current_app.logger.info(f"[CELERY BEAT] {success_message}")
    
        return success_message
    
    
    
    
    
    # --- Proactive Yearly Calendar Fetching (Zone-Based Rolling Wave) ---
    
    
    
    @celery.task(name='tasks.proactive_yearly_calendar_fetcher')
    
    def proactive_yearly_calendar_fetcher():
    
        """
    
        This is the master Celery Beat task for the 'Zone-Based Rolling Wave'.
    
        It runs daily and proactively fetches the *next year's* raw prayer time calendars
    
        from the external API. The load is distributed evenly across the entire year by
    
        assigning each zone to a specific day of the year based on its hash.
    
        """
    
        from .models import PrayerZoneCalendar
    
        from . import db
    
        import datetime
    
        import hashlib
    
    
    
        current_app.logger.info("[CELERY BEAT] Proactive Yearly Calendar Fetcher starting.")
    
    
    
        # --- Determine Target Date and Modulo ---
    
        now = datetime.datetime.utcnow()
    
        year_to_fetch = now.year + 1
    
        
    
        # Use day of the year (1-366 for leap years) for the modulo calculation
    
        day_of_year = now.timetuple().tm_yday
    
        days_in_year = 366 if (now.year % 4 == 0 and now.year % 100 != 0) or (now.year % 400 == 0) else 365
    
        modulo_value = day_of_year % days_in_year
    
    
    
        current_app.logger.info(f"Processing zone bucket {modulo_value} for year {year_to_fetch}.")
    
    
    
        # --- Query for All Unique Zones ---
    
        # We get all distinct combinations of zone_id and calculation_method.
    
        # This represents every unique calendar type we have in our system.
    
        all_zones = db.session.query(
    
            PrayerZoneCalendar.zone_id, 
    
            PrayerZoneCalendar.calculation_method
    
        ).distinct().all()
    
    
    
        if not all_zones:
    
            current_app.logger.info("No existing zones found in PrayerZoneCalendar table. Task complete.")
    
            return "No zones found to process."
    
    
    
        # --- Filter Zones for Today's Bucket and Dispatch Tasks ---
    
        zones_to_process_count = 0
    
        for zone_id, calculation_method in all_zones:
    
            # Create a consistent hash for the zone identifier
    
            # Use a combination of zone_id and method to ensure uniqueness
    
            unique_zone_key = f"{zone_id}-{calculation_method}"
    
            
    
            # Use hashlib for a stable integer hash
    
            hash_int = int(hashlib.sha256(unique_zone_key.encode('utf-8')).hexdigest(), 16)
    
    
    
            if (hash_int % days_in_year) == modulo_value:
    
                # This zone belongs to today's bucket.
    
                # Check if the calendar for next year already exists.
    
                calendar_exists = db.session.query(PrayerZoneCalendar.zone_id).filter(
    
                    PrayerZoneCalendar.zone_id == zone_id,
    
                    PrayerZoneCalendar.calculation_method == calculation_method,
    
                    PrayerZoneCalendar.year == year_to_fetch
    
                ).first()
    
    
    
                if not calendar_exists:
    
                    current_app.logger.info(f"Zone '{unique_zone_key}' is in today's bucket. Triggering fetch for {year_to_fetch}.")
    
                    
    
                    # We need lat/lon and method details to trigger the fetch task.
    
                    # We can get this from any existing calendar for that zone.
    
                    # This assumes that lat/lon for a zone_id is constant.
    
                    existing_calendar = db.session.query(PrayerZoneCalendar).filter(
    
                        PrayerZoneCalendar.zone_id == zone_id,
    
                        PrayerZoneCalendar.calculation_method == calculation_method
    
                    ).first()
    
    
    
                    if existing_calendar and existing_calendar.calendar_data:
    
                        try:
    
                            # Extract required info from the existing calendar data
    
                            # This is a bit fragile; depends on the structure of calendar_data
    
                            first_day_data = existing_calendar.calendar_data[0]
    
                            meta = first_day_data.get('meta', {})
    
                            latitude = meta.get('latitude')
    
                            longitude = meta.get('longitude')
    
                            
    
                            method_id, asr_juristic_id, high_latitude_method_id = map(int, calculation_method.split('-'))
    
    
    
                            if latitude is not None and longitude is not None:
    
                                fetch_and_cache_yearly_calendar_task.delay(
    
                                    zone_id=zone_id,
    
                                    year=year_to_fetch,
    
                                    method_id=method_id,
    
                                    asr_juristic_id=asr_juristic_id,
    
                                    high_latitude_method_id=high_latitude_method_id,
    
                                    latitude=latitude,
    
                                    longitude=longitude
    
                                )
    
                                zones_to_process_count += 1
    
                            else:
    
                                current_app.logger.warning(f"Could not find lat/lon in existing calendar for zone '{unique_zone_key}'.")
    
    
    
                        except (ValueError, IndexError, KeyError) as e:
    
                            current_app.logger.error(f"Error processing existing calendar for zone '{unique_zone_key}': {e}")
    
                    else:
    
                        current_app.logger.warning(f"Could not find an existing calendar with data for zone '{unique_zone_key}' to get lat/lon.")
    
                else:
    
                    current_app.logger.debug(f"Calendar for zone '{unique_zone_key}' for year {year_to_fetch} already exists. Skipping.")
    
    
    
        success_message = f"Dispatched calendar fetch tasks for {zones_to_process_count} zones."
    
        current_app.logger.info(f"[CELERY BEAT] {success_message}")
    
        return success_message
    
    