"""
Masjid Application Service
--------------------------
This service contains the core business logic for handling the entire lifecycle
of a Masjid Application, from submission to verification and final approval
or rejection.
"""

from .. import db
from ..models import MasjidApplication, User, ApplicationAuditLog


def submit_application(applicant: User, application_data: dict) -> MasjidApplication:
    """
    Creates a new MasjidApplication record in the database.

    This is the first step in the registration process. After the application
    is created, a background task will be triggered to start the automated
    verification process.

    Args:
        applicant: The User object of the user who is applying.
        application_data: A dictionary containing the application form data,
                          including name, address, photos, etc.

    Returns:
        The newly created MasjidApplication object.
    """
    new_application = MasjidApplication(
        applicant=applicant,
        official_name=application_data.get('official_name'),
        address_line_1=application_data.get('address_line_1'),
        city=application_data.get('city'),
        state=application_data.get('state'),
        postal_code=application_data.get('postal_code'),
        country=application_data.get('country'),
        latitude=application_data.get('latitude'),
        longitude=application_data.get('longitude'),
        website_url=application_data.get('website_url'),
        has_official_document=application_data.get('has_official_document', False),
        document_url=application_data.get('document_url'),
        exterior_photo_url=application_data.get('exterior_photo_url'),
        interior_photo_url=application_data.get('interior_photo_url'),
        status='pending' # Initial status
    )

    db.session.add(new_application)
    db.session.commit()

    # In a real-world scenario, you would trigger a background task here.
    # For example, using Celery: `start_verification_process.delay(new_application.id)`
    # For now, we will call it directly for simplicity, but this should be asynchronous.
    # start_verification_process(new_application.id)

    return new_application


# --- Verification Logic ---

from . import notification_service

from .third_party import image_hashing_service, google_vision_service
from ..models import ImageFingerprint
from sqlalchemy.sql import func

# Constants for the verification process
HAMMING_DISTANCE_THRESHOLD = 5 # How similar images can be to be considered duplicates
NEARBY_RADIUS_METERS = 100 # Radius to check for duplicate masjid locations

def start_verification_process(application_id: int):
    """
    The main entry point for the automated verification process.
    This function orchestrates all the individual verification steps.
    
    NOTE: This should be run as an asynchronous background task.
    
    Args:
        application_id: The ID of the MasjidApplication to verify.
    """
    application = MasjidApplication.query.get(application_id)
    if not application:
        print(f"Application with ID {application_id} not found.")
        return

    verification_details = {}
    trust_score = 0

    # 1. Internal Image Duplicate Check
    is_duplicate, matched_masjid_id = _check_internal_image_duplicates(application)
    verification_details['image_is_internal_duplicate'] = is_duplicate
    if is_duplicate:
        trust_score -= 50 # Heavy penalty for duplicate images
        application.status = 'needs_manual_review'
        application.rejection_reason = f"Potential duplicate of images from Masjid ID: {matched_masjid_id}"
    else:
        trust_score += 25

    # 2. Nearby Location Check
    is_nearby, nearby_masjid_id = _check_for_nearby_masjids(application)
    verification_details['has_nearby_masjid'] = is_nearby
    if is_nearby:
        trust_score -= 10
        application.status = 'needs_manual_review'
        application.rejection_reason = (application.rejection_reason or "") + f" | Nearby Masjid found: ID {nearby_masjid_id}"
    else:
        trust_score += 15

    # 3. Document OCR Check (if document was provided)
    if application.has_official_document:
        document_text = google_vision_service.detect_text_in_document_from_url(application.document_url)
        verification_details['document_ocr_text'] = document_text
        if document_text and application.official_name.lower() in document_text.lower():
            trust_score += 30
            verification_details['document_name_match'] = True
        else:
            trust_score -= 10
            verification_details['document_name_match'] = False

    # Update the application with the results
    application.trust_score = trust_score
    application.verification_details = verification_details
    
    # Decide final status based on score
    if application.status != 'needs_manual_review':
        if trust_score >= 60:
            # High score, auto-approve
            approve_application(application, User.query.get(1)) # Assuming user 1 is system/bot
        elif trust_score < 20:
            # Low score, auto-reject
            reject_application(application, User.query.get(1), "Failed automated checks.")
        else:
            # Medium score, needs review
            application.status = 'needs_manual_review'

    db.session.commit()


