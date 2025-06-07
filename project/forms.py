# project/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, FloatField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional

# Models for validation if needed (e.g., checking if email exists)
# from .models import User 

class RegistrationForm(FlaskForm):
    name = StringField('Name (Optional)', validators=[Optional(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters long.")])
    confirm_password = PasswordField('Confirm Password', 
                                     validators=[DataRequired(), EqualTo('password', message="Passwords must match.")])
    submit = SubmitField('Register')

    # Optional: Custom validator to check if email already exists
    # def validate_email(self, email):
    #     user = User.query.filter_by(email=email.data).first()
    #     if user:
    #         raise ValidationError('That email is already taken. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me') # Optional feature
    submit = SubmitField('Log In')

class LocationSettingsForm(FlaskForm):
    # For user's home/default location
    home_city_name = StringField('Home City Name (e.g., Mumbai)', validators=[Optional(), Length(max=100)])
    home_latitude = FloatField('Home Latitude', validators=[Optional(), NumberRange(min=-90, max=90)])
    home_longitude = FloatField('Home Longitude', validators=[Optional(), NumberRange(min=-180, max=180)])
    # Add a submit button specific to location if needed, or use a global save.
    # submit_location = SubmitField('Save Location Settings')


class PrayerCalculationSettingsForm(FlaskForm):
    # Choices for calculation methods - these keys should map to what AlAdhan API expects or our internal mapping
    # These are examples, actual values should match API documentation or your mapping logic
    calculation_method_choices = [
        ('Karachi', 'University of Islamic Sciences, Karachi (Hanafi Preferred)'),
        ('ISNA', 'Islamic Society of North America (ISNA)'),
        ('MWL', 'Muslim World League'),
        ('Makkah', 'Umm al-Qura University, Makkah'),
        ('Egyptian', 'Egyptian General Authority of Survey'),
        ('Tehran', 'University of Tehran'),
        ('Jafari', 'Shia Ithna-Ashari (Jafari)'),
        # Add other methods as supported by the API and needed by users
        # We need to ensure these map to the "Shafii, Hanafi, Maliki, Hanbali" user display
    ]
    # The user-facing choices will be "Shafii (Standard)", "Hanafi", etc.
    # This form field will store the internal key (like 'Karachi', 'ISNA_HANAFI_ASR')
    # The mapping from user choice (e.g., "Hanafi") to this key will happen in the route/service.
    
    calculation_method = SelectField('Prayer Calculation Method', 
                                     choices=calculation_method_choices, 
                                     validators=[DataRequired()])
    
    time_format_preference = SelectField('Time Display Format', 
                                         choices=[('12h', '12-Hour (AM/PM)'), ('24h', '24-Hour')],
                                         validators=[DataRequired()])
    
    adjust_timings_with_api_location = BooleanField('Auto-adjust Azan/Jamaat offsets if API location changes?')
    auto_update_api_location = BooleanField('Periodically auto-update API location using device GPS (if permission granted)?')
    # submit_calculation = SubmitField('Save Calculation Settings')


# Individual Prayer Time Setting Form (could be part of a larger form or repeated)
class PrayerSpecificSettingsForm(FlaskForm):
    # This is more of a structure; we'll likely handle these fields directly in the HTML/JS
    # and collect them into a JSON to send to the backend, rather than one giant WTForm.
    # However, defining the fields here can be useful for validation logic if we build it that way.
    
    # Example for one prayer (e.g., Fajr) - this would be repeated or dynamically generated
    # For simplicity, we'll manage these in admin_dashboard.html and send as JSON,
    # but this shows how you *could* do it with WTForms.
    
    # mode_choices = [('false', 'Offset from API'), ('true', 'Fixed Time')]
    # fajr_is_fixed_mode = SelectField('Fajr Mode', choices=mode_choices, coerce=lambda x: x == 'true')
    # fajr_fixed_azan = StringField('Fajr Fixed Azan (HH:MM)', validators=[Optional(), Length(5,5)])
    # fajr_fixed_jamaat = StringField('Fajr Fixed Jamaat (HH:MM)', validators=[Optional(), Length(5,5)])
    # fajr_azan_offset = IntegerField('Fajr Azan Offset (mins)', validators=[Optional(), NumberRange(min=-60, max=120)])
    # fajr_jamaat_offset = IntegerField('Fajr Jamaat Offset (mins)', validators=[Optional(), NumberRange(min=0, max=60)])
    
    # We will handle the detailed prayer settings (is_fixed, fixed_time, offset)
    # via direct HTML inputs and JavaScript sending a JSON object to the backend,
    # as this is more flexible for the dynamic UI we have for each prayer.
    # The backend will validate the received JSON data.
    
    submit_all_settings = SubmitField('Save All Prayer Settings')


class FullSettingsForm(FlaskForm):
    """
    A combined form for all user settings.
    This demonstrates one way; alternatively, settings can be grouped or handled by separate forms/API calls.
    """
    # User Profile part (optional, can be separate)
    name = StringField('Display Name (Optional)', validators=[Optional(), Length(max=100)])

    # Home Location
    home_city_name = StringField('Home City Name (e.g., Mumbai)', validators=[Optional(), Length(max=100)])
    home_latitude = FloatField('Home Latitude', validators=[Optional(), NumberRange(min=-90, max=90)])
    home_longitude = FloatField('Home Longitude', validators=[Optional(), NumberRange(min=-180, max=180)])

    # Calculation & Display Preferences
    # User will see "Shafii (Standard)", "Hanafi", "Maliki", "Hanbali" mapped to these values.
    # The mapping logic will be in the backend or JavaScript that populates this.
    # For simplicity, store the "key" that the API adapter understands.
    # For AlAdhan, these are numeric method IDs. Let's use descriptive keys for now.
    calculation_method_user_choices = [
        ('Karachi', "Karachi (Univ. of Islamic Sciences) - Hanafi Asr"), # Method 5 with Hanafi Asr if using old AlAdhan v1 method call
                                                                      # Or Method 3 (Karachi) with asr juristic = 1
        ('ISNA', "ISNA (Islamic Society of North America) - Standard Asr"), # Method 2
        ('MWL', "MWL (Muslim World League) - Standard Asr"), # Method 4
        ('Egyptian', "Egyptian General Authority - Standard Asr"), # Method 5
        ('Makkah', "Makkah (Umm al-Qura) - Standard Asr"), # Method 4 (often similar to MWL)
        ('Custom', "Custom (Set specific angles - Advanced, not implemented yet)") 
        # In settings UI, user will see "Shafii (Standard)", "Hanafi".
        # We will map "Hanafi" choice to a method that uses Hanafi Asr (e.g., Karachi with asr_juristic=1 or a specific Hanafi method ID)
        # And "Shafii (Standard)" to a method for other schools (e.g., ISNA or MWL with asr_juristic=0).
    ]
    calculation_method = SelectField('Calculation Method', 
                                     choices=calculation_method_user_choices, 
                                     validators=[DataRequired()])
    
    time_format_preference = SelectField('Time Display Format', 
                                         choices=[('12h', '12-Hour (AM/PM)'), ('24h', '24-Hour')],
                                         validators=[DataRequired()])
    
    adjust_timings_with_api_location = BooleanField('Auto-adjust my set Azan/Jamaat intervals if current API location changes?', default=True)
    auto_update_api_location = BooleanField('Try to auto-update current API location periodically (requires GPS permission)?', default=False)

    # --- Individual Prayer Settings ---
    # We will collect these via JavaScript from the UI and send as a JSON dictionary
    # So, no explicit WTForms fields here for each of the 5x5 prayer settings.
    # The backend route will expect a dictionary like:
    # prayer_settings_data: {
    #   'fajr': {'is_fixed': true, 'fixed_azan': '05:30', ...},
    #   'dhuhr': {'is_fixed': false, 'azan_offset': 15, ...},
    #   ...
    # }

    submit = SubmitField('Save All Settings')