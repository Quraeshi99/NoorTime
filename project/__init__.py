import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask_mail import Mail
from .utils.mail_config import get_smtp_config
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from .extensions import limiter, migrate, db
import logging
from flask import Flask
from flask_cors import CORS
from flask_limiter.util import get_remote_address

# Declare extensions here (db, login_manager, csrf, mail, limiter) - these should already be in project/extensions.py

login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
cors = CORS()


# Basic Flask-Login settings
login_manager.login_view = 'auth.login'  # Redirects to auth blueprint's login route
login_manager.login_message_category = 'info'
login_manager.login_message = "Please log in to access this page."  # Marathi message, you can change it

def create_app(config_name):
    """
    Flask Application Factory function.
    """
    app = Flask(__name__,
                instance_relative_config=False,
                static_folder='static',
                template_folder='templates')

    # 3. Load Config
    from config import config_by_name
    config_obj = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(config_obj)
    app.logger.info(f"App configured with: {config_obj.__class__.__name__}")

    # Add this line to print the database URI
    app.logger.info(f"SQLALCHEMY_DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")

    # 1. Sentry SDK initialization - for error and performance tracking
    if app.config.get('SENTRY_DSN'):
        sentry_sdk.init(
            dsn=app.config['SENTRY_DSN'],
            integrations=[FlaskIntegration()],
            send_default_pii=True,
            traces_sample_rate=1.0
        )
        app.logger.info("Sentry initialized for error tracking.")

    # 4. Check SECRET_KEY
    if not app.config.get('SECRET_KEY'):
        app.logger.error("CRITICAL: SECRET_KEY is not set! Application will not run securely.")

    # 5. Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # 6. Set Mail config in app by loading from .env or config
    smtp_config = get_smtp_config()
    app.config.update({
        'MAIL_SERVER': smtp_config['server'],
        'MAIL_PORT': smtp_config['port'],
        'MAIL_USE_TLS': smtp_config['use_tls'],
        'MAIL_USE_SSL': not smtp_config['use_tls'],
        'MAIL_USERNAME': smtp_config['username'],
        'MAIL_PASSWORD': smtp_config['password'],
        'MAIL_DEFAULT_SENDER': smtp_config['default_sender'],
    })
    mail.init_app(app)

    # 7. Initialize Rate Limiter
    limiter.init_app(app)

    # 8. Define user loader for Flask-Login
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        app.logger.info(f"DEBUG: Attempting to load user with ID: {user_id}")
        user = User.query.get(int(user_id))
        if user:
            app.logger.info(f"DEBUG: User loaded: {user.email}")
        else:
            app.logger.info(f"DEBUG: User with ID {user_id} not found.")
        return user

    # 9. Register Blueprints in app context
    with app.app_context():
        from .routes.main_routes import main_bp
        from .routes.auth_routes import auth_bp
        from .routes.api_routes import api_bp
        from .routes.test_mail import test_mail_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(test_mail_bp, url_prefix='/test')

        # 10. Set up Logging
        log_level_str = app.config.get('LOG_LEVEL', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        app.logger.setLevel(log_level)

        if not app.debug and not app.testing:
            # Add extra handlers in Production here if needed
            pass

        app.logger.info(f"Application initialized with environment: {app.config.get('FLASK_ENV')}, Debug: {app.config.get('DEBUG')}")

    # 11. Finally, return the app
    return app