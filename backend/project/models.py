# project/models.py

from datetime import datetime
from flask_login import UserMixin
from . import db # Import the db object defined in project/__init__.py

# --- Community & Masjid Models ---

class MasjidApplication(db.Model):
    """Stores applications from users wanting to register their organization as a Masjid."""
    __tablename__ = 'masjid_application'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # --- Application Data ---
    official_name = db.Column(db.String(200), nullable=False)
    address_line_1 = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    
    # Pin-pointed location from the user
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    
    website_url = db.Column(db.String(255), nullable=True)
    has_official_document = db.Column(db.Boolean, default=False)
    document_url = db.Column(db.String(255), nullable=True) # Link to Supabase Storage
    exterior_photo_url = db.Column(db.String(255), nullable=False)
    interior_photo_url = db.Column(db.String(255), nullable=False)

    # --- Verification & Status ---
    # Possible values: 'pending', 'approved', 'rejected', 'needs_manual_review', 'needs_community_verification'
    status = db.Column(db.String(50), default='pending', nullable=False, index=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    trust_score = db.Column(db.Integer, default=0)
    
    # Stores a JSON object with results of automated checks
    # e.g., {"address_verified": true, "image_is_internal_duplicate": false}
    verification_details = db.Column(db.JSON, nullable=True)
    
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # --- Relationships ---
    applicant = db.relationship('User', foreign_keys=[user_id], backref=db.backref('masjid_applications', lazy=True))
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])

    def __repr__(self):
        return f'<MasjidApplication ID:{self.id} Name:{self.official_name} Status:{self.status}>'

class ImageFingerprint(db.Model):
    """Stores perceptual hashes of masjid images to prevent internal duplicates."""
    __tablename__ = 'image_fingerprint'

    id = db.Column(db.Integer, primary_key=True)
    
    # Can be linked to a user (if approved) or an application (if pending)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    application_id = db.Column(db.Integer, db.ForeignKey('masjid_application.id'), nullable=True, index=True)
    
    image_url = db.Column(db.String(255), nullable=False)
    # e.g., 'exterior', 'interior'
    image_type = db.Column(db.String(20), nullable=False)
    
    # The perceptual hash (fingerprint) of the image
    phash = db.Column(db.String(16), nullable=False, index=True) # 64-bit hash is 16 hex chars

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<ImageFingerprint ID:{self.id} pHash:{self.phash}>'

class ApplicationAuditLog(db.Model):
    """Tracks all status changes and actions on a MasjidApplication for accountability."""
    __tablename__ = 'application_audit_log'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('masjid_application.id'), nullable=False, index=True)
    
    # The user who performed the action (e.g., an admin)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # e.g., 'status_change', 'forced_approval', 'rejection_reason_updated'
    action = db.Column(db.String(50), nullable=False)
    
    details = db.Column(db.Text, nullable=True) # e.g., "Status changed from 'pending' to 'approved'"
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # --- Relationships ---
    application = db.relationship('MasjidApplication', backref=db.backref('audit_logs', lazy=True, cascade="all, delete-orphan"))
    actor = db.relationship('User')

    def __repr__(self):
        return f'<ApplicationAuditLog ID:{self.id} AppID:{self.application_id} Action:{self.action}>'


class UserMasjidFollow(db.Model):
    """Association table for the many-to-many relationship between users and masjids they follow."""
    __tablename__ = 'user_masjid_follow'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    masjid_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    
    # This flag determines which followed masjid's settings are currently active for the user.
    is_default = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships to easily access the user and masjid objects from the association
    user = db.relationship('User', foreign_keys=[user_id], back_populates='followed_masjids_association')
    masjid = db.relationship('User', foreign_keys=[masjid_id], back_populates='followers_association')

    def __repr__(self):
        return f'<UserMasjidFollow User:{self.user_id} follows Masjid:{self.masjid_id} Default:{self.is_default}>'

