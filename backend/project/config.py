import os
from dotenv import load_dotenv

# Load .env file
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print("Warning: .env file not found. Using defaults or environment variables.")

class Config:
    """Base configuration."""
    SECRET_KEY = 'a_very_long_and_random_secret_key_for_noortime_project'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True # Enabled by default, can be disabled in testing
    LOG_LEVEL = "INFO"

    # Supabase config - needed for JWT validation
    SUPABASE_URL = os.environ.get('SUPABASE_URL')

    # Sentry Configuration
    SENTRY_DSN = os.environ.get('SENTRY_DSN')

    # Redis and Caching Configuration
    # Used for Celery broker, result backend, and general application caching.
    # It's highly recommended to set this from an environment variable in production.
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'

    # Celery Configuration
    # The broker URL tells Celery where to send messages (the "Message Box").
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or REDIS_URL
    # The result backend URL tells Celery where to store the results of tasks.
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or REDIS_URL

    # Prayer Time API Configuration
    PRAYER_API_ADAPTER = os.environ.get('PRAYER_API_ADAPTER') or "AlAdhanAdapter"
    PRAYER_API_BASE_URL = os.environ.get('PRAYER_API_BASE_URL') or "http://api.aladhan.com/v1"
    PRAYER_API_KEY = os.environ.get('PRAYER_API_KEY')
    PRAYER_ZONE_GRID_SIZE = float(os.environ.get("PRAYER_ZONE_GRID_SIZE", 0.2))

    # Geocoding API Configuration
    GEOCODING_PROVIDER = os.environ.get('GEOCODING_PROVIDER', 'LocationIQ') # Can be 'LocationIQ' or 'OpenWeatherMap'
    OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')
    LOCATIONIQ_API_KEY = os.environ.get('LOCATIONIQ_API_KEY')

    # Push Notification Configuration (FCM)
    FCM_SERVER_KEY = os.environ.get('FCM_SERVER_KEY')

    # Yearly Cache Management Configuration
    # Defines the start date for the "grace period" during which next year's calendars are pre-fetched.
    CACHE_GRACE_PERIOD_START_MONTH = int(os.environ.get('CACHE_GRACE_PERIOD_START_MONTH', 12)) # December
    CACHE_GRACE_PERIOD_START_DAY = int(os.environ.get('CACHE_GRACE_PERIOD_START_DAY', 15))

    # Defines the date when the cleanup script for old calendars should run.
    CACHE_CLEANUP_MONTH = int(os.environ.get('CACHE_CLEANUP_MONTH', 1)) # January
    CACHE_CLEANUP_DAY = int(os.environ.get('CACHE_CLEANUP_DAY', 3))

    # Default Location and Calculation Method
    DEFAULT_LATITUDE = os.environ.get('DEFAULT_LATITUDE', "19.2183")
    DEFAULT_LONGITUDE = os.environ.get('DEFAULT_LONGITUDE', "72.8493")
    DEFAULT_CALCULATION_METHOD = os.environ.get('DEFAULT_CALCULATION_METHOD', "Karachi")

    # Calculation Method Choices for Forms/Templates
    CALCULATION_METHOD_CHOICES = [
        {'key': 'Karachi', 'name': "Karachi (Univ. of Islamic Sci.)"},
        {'key': 'ISNA', 'name': "ISNA (N. America) - Standard Asr"},
        {'key': 'MWL', 'name': "Muslim World League - Standard Asr"},
        {'key': 'Egyptian', 'name': "Egyptian General Authority - Standard Asr"},
        {'key': 'Makkah', 'name': "Makkah (Umm al-Qura) - Standard Asr"},
        {'key': 'Tehran', 'name': "Tehran (Univ. of Tehran Geophysics)"},
        {'key': 'Jafari', 'name': "Shia Ithna-Ashari (Jafari)"},
    ]

class DevelopmentConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    LOG_LEVEL = "DEBUG"

class ProductionConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') # Explicitly set for production

    # Ensure critical secrets are set in production
    # if not Config.SECRET_KEY or Config.SECRET_KEY == 'a_default_fallback_secret_key_for_development_only':
    #     raise ValueError("CRITICAL: SECRET_KEY not found in environment!")
    # 
    # if not SQLALCHEMY_DATABASE_URI:
    #     raise ValueError("CRITICAL: DATABASE_URL for production is not set!")

    # if not Config.SUPABASE_URL:
    #     raise ValueError("CRITICAL: SUPABASE_URL for production is not set!")

    # if not Config.SENTRY_DSN:
    #     print("Warning: SENTRY_DSN not found. Error tracking will be disabled.")

    # if not Config.OPENWEATHERMAP_API_KEY:
    #     raise ValueError("CRITICAL: OPENWEATHERMAP_API_KEY not found in environment. Geocoding will fail.")

class TestingConfig(Config):
    TESTING = True
    # Use an in-memory SQLite database for tests to ensure speed and isolation.
    # This avoids network issues and dependency on external databases.
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False # Disable rate limiting for tests
    SECRET_KEY = 'test-secret-key'

config_by_name = {
    'development': DevelopmentConfig,
    #        'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}




