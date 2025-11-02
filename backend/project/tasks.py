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