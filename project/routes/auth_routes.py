# project/routes/auth_routes.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from .. import db, limiter  # Import from project/__init__.py
from ..models import User, UserSettings
from ..forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("60 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        email_exists = User.query.filter_by(email=form.email.data.lower()).first()
        if email_exists:
            flash('This email address is already registered. Please log in.', 'danger')
            return redirect(url_for('auth.register'))

        new_user = User(
            email=form.email.data.lower(),
            name=form.name.data or None
        )
        new_user.set_password(form.password.data)

        # Set default location and method from config
        try:
            new_user.default_latitude = float(current_app.config.get('DEFAULT_LATITUDE'))
            new_user.default_longitude = float(current_app.config.get('DEFAULT_LONGITUDE'))
            new_user.default_calculation_method = current_app.config.get('DEFAULT_CALCULATION_METHOD')
            new_user.time_format_preference = '12h'
        except (ValueError, TypeError):
            current_app.logger.error("Default lat/long from config are not valid. Using hardcoded fallbacks.")
            new_user.default_latitude = 19.2183
            new_user.default_longitude = 72.8493
            new_user.default_calculation_method = 'Karachi'

        db.session.add(new_user)
        db.session.flush() # Use flush to get the new_user.id before committing

        # Create default settings for the new user
        new_user_settings = UserSettings(user_id=new_user.id)
        db.session.add(new_user_settings)

        try:
            db.session.commit()
            current_app.logger.info(f"New user registered: {new_user.email}")
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error during registration for {form.email.data}: {e}", exc_info=True)
            flash('An error occurred during registration. Please try again.', 'danger')

    return render_template('register.html', title='Register', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("60 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            current_app.logger.info(f"User '{user.email}' logged in successfully.")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.settings'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html', title='Log In', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    current_app.logger.info(f"User '{current_user.email}' logging out.")
    logout_user()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('main.index'))