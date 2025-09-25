"""
Notification Service
--------------------
This service is responsible for sending all user-facing notifications, starting
with emails for the Masjid Application process.
"""

from flask_mail import Message
from .. import mail
from ..models import MasjidApplication

def send_approval_email(application: MasjidApplication):
    """
    Sends an email to the user informing them that their application has been approved.

    Args:
        application: The approved MasjidApplication object.
    """
    if not application.applicant.email:
        return

    applicant = application.applicant
    subject = "Congratulations! Your Masjid Application has been Approved"
    body = f"""Dear {applicant.name},

Congratulations! Your application to register '{application.official_name}' as a Masjid on NoorTime has been approved.

Your unique Masjid Code is: {applicant.masjid_code}

You can now log in to your account to manage your Masjid's prayer times and post announcements for your followers.

Thank you for being a part of the NoorTime community.

Sincerely,
The NoorTime Team"""

    msg = Message(subject, recipients=[applicant.email], body=body)
    
    try:
        mail.send(msg)
    except Exception as e:
        # In a production app, you would log this error extensively.
        print(f"Error sending approval email to {applicant.email}: {e}")

def send_rejection_email(application: MasjidApplication):
    """
    Sends an email to the user informing them that their application has been rejected.

    Args:
        application: The rejected MasjidApplication object.
    """
    if not application.applicant.email:
        return

    applicant = application.applicant
    subject = "Update on Your NoorTime Masjid Application"
    reason = application.rejection_reason or "the information provided could not be verified at this time."
    body = f"""Dear {applicant.name},

Thank you for your interest in registering '{application.official_name}' as a Masjid on NoorTime.

After careful review, we were unable to approve your application at this time. 
Reason for rejection: {reason}

This could be due to several factors, such as an unverified address, duplicate images, or incomplete information. Please review your submission and feel free to re-apply with corrected information.

If you believe this is an error, please contact our support team.

Sincerely,
The NoorTime Team"""

    msg = Message(subject, recipients=[applicant.email], body=body)
    
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending rejection email to {applicant.email}: {e}")