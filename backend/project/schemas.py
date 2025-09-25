# project/schemas.py

from marshmallow import Schema, fields

class PrayerTimeSchema(Schema):
    azan = fields.Str(required=True)
    jamaat = fields.Str(required=True)

class PrayerTimesSchema(Schema):
    fajr = fields.Nested(PrayerTimeSchema, required=True)
    dhuhr = fields.Nested(PrayerTimeSchema, required=True)
    asr = fields.Nested(PrayerTimeSchema, required=True)
    maghrib = fields.Nested(PrayerTimeSchema, required=True)
    isha = fields.Nested(PrayerTimeSchema, required=True)
    jummah = fields.Nested(PrayerTimeSchema, required=True)
    chasht = fields.Nested(PrayerTimeSchema, required=True)

class DateInfoSchema(Schema):
    gregorian = fields.Str(required=True)
    hijri = fields.Str(required=True)

class NextDayPrayerDisplaySchema(Schema):
    name = fields.Str(required=True)
    azan = fields.Str(required=True)
    jamaat = fields.Str(required=True)

class UserPreferencesSchema(Schema):
    timeFormat = fields.Str(required=True)
    calculationMethod = fields.Str(required=True)
    homeLatitude = fields.Float(required=True)
    homeLongitude = fields.Float(required=True)

class MasjidSearchQuerySchema(Schema):
    """Schema for validating search query parameters for masjids."""
    code = fields.Str()
    lat = fields.Float()
    lon = fields.Float()
    radius = fields.Int()

class MasjidSchema(Schema):
    """Schema for serializing Masjid data."""
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    masjid_code = fields.Str(dump_only=True)
    default_city_name = fields.Str(dump_only=True, attribute="default_city_name")
    default_latitude = fields.Float(dump_only=True, attribute="default_latitude")
    default_longitude = fields.Float(dump_only=True, attribute="default_longitude")

class AnnouncementPostSchema(Schema):
    """Schema for validating the payload for creating a new announcement."""
    title = fields.Str(required=True)
    content = fields.Str(required=True)

class AnnouncementSchema(AnnouncementPostSchema):
    """Schema for serializing announcement data."""
    id = fields.Int(dump_only=True)
    masjid_id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

class InitialPrayerDataSchema(Schema):
    currentLocationName = fields.Str(required=True)
    currentPrayerPeriod = fields.Dict(required=True)
    prayerTimes = fields.Nested(PrayerTimesSchema, required=True)
    dateInfo = fields.Nested(DateInfoSchema, required=True)
    nextDayPrayerDisplay = fields.Nested(NextDayPrayerDisplaySchema, required=True)
    userPreferences = fields.Nested(UserPreferencesSchema, required=True)
    isUserAuthenticated = fields.Bool(required=True)
    
    # New fields for community feature
    is_following_default_masjid = fields.Bool(required=True)
    default_masjid_info = fields.Nested(MasjidSchema, required=False)
    announcements = fields.List(fields.Nested(AnnouncementSchema), required=False)

class MessageSchema(Schema):
    message = fields.Str(required=True)

class MasjidApplicationSchema(Schema):
    """Schema for submitting and validating a new Masjid application."""
    official_name = fields.Str(required=True)
    address_line_1 = fields.Str(required=True)
    city = fields.Str(required=True)
    state = fields.Str(required=True)
    postal_code = fields.Str(required=True)
    country = fields.Str(required=True)
    latitude = fields.Float(required=True)
    longitude = fields.Float(required=True)
    website_url = fields.URL(required=False, allow_none=True)
    has_official_document = fields.Bool(required=True)
    document_url = fields.URL(required=False, allow_none=True)
    exterior_photo_url = fields.URL(required=True)
    interior_photo_url = fields.URL(required=True)

class MasjidApplicationAdminSchema(MasjidApplicationSchema):
    """More detailed schema for admins viewing applications."""
    id = fields.Int(dump_only=True)
    status = fields.Str(dump_only=True)
    trust_score = fields.Int(dump_only=True)
    verification_details = fields.Dict(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    
    # Include applicant's info
    applicant = fields.Nested(lambda: UserSchema, dump_only=True)

class ApplicationActionSchema(Schema):
    """Schema for actions on an application, like rejection."""
    reason = fields.Str(required=True)

class UserSchema(Schema):
    """Basic user schema for nesting in other schemas."""
    id = fields.Int(dump_only=True)
    email = fields.Email(dump_only=True)
    name = fields.Str(dump_only=True)
    role = fields.Str(dump_only=True)

class GeocodeSchema(Schema):
    city = fields.Str(required=True)

class AutocompleteSchema(Schema):
    query = fields.Str(required=True)

class InitialPrayerDataArgsSchema(Schema):
    lat = fields.Float()
    lon = fields.Float()
    method = fields.Str()
    city = fields.Str()