import os
from dotenv import load_dotenv
load_dotenv()

# .env फाइल लोड करें
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print("Warning: .env file not found. Using defaults or Replit Secrets.")

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_default_fallback_secret_key_for_development_only'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    LOG_LEVEL = "INFO"  # Always keep as string

    PRAYER_API_ADAPTER = os.environ.get('PRAYER_API_ADAPTER') or "AlAdhanAdapter"
    PRAYER_API_BASE_URL = os.environ.get('PRAYER_API_BASE_URL') or "http://api.aladhan.com/v1"
    PRAYER_API_KEY = os.environ.get('PRAYER_API_KEY')

    OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')

    DEFAULT_LATITUDE = os.environ.get('DEFAULT_LATITUDE') or "19.2183"
    DEFAULT_LONGITUDE = os.environ.get('DEFAULT_LONGITUDE') or "72.8493"
    DEFAULT_CALCULATION_METHOD = os.environ.get('DEFAULT_CALCULATION_METHOD') or "Karachi"

class DevelopmentConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or 'sqlite:///database.db'
    LOG_LEVEL = "DEBUG"  # Fixed: Now string

class ProductionConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False

    if not Config.SECRET_KEY or Config.SECRET_KEY == 'a_default_fallback_secret_key_for_development_only':
        raise ValueError("SECRET_KEY not found in environment!")

    if not Config.OPENWEATHERMAP_API_KEY:
        print("Warning: OPENWEATHERMAP_API_KEY not set. Geocoding may fail.")

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_secret_key():
    key = os.environ.get('SECRET_KEY')
    if not key:
        print("WARNING: SECRET_KEY not found. Using insecure fallback key.")
        return 'this-is-a-super-insecure-default-key-for-dev-only'
    return key

Config.SECRET_KEY = get_secret_key()
