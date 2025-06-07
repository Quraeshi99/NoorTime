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

# एक्सटेंशन्स को यहाँ declare करें (db, login_manager, csrf, mail, limiter) - ये पहले से project/extensions.py में होंगे

login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
cors = CORS()
limiter = limiter  # पहले से import हुआ है

# Flask-Login की बेसिक सेटिंग्स
login_manager.login_view = 'auth.login'  # auth blueprint के login route पर redirect करता है
login_manager.login_message_category = 'info'
login_manager.login_message = "कृपया इस पृष्ठावर प्रवेश करण्यासाठी लॉग इन करा."  # Marathi message, आप बदल सकते हैं

def create_app(config_name):
    """
    Flask Application Factory function.
    """

    # 1. Sentry SDK initialization - error और performance tracking के लिए
    sentry_sdk.init(
        dsn="https://86fa82252c8e7c403361307d500fb84f@o4509459679281152.ingest.us.sentry.io/4509459707789312",
        integrations=[FlaskIntegration()],
        send_default_pii=True,
        traces_sample_rate=1.0
    )

    # 2. Flask app बनाएं
    app = Flask(__name__,
                instance_relative_config=False,
                static_folder='static',
                template_folder='templates')

    # 3. Config load करें
    if isinstance(config_name, str):
        from config import config_by_name
        app.config.from_object(config_by_name[config_name])
        app.logger.info(f"App configured with: {config_name}")
    else:
        app.config.from_object(config_name)
        app.logger.info(f"App configured with object: {config_name.__class__.__name__}")

    # 4. SECRET_KEY की जांच करें
    if not app.config.get('SECRET_KEY'):
        app.logger.error("CRITICAL: SECRET_KEY is not set! Application will not run securely.")

    # 5. Extensions initialize करें
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # 6. Mail config को .env या config से load करके app में सेट करें
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

    # 7. Rate limiter initialize करें
    limiter.init_app(app)

    # 8. Flask-Login के लिए user loader define करें
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 9. Blueprints को app context में register करें
    with app.app_context():
        from .routes.main_routes import main_bp
        from .routes.auth_routes import auth_bp
        from .routes.api_routes import api_bp
        from .routes.test_mail import test_mail_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(test_mail_bp, url_prefix='/test')

        # 10. Logging सेट करें
        log_level_str = app.config.get('LOG_LEVEL', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        app.logger.setLevel(log_level)

        if not app.debug and not app.testing:
            # Production में extra handlers लगाना हो तो यहाँ करें
            pass

        app.logger.info(f"Application initialized with environment: {app.config.get('FLASK_ENV')}, Debug: {app.config.get('DEBUG')}")

    # 11. अंत में app return करें
    return app
