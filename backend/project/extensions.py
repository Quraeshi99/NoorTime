# project/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from redis import from_url

class FlaskRedis:
    """A wrapper class to provide a Flask-like interface for the Redis client."""
    def __init__(self, app=None):
        self.redis_client = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the Redis client from the Flask app configuration."""
        self.redis_client = from_url(app.config.get('REDIS_URL'))

    def __getattr__(self, name):
        """Proxy attribute access to the underlying Redis client."""
        return getattr(self.redis_client, name)

# SQLAlchemy का एक्सटेंशन
db = SQLAlchemy()

# Migrate का एक्सटेंशन (DB migrations के लिए)
migrate = Migrate()

# Limiter का एक्सटेंशन (Rate limiting के लिए)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]  # यह default limit है, जिसे आप __init__.py में override कर सकते हो
)

# Redis Client का एक्सटेंशन
redis_client = FlaskRedis()