class MasjidAnnouncement(db.Model):
    """Stores announcements created by a Masjid account."""
    __tablename__ = 'masjid_announcement'
    id = db.Column(db.Integer, primary_key=True)
    masjid_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to get the Masjid that made the announcement
    masjid = db.relationship('User', backref=db.backref('announcements', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<MasjidAnnouncement ID:{self.id} Title:{self.title}>'


class GuestProfile(db.Model):
    """Stores information about a guest user, identified by their device ID."""
    __tablename__ = 'guest_profile'

    # A UUID generated by the client device, used to identify the guest.
    device_id = db.Column(db.String(36), primary_key=True)

    # The masjid the guest is currently following.
    followed_masjid_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)

    # Timestamps for tracking.
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # --- Relationships ---
    # Relationship to the User model (where the user is a Masjid).
    followed_masjid = db.relationship('User', foreign_keys=[followed_masjid_id])

    def __repr__(self):
        return f'<GuestProfile Device:{self.device_id} follows Masjid:{self.followed_masjid_id}>'


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    supabase_user_id = db.Column(db.String(36), unique=True, nullable=True, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    
    # Role-Based Access Control (RBAC)
    # Possible values: 'Super Admin', 'Manager', 'Client', 'Masjid'
    role = db.Column(db.String(20), nullable=False, default='Client')
    
    # --- New fields for Masjid functionality ---
    # Unique, shareable code for users with the 'Masjid' role.
    masjid_code = db.Column(db.String(12), unique=True, nullable=True, index=True)
    
    # --- User's personal settings (used if not following a default masjid) ---
    default_latitude = db.Column(db.Float, nullable=True)
    default_longitude = db.Column(db.Float, nullable=True)
    default_city_name = db.Column(db.String(100), nullable=True)
    default_calculation_method = db.Column(db.String(50), nullable=True) 
    time_format_preference = db.Column(db.String(10), default='12h')
    last_seen_at = db.Column(db.DateTime, nullable=True, index=True)

    # --- Relationships ---
    # One-to-one relationship to the user's personal prayer time settings.
    settings = db.relationship('UserSettings', backref='user', uselist=False, cascade="all, delete-orphan")

    # Relationships for Permission Management System
    user_permissions = db.relationship('UserPermission', back_populates='user', lazy=True, cascade="all, delete-orphan")

    # Many-to-many relationships for following masjids
    followed_masjids_association = db.relationship('UserMasjidFollow', foreign_keys=[UserMasjidFollow.user_id], back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    followers_association = db.relationship('UserMasjidFollow', foreign_keys=[UserMasjidFollow.masjid_id], back_populates='masjid', lazy='dynamic', cascade="all, delete-orphan")

    @property
    def followed_masjids(self):
        """Returns a list of Masjid objects the user is following."""
        return [association.masjid for association in self.followed_masjids_association]

    @property
    def default_masjid_follow(self):
        """Returns the UserMasjidFollow association object for the default masjid, or None."""
        return self.followed_masjids_association.filter_by(is_default=True).first()

    def has_permission(self, permission_name):
        # Check direct user permissions
        for up in self.user_permissions:
            if up.permission.name == permission_name and up.has_permission:
                return True
            elif up.permission.name == permission_name and not up.has_permission:
                return False # Explicitly revoked

        # Check role-based permissions
        role_permissions = RolePermission.query.filter_by(role_name=self.role).all()
        for rp in role_permissions:
            if rp.permission.name == permission_name:
                return True
        return False

    def __repr__(self):
        return f'<User {self.email} - {self.role}>'


class UserDevice(db.Model):
    """Stores device tokens for sending push notifications to users."""
    __tablename__ = 'user_device'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # The FCM device token provided by the client app.
    device_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    
    # Type of the device (e.g., 'android', 'ios', 'web')
    device_type = db.Column(db.String(20), nullable=False, default='android')
    
    # Timestamps for tracking when the token was added or last updated.
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # --- Relationships ---
    user = db.relationship('User', backref=db.backref('devices', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<UserDevice ID:{self.id} UserID:{self.user_id}>'


class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)

    # Setting to adjust fixed/offset prayer times if API location changes
    adjust_timings_with_api_location = db.Column(db.Boolean, default=True)
    
    # Auto-update API location periodically (if geolocation permission is granted)
    auto_update_api_location = db.Column(db.Boolean, default=False)

    # Threshold for prayer time updates (in minutes)
    threshold_minutes = db.Column(db.Integer, default=5)
    # Stores the last API time that caused an update for each prayer
    last_api_times_for_threshold = db.Column(db.Text, nullable=True)

    # --- Fiqh & High Latitude Settings ---
    # Defines the Asr calculation method. 'Standard' for Jumhoor, 'Hanafi' for Hanafi school.
    asr_juristic = db.Column(db.String(20), default='Standard', nullable=False)
    # Defines the adjustment method for locations at high latitudes.
    high_latitude_method = db.Column(db.String(50), default='MiddleOfTheNight', nullable=False)

    # --- Prayer specific settings ---
    fajr_is_fixed = db.Column(db.Boolean, default=False)
    fajr_fixed_azan = db.Column(db.String(5), default="05:30")
    fajr_fixed_jamaat = db.Column(db.String(5), default="05:45")
    fajr_azan_offset = db.Column(db.Integer, default=10)
    fajr_jamaat_offset = db.Column(db.Integer, default=15)

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
    maghrib_azan_offset = db.Column(db.Integer, default=0)
    maghrib_jamaat_offset = db.Column(db.Integer, default=5) 

    isha_is_fixed = db.Column(db.Boolean, default=False)
    isha_fixed_azan = db.Column(db.String(5), default="20:15")
    isha_fixed_jamaat = db.Column(db.String(5), default="20:30")
    isha_azan_offset = db.Column(db.Integer, default=45) 
    isha_jamaat_offset = db.Column(db.Integer, default=15)

    # Jummah specific settings
    jummah_is_fixed = db.Column(db.Boolean, default=True) # Default to fixed for backward compatibility
    jummah_azan_time = db.Column(db.String(5), default="01:15")
    jummah_khutbah_start_time = db.Column(db.String(5), default="01:30")
    jummah_jamaat_time = db.Column(db.String(5), default="01:45")
    jummah_azan_offset = db.Column(db.Integer, default=15) # Offset from Dhuhr raw time
    jummah_khutbah_offset = db.Column(db.Integer, default=15) # Offset from calculated Jummah Azan time
    jummah_jamaat_offset = db.Column(db.Integer, default=15) # Offset from calculated Jummah Azan time

    # Hijri date adjustment for user's display
    hijri_offset = db.Column(db.Integer, default=0)

    # IANA timezone string (e.g., 'Asia/Kolkata', 'America/New_York')
    timezone = db.Column(db.String(100), default='UTC', nullable=False)

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

# Add default permissions if they don't exist
@event.listens_for(db.Mapper, 'after_configured')
def receive_after_configured():
    if not db.session.query(Permission).filter_by(name='can_view_system_health').first():
        db.session.add(Permission(name='can_view_system_health', description='Can view system health dashboard'))
        db.session.commit()

class UserPermission(db.Model):
    __tablename__ = 'user_permission'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'), primary_key=True)
    has_permission = db.Column(db.Boolean, default=True, nullable=False) # True for grant, False for revoke

    user = db.relationship('User', back_populates='user_permissions')
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

class PrayerZoneCalendar(db.Model):
    """
    Stores a full year's prayer time calendar for a specific geographic zone and calculation method.
    This is the core of the caching system. It is designed to be highly efficient by
    storing pre-calculated yearly calendars, avoiding repeated API calls.
    """
    __tablename__ = 'prayer_zone_calendar'

    # --- Composite Primary Key ---
    # The primary key is a combination of the zone, the year, and the calculation method.
    # This ensures that for any given zone and year, we can store multiple calendars
    # based on the user's preferred calculation method (e.g., Karachi, ISNA, etc.).
    __table_args__ = (db.UniqueConstraint('zone_id', 'year', 'calculation_method', name='uq_zone_year_method'),)

    # The human-readable, unique identifier for the geographic zone.
    # Examples: 'IN_UP_BADAUN' (for an Admin Level 2 zone)
    #           'IN_UP_BADAUN_BISAULI' (for an Admin Level 3 sub-zone)
    #           'grid_28.6_77.2' (as a fallback for remote areas)
    zone_id = db.Column(db.String(255), primary_key=True)

    # The year for which the prayer time calendar is valid (e.g., 2025).
    year = db.Column(db.Integer, primary_key=True)

    # The key for the calculation method used to generate this calendar (e.g., 'Karachi', 'ISNA').
    # This allows storing different prayer times for the same zone based on fiqh/school of thought.
    calculation_method = db.Column(db.String(50), primary_key=True)

    # A SHA-256 hash of the calendar_data JSON string. This acts as a 'digital fingerprint'
    # to allow for extremely fast, 100% accurate comparisons of calendars without
    # loading the full data into memory.
    calendar_hash = db.Column(db.String(64), nullable=True, index=True)

    # Version of the schema used for the calendar_data JSON. Used for cache invalidation.
    schema_version = db.Column(db.String(10), nullable=False, default='v1')

    # --- Calendar Data ---
    # Stores the entire year's data (365 days) as a single JSON object.
    # This is highly efficient for reads, as we only do one lookup per year per zone per method.
    # Using db.JSON is optimal for databases that support it (like PostgreSQL/Supabase).
    calendar_data = db.Column(db.JSON, nullable=False)

    # --- Metadata ---
    # Timestamps for tracking when the record was created and last updated.
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<PrayerZoneCalendar Zone:{self.zone_id} Year:{self.year} Method:{self.calculation_method}>'

class GeocodingCache(db.Model):
    """
    Caches geocoding results to prevent repeated API calls for the same city.
    """
    __tablename__ = 'geocoding_cache'

    # The city name is the primary key, normalized to lowercase to avoid duplicates.
    city_name = db.Column(db.String(255), primary_key=True)
    
    # The geographic coordinates for the city.
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    
    # Full country name for context, e.g., "India"
    country = db.Column(db.String(100), nullable=True)

    # Metadata for tracking when the record was created.
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<GeocodingCache {self.city_name} -> ({self.latitude}, {self.longitude})>'


class MonthlyScheduleCache(db.Model):
    """
    Caches the final, generated monthly "Director's Script" for a user or a Masjid.

    This is the ultimate cache layer that stores the pre-calculated, state-based
    schedule that is sent to the client. This prevents re-calculating the complex
    script on every request and enables the "Don't Recalculate, Re-use" strategy
    for Masjid followers.
    """
    __tablename__ = 'monthly_schedule_cache'

    id = db.Column(db.Integer, primary_key=True)

    # The owner of this schedule. This is a foreign key to the User table.
    # If it's an individual user's schedule, it's their user.id.
    # If it's a Masjid's schedule, it's the Masjid's own user.id.
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    # The year and month for which this schedule is valid.
    year = db.Column(db.Integer, nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False, index=True)

    # A version number that gets incremented every time the schedule is regenerated
    # due to a settings change. This helps clients know if they need to re-sync.
    version = db.Column(db.Integer, nullable=False, default=1)

    # The full JSON "Director's Script" for the month.
    # Using db.Text for broad compatibility, but db.JSON is preferred for PostgreSQL.
    schedule_script = db.Column(db.Text, nullable=False)

    # A SHA-256 hash of the schedule_script. This allows for extremely fast
    # comparison to check if a newly generated script is different from the stored one.
    script_hash = db.Column(db.String(64), nullable=False, index=True)

    # Timestamps for tracking.
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # --- Relationships ---
    owner = db.relationship('User', backref=db.backref('monthly_schedules', lazy='dynamic', cascade="all, delete-orphan"))

    # --- Constraints ---
    __table_args__ = (db.UniqueConstraint('owner_id', 'year', 'month', name='uq_owner_year_month'),)

    def __repr__(self):
        return f'<MonthlyScheduleCache Owner:{self.owner_id} For:{self.year}-{self.month} v{self.version}>'

