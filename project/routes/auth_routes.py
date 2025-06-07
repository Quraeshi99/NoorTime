# project/routes/auth_routes.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash  # For registration if not using model method

from .. import db, limiter  # project/__init__.py से इम्पोर्ट
from ..models import User, UserSettings
from ..forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)  # url_prefix='/auth' app फैक्ट्री में सेट होगा

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour")  # प्रति घंटे 5 रजिस्ट्रेशन प्रयास की सीमा
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))  # या main.settings

    form = RegistrationForm()
    if form.validate_on_submit():
        email_exists = User.query.filter_by(email=form.email.data.lower()).first()
        if email_exists:
            current_app.logger.warning(f"Registration attempt with existing email: {form.email.data.lower()}")
            flash('हा ईमेल पत्ता आधीच नोंदणीकृत आहे. कृपया वेगळा ईमेल वापरा किंवा लॉग इन करा.', 'danger')  # Marathi
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(
            email=form.email.data.lower(),
            password_hash=hashed_password,
            name=form.name.data if form.name.data else None
        )
        db.session.add(new_user)
        db.session.commit()  # Commit here to get new_user.id

        # Create default settings for the new user
        new_user_settings = UserSettings(user_id=new_user.id)  # Will use defaults from model

        # Set default location and method from config for new user (can be changed in settings)
        try:
            new_user.default_latitude = float(current_app.config.get('DEFAULT_LATITUDE', 19.2183))
            new_user.default_longitude = float(current_app.config.get('DEFAULT_LONGITUDE', 72.8493))
            new_user.default_calculation_method = current_app.config.get('DEFAULT_CALCULATION_METHOD', 'Karachi')  # Ensure this key matches choices
            new_user.time_format_preference = '12h'  # Default
            new_user_settings.adjust_timings_with_api_location = True
            new_user_settings.auto_update_api_location = False

        except ValueError:
            current_app.logger.error("Default lat/long from config are not valid floats. Using hardcoded fallbacks.")
            new_user.default_latitude = 19.2183
            new_user.default_longitude = 72.8493
            new_user.default_calculation_method = 'Karachi'

        db.session.add(new_user_settings)  # Add settings linked to new_user

        try:
            db.session.commit()
            current_app.logger.info(f"New user registered: {new_user.email}")
            flash('तुमची नोंदणी यशस्वी झाली! आता तुम्ही लॉग इन करू शकता.', 'success')  # Marathi
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error during registration for {form.email.data}: {e}", exc_info=True)
            flash('नोंदणीदरम्यान एक त्रुटी आली. कृपया पुन्हा प्रयत्न करा.', 'danger')  # Marathi

    elif request.method == 'POST':  # Form validation failed
        current_app.logger.warning(f"Registration form validation failed for email: {form.email.data}")
        # Errors will be displayed by form fields in template

    return render_template('register.html', title='नोंदणी करा', form=form)  # Register in Marathi


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")  # प्रति मिनट 10 लॉगिन प्रयास की सीमा
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))  # या main.settings

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            current_app.logger.info(f"User '{user.email}' logged in successfully.")
            flash('तुम्ही यशस्वीरित्या लॉग इन केले आहे!', 'success')  # Marathi

            # Redirect to the page user was trying to access, or to settings/index
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.settings'))
        else:
            current_app.logger.warning(f"Failed login attempt for email: '{form.email.data}'.")
            flash('अवैध ईमेल किंवा पासवर्ड.', 'danger')  # Marathi

    elif request.method == 'POST':  # Form validation failed
        current_app.logger.warning(f"Login form validation failed for email: {form.email.data}")

    return render_template('login.html', title='लॉग इन', form=form)  # Log In in Marathi


@auth_bp.route('/logout')
@login_required  # Only logged-in users can logout
def logout():
    current_app.logger.info(f"User '{current_user.email}' logging out.")
    logout_user()
    flash('तुम्ही यशस्वीरित्या लॉग आउट झाला आहात.', 'info')  # Marathi
    return redirect(url_for('main.index'))  # Redirect to home page after logout
