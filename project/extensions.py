# project/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# SQLAlchemy का एक्सटेंशन
db = SQLAlchemy()

# Migrate का एक्सटेंशन (DB migrations के लिए)
migrate = Migrate()

# Limiter का एक्सटेंशन (Rate limiting के लिए)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]  # यह default limit है, जिसे आप __init__.py में override कर सकते हो
)
