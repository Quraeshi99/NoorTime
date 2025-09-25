# project/routes/masjid_routes.py

from flask import request, g, current_app
from flask_smorest import Blueprint, abort
from webargs import fields

from ..services import masjid_service
from ..models import User
from ..schemas import MasjidSearchQuerySchema, MasjidSchema, MessageSchema, AnnouncementSchema, AnnouncementPostSchema
from ..utils.auth import jwt_required, has_permission

masjid_bp = Blueprint(
    'Masjids', 
    __name__, 
    url_prefix='/api/masjids', 
    description="Operations for finding, following, and interacting with Masjids."
)

@masjid_bp.route('/')
@masjid_bp.arguments(MasjidSearchQuerySchema, location='query')
@masjid_bp.response(200, MasjidSchema(many=True), description="List of Masjids found.")
@masjid_bp.response(404, MessageSchema, description="No Masjid found for the given code.")
def search_masjids(args):
    """
    Search for Masjids.

    You can search by a unique Masjid code, or by location (latitude/longitude).
    Providing a code will return a single result. Providing location will return nearby Masjids.
    """
    code = args.get('code')
    lat = args.get('lat')
    lon = args.get('lon')

    if code:
        masjid = User.query.filter_by(role='Masjid', masjid_code=code).first()
        if not masjid:
            abort(404, message=f"No Masjid found with code '{code}'.")
        return [masjid]
    
    if lat is not None and lon is not None:
        radius = args.get('radius', 50) # Default radius of 50km
        nearby_masjids = masjid_service.get_masjids_by_location(lat, lon, radius)
        return nearby_masjids

    # If no parameters, maybe return a featured list or abort
    # For now, we'll return an empty list if no search params are given
    return []

@masjid_bp.route('/<int:masjid_id>/follow', methods=['POST'])
@jwt_required
@masjid_bp.response(200, MessageSchema, description="Successfully followed the Masjid.")
@masjid_bp.response(404, MessageSchema, description="Masjid not found.")
@masjid_bp.response(409, MessageSchema, description="User is already following this Masjid.")
@masjid_bp.doc(security=[{"Bearer": []}])
def follow(masjid_id):
    """Follow a Masjid."""
    user = g.user
    masjid_to_follow = User.query.filter_by(id=masjid_id, role='Masjid').first()

    if not masjid_to_follow:
        abort(404, message="Masjid not found.")

    result = masjid_service.follow_masjid(user, masjid_to_follow)
    if result['status'] == 'already_following':
        abort(409, message=result['message'])
    
    return {"message": result['message']}

@masjid_bp.route('/<int:masjid_id>/unfollow', methods=['POST'])
@jwt_required
@masjid_bp.response(200, MessageSchema, description="Successfully unfollowed the Masjid.")
@masjid_bp.response(404, MessageSchema, description="Masjid or follow relationship not found.")
@masjid_bp.doc(security=[{"Bearer": []}])
def unfollow(masjid_id):
    """Unfollow a Masjid."""
    user = g.user
    masjid_to_unfollow = User.query.filter_by(id=masjid_id, role='Masjid').first()

    if not masjid_to_unfollow:
        abort(404, message="Masjid not found.")

    result = masjid_service.unfollow_masjid(user, masjid_to_unfollow)
    if result['status'] == 'not_following':
        abort(404, message=result['message'])

    return {"message": result['message']}

@masjid_bp.route('/followed/default/<int:masjid_id>', methods=['PUT'])
@jwt_required
@masjid_bp.response(200, MessageSchema, description="Default Masjid updated successfully.")
@masjid_bp.response(404, MessageSchema, description="You are not following this Masjid.")
@masjid_bp.doc(security=[{"Bearer": []}])
def set_default(masjid_id):
    """Set a followed Masjid as the default for prayer times and announcements."""
    user = g.user
    masjid_to_set_default = User.query.get(masjid_id)

    result = masjid_service.set_default_masjid(user, masjid_to_set_default)
    if result['status'] == 'not_following':
        abort(404, message=result['message'])
    
    return {"message": result['message']}

@masjid_bp.route('/followed', methods=['GET'])
@jwt_required
@masjid_bp.response(200, MasjidSchema(many=True), description="A list of Masjids the user follows.")
@masjid_bp.doc(security=[{"Bearer": []}])
def get_followed_masjids():
    """Get the list of Masjids the current user is following."""
    user = g.user
    return user.followed_masjids

@masjid_bp.route('/<int:masjid_id>/announcements', methods=['GET'])
@masjid_bp.response(200, AnnouncementSchema(many=True), description="List of announcements for the Masjid.")
@masjid_bp.response(404, MessageSchema, description="Masjid not found.")
def get_announcements(masjid_id):
    """Get all announcements for a specific Masjid."""
    masjid = User.query.filter_by(id=masjid_id, role='Masjid').first()
    if not masjid:
        abort(404, message="Masjid not found.")
    return masjid.announcements

@masjid_bp.route('/<int:masjid_id>/announcements', methods=['POST'])
@jwt_required
@has_permission('can_create_announcements') # Assumes this permission is tied to the Masjid role
@masjid_bp.arguments(AnnouncementPostSchema)
@masjid_bp.response(21, AnnouncementSchema, description="Announcement created successfully.")
@masjid_bp.response(403, MessageSchema, description="User does not have permission to post for this Masjid.")
@masjid_bp.response(404, MessageSchema, description="Masjid not found.")
@masjid_bp.doc(security=[{"Bearer": []}])
def create_announcement(data, masjid_id):
    """Create a new announcement for a Masjid. User must be the Masjid admin."""
    user = g.user
    masjid = User.query.filter_by(id=masjid_id, role='Masjid').first()

    if not masjid:
        abort(404, message="Masjid not found.")
    
    # Security check: Ensure the logged-in user *is* the Masjid account they are trying to post for.
    if user.id != masjid.id:
        abort(403, message="You do not have permission to post announcements for this Masjid.")

    new_announcement = masjid_service.create_announcement(masjid, data['title'], data['content'])
    return new_announcement
