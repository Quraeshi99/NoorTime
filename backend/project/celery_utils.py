"""
This module sets up and configures the Celery application instance,
ensuring it integrates correctly with the Flask application context.
"""
from celery import Celery

# We create a Celery instance without a specific broker URL here.
# The configuration will be loaded from the Flask app config later.
celery = Celery(__name__)

def init_celery(app):
    """
    Initializes and configures the Celery instance with the Flask app's configuration.
    It also wraps Celery tasks in the Flask application context.

    Args:
        app (Flask): The configured Flask application instance.

    Returns:
        Celery: The configured Celery instance.
    """
    # Update Celery configuration from the Flask app's config.
    # This allows us to manage Celery settings like broker and backend URLs
    # from the same place as our Flask settings (config.py).
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND'],
    )

    # Subclass Celery's Task class to wrap every task execution in a Flask app context.
    # This is crucial because it ensures that tasks have access to Flask's `current_app`,
    # the database session, and other extensions, just like a regular HTTP request.
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    # Replace the default Task class with our context-aware one.
    celery.Task = ContextTask
    return celery
