
import string
import random
from .. import db
from ..models import User, UserMasjidFollow, MasjidAnnouncement
from .notification_service import send_announcement_to_masjid_followers

def generate_unique_masjid_code(size=8):
    """Generates a unique, random alphanumeric code for a Masjid."""
    # Generate a random code
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choice(chars) for _ in range(size))
        # Check if the code already exists
        if not User.query.filter_by(masjid_code=code).first():
            return code

def follow_masjid(user, masjid_to_follow):
    """Makes a user follow a masjid."""
    # Check if the user is already following this masjid
    if user.followed_masjids_association.filter_by(masjid_id=masjid_to_follow.id).first():
        return {"status": "already_following", "message": "You are already following this Masjid."}

    # Create the follow relationship
    new_follow = UserMasjidFollow(user_id=user.id, masjid_id=masjid_to_follow.id)
    
    # If this is the first masjid the user is following, set it as default
    if user.followed_masjids_association.count() == 0:
        new_follow.is_default = True

    db.session.add(new_follow)
    db.session.commit()
    return {"status": "success", "message": "Successfully followed the Masjid."}

def unfollow_masjid(user, masjid_to_unfollow):
    """Makes a user unfollow a masjid."""
    follow_association = user.followed_masjids_association.filter_by(masjid_id=masjid_to_unfollow.id).first()

    if not follow_association:
        return {"status": "not_following", "message": "You are not following this Masjid."}

    was_default = follow_association.is_default
    db.session.delete(follow_association)
    db.session.commit()

    # If the unfollowed masjid was the default, we need to set a new default
    if was_default and user.followed_masjids_association.count() > 0:
        new_default = user.followed_masjids_association.first()
        new_default.is_default = True
        db.session.commit()

    return {"status": "success", "message": "Successfully unfollowed the Masjid."}

def set_default_masjid(user, new_default_masjid):
    """Sets a new default masjid for the user from their followed list."""
    # First, set all followed masjids to not be the default
    UserMasjidFollow.query.filter_by(user_id=user.id).update({'is_default': False})
    
    # Now, set the new one as the default
    follow_association = user.followed_masjids_association.filter_by(masjid_id=new_default_masjid.id).first()
    if follow_association:
        follow_association.is_default = True
        db.session.commit()
        return {"status": "success", "message": f"Masjid {new_default_masjid.name} is now your default."}
    else:
        # This case should ideally not be hit if the API checks for following first
        return {"status": "not_following", "message": "You are not following this Masjid."}

def get_masjids_by_location(lat, lon, radius_km=50):
    """Finds masjids within a certain radius of a given location."""
    # This is a simplified example. A real implementation would use PostGIS for efficiency.
    # For now, we will filter in Python, which is inefficient for large datasets.
    all_masjids = User.query.filter_by(role='Masjid').all()
    nearby_masjids = []
    
    from geopy.distance import geodesic
    center_point = (lat, lon)

    for masjid in all_masjids:
        if masjid.default_latitude and masjid.default_longitude:
            masjid_point = (masjid.default_latitude, masjid.default_longitude)
            distance = geodesic(center_point, masjid_point).km
            if distance <= radius_km:
                nearby_masjids.append(masjid)
    
    return nearby_masjids

def create_announcement(masjid, title, content):
    """Creates a new announcement for a Masjid."""
    if masjid.role != 'Masjid':
        return None # Or raise an error
    
    new_announcement = MasjidAnnouncement(
        masjid_id=masjid.id,
        title=title,
        content=content
    )
    db.session.add(new_announcement)
    db.session.commit()

    # Send notification to followers
    send_announcement_to_masjid_followers(masjid, new_announcement)

    return new_announcement