def _check_internal_image_duplicates(application: MasjidApplication) -> (bool, int):
    """Checks if the application's images are duplicates of existing ones."""
    # Generate hashes for the new images
    exterior_hash = image_hashing_service.generate_phash_from_url(application.exterior_photo_url)
    interior_hash = image_hashing_service.generate_phash_from_url(application.interior_photo_url)

    if not exterior_hash or not interior_hash:
        return True, None # Failed to hash, flag for review

    # Store the new hashes
    db.session.add(ImageFingerprint(application_id=application.id, image_url=application.exterior_photo_url, image_type='exterior', phash=exterior_hash))
    db.session.add(ImageFingerprint(application_id=application.id, image_url=application.interior_photo_url, image_type='interior', phash=interior_hash))

    # Check against all other fingerprints
    all_other_hashes = ImageFingerprint.query.filter(ImageFingerprint.application_id != application.id).all()

    for existing_fp in all_other_hashes:
        if image_hashing_service.compare_phashes(exterior_hash, existing_fp.phash) < HAMMING_DISTANCE_THRESHOLD:
            return True, existing_fp.user_id or existing_fp.application.user_id
        if image_hashing_service.compare_phashes(interior_hash, existing_fp.phash) < HAMMING_DISTANCE_THRESHOLD:
            return True, existing_fp.user_id or existing_fp.application.user_id

    return False, None

def _check_for_nearby_masjids(application: MasjidApplication) -> (bool, int):
    """Checks for existing approved masjids within a certain radius."""
    # Using a simplified distance calculation. For production, use PostGIS.
    # Earth radius in kilometers
    earth_radius_km = 6371

    # Convert radius to degrees for latitude/longitude
    lat_diff = (NEARBY_RADIUS_METERS / 1000.0) / earth_radius_km
    lon_diff = (NEARBY_RADIUS_METERS / 1000.0) / (earth_radius_km * func.cos(func.radians(application.latitude)))

    nearby_masjids = User.query.filter(
        User.role == 'Masjid',
        func.abs(User.default_latitude - application.latitude) < lat_diff,
        func.abs(User.default_longitude - application.longitude) < lon_diff
    ).all()

    if nearby_masjids:
        return True, nearby_masjids[0].id
    return False, None

# --- Approval and Rejection Logic ---

def approve_application(application: MasjidApplication, admin_user: User):
    """Approves an application and promotes the applicant to a Masjid user."""
    applicant = application.applicant
    applicant.role = 'Masjid'
    # You would call your masjid code generation logic here
    # applicant.masjid_code = generate_unique_masjid_code()
    
    application.status = 'approved'
    application.reviewed_by = admin_user
    
    # Link fingerprints to the user now that they are a masjid
    for fp in ImageFingerprint.query.filter_by(application_id=application.id).all():
        fp.user_id = applicant.id
        fp.application_id = None # Clear the link to the application

    db.session.add(ApplicationAuditLog(application=application, actor=admin_user, action='approved'))
    db.session.commit()
    notification_service.send_approval_email(application)

def reject_application(application: MasjidApplication, admin_user: User, reason: str):
    """Rejects an application."""
    application.status = 'rejected'
    application.rejection_reason = reason
    application.reviewed_by = admin_user
    db.session.add(ApplicationAuditLog(application=application, actor=admin_user, action='rejected', details=reason))
    db.session.commit()
    notification_service.send_rejection_email(application)
