# project/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, FloatField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional

class RegistrationForm(FlaskForm):
    name = StringField('Name (Optional)', validators=[Optional(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters long.")])
    confirm_password = PasswordField('Confirm Password', 
                                     validators=[DataRequired(), EqualTo('password', message="Passwords must match.")])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class FullSettingsForm(FlaskForm):
    """
    A combined form for all user settings, used for validation if needed.
    The actual form is dynamically rendered in the template.
    """
    # User Profile
    name = StringField('Display Name', validators=[Optional(), Length(max=100)])

    # Home Location
    home_city_name = StringField('Home City Name', validators=[Optional(), Length(max=100)])
    home_latitude = FloatField('Home Latitude', validators=[Optional(), NumberRange(min=-90, max=90)])
    home_longitude = FloatField('Home Longitude', validators=[Optional(), NumberRange(min=-180, max=180)])

    # Preferences
    calculation_method = SelectField('Calculation Method', validators=[DataRequired()])
    time_format_preference = SelectField('Time Display Format', 
                                         choices=[('12h', '12-Hour (AM/PM)'), ('24h', '24-Hour')],
                                         validators=[DataRequired()])
    
    adjust_timings_with_api_location = BooleanField('Auto-adjust offsets on location change?')
    auto_update_api_location = BooleanField('Auto-update location periodically?')

    submit = SubmitField('Save All Settings')

    def __init__(self, *args, **kwargs):
        super(FullSettingsForm, self).__init__(*args, **kwargs)
        # Dynamically set choices for calculation_method if they are passed
        if 'calculation_method_choices' in kwargs:
            self.calculation_method.choices = kwargs['calculation_method_choices']
