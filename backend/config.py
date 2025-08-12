import os
from dotenv import load_dotenv

# Load .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print("Warning: .env file not found. Using defaults or environment variables.")

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_default_fallback_secret_key_for_development_only'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True # Enabled by default, can be disabled in testing
    LOG_LEVEL = "INFO"

    # Supabase config - needed for JWT validation
    SUPABASE_URL = os.environ.get('SUPABASE_URL')

    # Sentry Configuration
    SENTRY_DSN = os.environ.get('SENTRY_DSN')

    # Prayer Time API Configuration
    PRAYER_API_ADAPTER = os.environ.get('PRAYER_API_ADAPTER') or "AlAdhanAdapter"
    PRAYER_API_BASE_URL = os.environ.get('PRAYER_API_BASE_URL') or "http://api.aladhan.com/v1"
    PRAYER_API_KEY = os.environ.get('PRAYER_API_KEY')

    # Geocoding API Configuration
    OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')

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
    if not Config.SECRET_KEY or Config.SECRET_KEY == 'a_default_fallback_secret_key_for_development_only':
        raise ValueError("CRITICAL: SECRET_KEY not found in environment!")
    
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("CRITICAL: DATABASE_URL for production is not set!")

    if not Config.SUPABASE_URL:
        raise ValueError("CRITICAL: SUPABASE_URL for production is not set!")

    if not Config.SENTRY_DSN:
        print("Warning: SENTRY_DSN not found. Error tracking will be disabled.")

    if not Config.OPENWEATHERMAP_API_KEY:
        raise ValueError("CRITICAL: OPENWEATHERMAP_API_KEY not found in environment. Geocoding will fail.")

class TestingConfig(Config):
    TESTING = True
    # Use a separate PostgreSQL database for testing, defined by TEST_DATABASE_URL
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL')
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False # Disable rate limiting for tests

    # Ensure the test database URL is set, otherwise fail fast
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("CRITICAL: TEST_DATABASE_URL is not set. Testing cannot proceed.")

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}




