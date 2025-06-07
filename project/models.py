# project/models.py

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db # project/__init__.py में परिभाषित db ऑब्जेक्ट को इम्पोर्ट करें

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=True) # Optional user name
    
    # Default location and calculation method for the user
    default_latitude = db.Column(db.Float, nullable=True)
    default_longitude = db.Column(db.Float, nullable=True)
    default_city_name = db.Column(db.String(100), nullable=True) # For display
    # Calculation method will store a key like "Hanafi", "ISNA", "Karachi" etc.
    default_calculation_method = db.Column(db.String(50), nullable=True) 
    time_format_preference = db.Column(db.String(10), default='12h') # '12h' or '24h'

    # Relationship to UserSettings
    # 'uselist=False' makes it a one-to-one relationship from User to UserSettings
    settings = db.relationship('UserSettings', backref='user', uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)

    # Setting to adjust fixed/offset prayer times if API location changes
    adjust_timings_with_api_location = db.Column(db.Boolean, default=True)
    
    # Auto-update API location periodically (if geolocation permission is granted)
    auto_update_api_location = db.Column(db.Boolean, default=False)

    # --- Prayer specific settings ---
    # We will create fields for each prayer (Fajr, Dhuhr, Asr, Maghrib, Isha, Jummah)
    # Each will have: _is_fixed, _fixed_azan, _fixed_jamaat, _azan_offset, _jamaat_offset

    # Example for Fajr (repeat this pattern for Dhuhr, Asr, Maghrib, Isha)
    fajr_is_fixed = db.Column(db.Boolean, default=False)
    fajr_fixed_azan = db.Column(db.String(5), default="05:30") # HH:MM
    fajr_fixed_jamaat = db.Column(db.String(5), default="05:45")
    fajr_azan_offset = db.Column(db.Integer, default=10) # Mins from API Fajr start
    fajr_jamaat_offset = db.Column(db.Integer, default=15) # Mins from calculated Fajr Azan

    dhuhr_is_fixed = db.Column(db.Boolean, default=True) 
    dhuhr_fixed_azan = db.Column(db.String(5), default="01:30")
    dhuhr_fixed_jamaat = db.Column(db.String(5), default="01:45")
    dhuhr_azan_offset = db.Column(db.Integer, default=15) 
    dhuhr_jamaat_offset = db.Column(db.Integer, default=15)

    asr_is_fixed = db.Column(db.Boolean, default=False)
    asr_fixed_azan = db.Column(db.String(5), default="05:00")
    asr_fixed_jamaat = db.Column(db.String(5), default="05:20")
    asr_azan_offset = db.Column(db.Integer, default=20) 
    asr_jamaat_offset = db.Column(db.Integer, default=20)

    maghrib_is_fixed = db.Column(db.Boolean, default=False) 
    maghrib_fixed_azan = db.Column(db.String(5), default="18:50") 
    maghrib_fixed_jamaat = db.Column(db.String(5), default="18:55") 
    maghrib_azan_offset = db.Column(db.Integer, default=0) # At API Maghrib/Sunset
    maghrib_jamaat_offset = db.Column(db.Integer, default=5) 

    isha_is_fixed = db.Column(db.Boolean, default=False)
    isha_fixed_azan = db.Column(db.String(5), default="20:15")
    isha_fixed_jamaat = db.Column(db.String(5), default="20:30")
    isha_azan_offset = db.Column(db.Integer, default=45) 
    isha_jamaat_offset = db.Column(db.Integer, default=15)

    # Jummah specific settings (usually fixed, but can have offsets if needed, though simpler as fixed)
    # We also need Khutbah time for Jummah
    jummah_azan_time = db.Column(db.String(5), default="01:15") # Fixed Azan
    jummah_khutbah_start_time = db.Column(db.String(5), default="01:30") # Fixed Khutbah start
    jummah_jamaat_time = db.Column(db.String(5), default="01:45") # Fixed Jama'at

    def __repr__(self):
        return f'<UserSettings for User ID {self.user_id}>'

# You can add more models here if needed in the future
# For example, a model to store user's bookmarked locations if the app supports multiple locations.