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