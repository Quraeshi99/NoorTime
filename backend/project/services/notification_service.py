# project/services/notification_service.py

from flask import current_app
from pyfcm import FCMNotification
from ..models import User, UserDevice


def get_push_service():
    """Initializes and returns the FCM push service."""
    api_key = current_app.config.get('FCM_SERVER_KEY')
    if not api_key:
        current_app.logger.error("FCM_SERVER_KEY is not configured. Push notifications are disabled.")
        return None
    return FCMNotification(api_key=api_key)

def send_notification_to_user(user, title, body, data_message=None):
    """
    Sends a push notification to all registered devices for a specific user.

    Args:
        user (User): The user object to send the notification to.
        title (str): The title of the notification.
        body (str): The body/message of the notification.
        data_message (dict, optional): A dictionary of custom data to send with the notification.
    """
    push_service = get_push_service()
    if not push_service:
        return

    # Get all device tokens for the user
    device_tokens = [device.device_token for device in user.devices]

    if not device_tokens:
        current_app.logger.info(f"User {user.id} has no registered devices. Skipping notification.")
        return

    current_app.logger.info(f"Sending notification to {len(device_tokens)} devices for user {user.id}.")

    try:
        result = push_service.notify_multiple_devices(
            registration_ids=device_tokens,
            message_title=title,
            message_body=body,
            data_message=data_message
        )
        current_app.logger.debug(f"FCM result: {result}")
        # TODO: Handle cleanup of invalid tokens based on the result

    except Exception as e:
        current_app.logger.error(f"Error sending FCM notification: {e}", exc_info=True)

def send_announcement_to_masjid_followers(masjid, announcement):
    """
    Sends a notification for a new announcement to all followers of a Masjid.

    Args:
        masjid (User): The Masjid user object that created the announcement.
        announcement (MasjidAnnouncement): The announcement object.
    """
    if masjid.role != 'Masjid':
        current_app.logger.warning(f"Attempted to send announcement from non-masjid user {masjid.id}")
        return

    # The title of the notification will be the Masjid's name
    title = masjid.name or "New Announcement"
    body = announcement.title
    
    # Optional: send the announcement ID or other data for the app to handle
    data_message = {
        "type": "new_announcement",
        "announcement_id": str(announcement.id),
        "masjid_id": str(masjid.id)
    }

    # Get all followers
    followers = [association.user for association in masjid.followers_association]
    
    current_app.logger.info(f"Sending announcement '{announcement.id}' from Masjid '{masjid.id}' to {len(followers)} followers.")

    for follower in followers:
        send_notification_to_user(follower, title, body, data_message)
