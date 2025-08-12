# project/models.py

from datetime import datetime
from flask_login import UserMixin
from . import db # Import the db object defined in project/__init__.py

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    # Add a field to store the Supabase User ID, which is a UUID.
    supabase_user_id = db.Column(db.String(36), unique=True, nullable=True, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True) # Optional user name
    
    # Role-Based Access Control (RBAC)
    # Replaces the old is_admin boolean for more flexibility.
    # Possible values: 'Super Admin', 'Manager', 'Client'
    role = db.Column(db.String(20), nullable=False, default='Client')
    
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

    # Relationships for Permission Management System
    user_permissions = db.relationship('UserPermission', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User {self.email} - {self.role}>'

class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)

    # Setting to adjust fixed/offset prayer times if API location changes
    adjust_timings_with_api_location = db.Column(db.Boolean, default=True)
    
    # Auto-update API location periodically (if geolocation permission is granted)
    auto_update_api_location = db.Column(db.Boolean, default=False)

    # Threshold for prayer time updates (in minutes)
    threshold_minutes = db.Column(db.Integer, default=5) # Default to 5 minutes
    # Stores the last API time that caused an update for each prayer
    # This will be a JSON string or similar to store multiple prayer times
    last_api_times_for_threshold = db.Column(db.Text, nullable=True)

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

class AppSettings(db.Model):
    __tablename__ = 'app_settings'
    id = db.Column(db.Integer, primary_key=True)
    # General settings
    default_latitude = db.Column(db.Float, nullable=True)
    default_longitude = db.Column(db.Float, nullable=True)
    default_calculation_method = db.Column(db.String(50), nullable=True)
    
    # API Keys (can be managed from admin)
    sentry_dsn = db.Column(db.String(255), nullable=True)
    openweathermap_api_key = db.Column(db.String(255), nullable=True)

    # Feature flags
    is_new_feature_enabled = db.Column(db.Boolean, default=False)
    
    # Content settings
    welcome_message = db.Column(db.String(500), default="Welcome to NoorTime!")

    def __repr__(self):
        return f'<AppSettings id={self.id}>'

class Popup(db.Model):
    __tablename__ = 'popup'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Popup {self.name}>'

# --- Permission Management System Models ---

class Permission(db.Model):
    __tablename__ = 'permission'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False) # e.g., 'can_view_users'
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Permission {self.name}>'

class UserPermission(db.Model):
    __tablename__ = 'user_permission'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'), primary_key=True)
    has_permission = db.Column(db.Boolean, default=True, nullable=False) # True for grant, False for revoke

    user = db.relationship('User', backref=db.backref('user_permissions_link', lazy=True, cascade="all, delete-orphan"))
    permission = db.relationship('Permission', backref=db.backref('user_permissions_link', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<UserPermission User:{self.user_id} Perm:{self.permission_id} Has:{self.has_permission}>'

class RolePermission(db.Model):
    __tablename__ = 'role_permission'
    role_name = db.Column(db.String(20), primary_key=True) # e.g., 'Manager', 'Super Admin'
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'), primary_key=True)

    permission = db.relationship('Permission', backref=db.backref('role_permissions_link', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<RolePermission Role:{self.role_name} Perm:{self.permission_id}>'
