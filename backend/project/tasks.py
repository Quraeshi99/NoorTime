"""
This module contains all the Celery tasks for the NoorTime application.
These tasks run in the background and handle long-running or periodic jobs.
"""
from .celery_utils import celery
from flask import current_app

# To avoid circular imports, we will import the service function inside the task.
# This is a common pattern in larger Flask applications.

@celery.task(name='tasks.fetch_and_cache_yearly_calendar')
def fetch_and_cache_yearly_calendar_task(zone_id, year, method_id, asr_juristic_id, high_latitude_method_id, latitude, longitude):
    """
    Celery task to fetch a yearly prayer calendar from an external API
    and cache it in the database. This is a background job.
    """
    current_app.logger.info(f"[CELERY TASK] Starting background fetch for zone '{zone_id}', year {year}.")
    try:
        # We import the service function here to avoid circular dependencies
        # between services and tasks.
        from .services.prayer_time_service import _get_yearly_calendar_data

        # We call the existing service function which contains the full logic 
        # to fetch from API and save to the database. 
        # force_refresh=True ensures it always hits the external API.
        _get_yearly_calendar_data(
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
        return result_message
    except Exception as e:
        # Log any exceptions that occur within the task
        error_message = f"Background fetch failed for zone '{zone_id}', year {year}: {e}"
        current_app.logger.error(f"[CELERY TASK] {error_message}", exc_info=True)
        # Reraise the exception to mark the task as failed, which can be useful for retries.
        raise