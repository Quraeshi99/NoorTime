# project/__init__.py
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask_mail import Mail
from .utils.mail_config import get_smtp_config
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from .extensions import limiter, migrate
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# config.py से कॉन्फ़िगरेशन ऑब्जेक्ट इम्पोर्ट करें
# हमें config.py तक पहुँचने के लिए sys.path को एडजस्ट करने की आवश्यकता हो सकती है
# या config.py को भी project पैकेज का हिस्सा बनाना होगा।
# अभी के लिए, हम मान रहे हैं कि run.py सही कॉन्फ़िगरेशन ऑब्जेक्ट पास करेगा।
# from config import config_by_name # यह यहाँ काम नहीं करेगा क्योंकि config.py पैकेज के बाहर है

# एक्सटेंशन ऑब्जेक्ट्स को यहाँ इनिशियलाइज़ करें लेकिन बिना ऐप के
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
cors = CORS() # CORS को यहाँ भी इनिशियलाइज़ किया जा सकता है
mail = Mail()
limiter = Limiter(
    key_func=get_remote_address,
    # default_limits और storage_uri ऐप फैक्ट्री में कॉन्फ़िगर किए जाएंगे
    # strategy="fixed-window" # या ऐप फैक्ट्री में
)

# Flask-Login के लिए कॉन्फ़िगरेशन
login_manager.login_view = 'auth.login' # auth ब्लूप्रिंट में login रूट
login_manager.login_message_category = 'info'
login_manager.login_message = "कृपया इस पृष्ठावर प्रवेश करण्यासाठी लॉग इन करा." # Login message in Marathi or English as per app lang

def create_app(config_name):

    sentry_sdk.init(
        dsn="https://86fa82252c8e7c403361307d500fb84f@o4509459679281152.ingest.us.sentry.io/4509459707789312",  # यहाँ अपना Sentry DSN डालना है
        integrations=[FlaskIntegration()],
        send_default_pii=True,       # User info भेजना हो तो True रखो
        traces_sample_rate=1.0       # Performance tracing के लिए, 0.0 से 1.0 तक, 1.0 मतलब 100%
    )

    app = Flask(__name__,
                instance_relative_config=False,
                static_folder='static',
                template_folder='templates')

    # बाकी का कोड वैसे ही...
def create_app(config_name):
    """
    Flask Application Factory.
    """
    app = Flask(__name__, 
                instance_relative_config=False, # True if config.py is in an 'instance' folder
                static_folder='static',      # project/static
                template_folder='templates') # project/templates

    # config.py से कॉन्फ़िगरेशन लोड करें
    # config.py रूट डायरेक्टरी में है, इसलिए हमें उसे एक्सेस करने का तरीका ढूंढना होगा
    # या config ऑब्जेक्ट को सीधे पास करना होगा, जैसा run.py में किया गया है।
    # create_app फंक्शन को config ऑब्जेक्ट सीधे run.py से मिलेगा।
    if isinstance(config_name, str): # If config_name is a string like 'development'
        from config import config_by_name # Dynamically import if not already done
        app.config.from_object(config_by_name[config_name])
        app.logger.info(f"App configured with: {config_name}")
    else: # If config_name is already a config object
        app.config.from_object(config_name)
        app.logger.info(f"App configured with object: {config_name.__class__.__name__}")


    # सुनिश्चित करें कि SECRET_KEY सेट है
    if not app.config.get('SECRET_KEY'):
        app.logger.error("CRITICAL: SECRET_KEY is not set! Application will not run securely.")
        # raise ValueError("SECRET_KEY must be set in the configuration.")
        # For Replit, it might be set via Secrets, so app.config.get will fetch it.
        # If it's truly missing, the app might fail or be insecure.

    # एक्सटेंशन को ऐप के साथ इनिशियलाइज़ करें
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}}) # API रूट्स के लिए CORS
    # 📬 Mail Config from .env file
    smtp_config = get_smtp_config()

    app.config['MAIL_SERVER'] = smtp_config['server']
    app.config['MAIL_PORT'] = smtp_config['port']
    app.config['MAIL_USE_TLS'] = smtp_config['use_tls']
    app.config['MAIL_USE_SSL'] = not smtp_config['use_tls']
    app.config['MAIL_USERNAME'] = smtp_config['username']
    app.config['MAIL_PASSWORD'] = smtp_config['password']
    app.config['MAIL_DEFAULT_SENDER'] = smtp_config['default_sender']

    mail.init_app(app)
    # Limiter को ऐप कॉन्फ़िगरेशन के साथ इनिशियलाइज़ करें
    limiter.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))


    with app.app_context():
        # ब्लूप्रिंट्स को यहाँ रजिस्टर करें
        from .routes.main_routes import main_bp
        from .routes.auth_routes import auth_bp
        from .routes.api_routes import api_bp
        from .routes.test_mail import test_mail_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp, url_prefix='/auth') # /auth/login, /auth/register
        app.register_blueprint(api_bp, url_prefix='/api')   # /api/initial_data, /api/live_data
        app.register_blueprint(test_mail_bp, url_prefix='/test')  

        app.logger.info("Blueprints registered.")

        # डेटाबेस टेबल्स बनाएँ (यदि वे मौजूद नहीं हैं)
        # db.create_all() # इसे 'flask create-db' कमांड से करना बेहतर है
        
        # लॉगिंग को और कॉन्फ़िगर करें (यदि आवश्यक हो)
        log_level_str = app.config.get('LOG_LEVEL', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        app.logger.setLevel(log_level)
        
        if not app.debug and not app.testing:
            # Production logging (example: to stderr, Replit handles this well)
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(log_level)
            # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            # stream_handler.setFormatter(formatter)
            # app.logger.addHandler(stream_handler) # Flask's default logger already logs to stderr
            pass # Flask's default logger is usually sufficient for Replit console output

        app.logger.info(f"Application initialized with environment: {app.config.get('FLASK_ENV')}, Debug: {app.config.get('DEBUG')}")

        return app
