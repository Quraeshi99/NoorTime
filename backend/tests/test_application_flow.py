"""
Tests for the Masjid Application Workflow
-----------------------------------------
This file contains tests for the entire application submission and verification
process, from a user submitting the form to the admin approving or rejecting it.
"""

import pytest
from project.models import User, MasjidApplication


def test_submit_application_successfully(test_client, db):
    """
    GIVEN a logged-in client user
    WHEN they submit a valid masjid application
    THEN a new MasjidApplication record should be created in the database
    """
    # Log in the user to get a valid JWT token
    # (Assuming you have a /login endpoint that returns a token)
    # For this test, we'll assume the test_client is already authenticated
    # or that the endpoint is temporarily unprotected for testing.
    
    application_data = {
        "official_name": "Test Masjid",
        "address_line_1": "123 Test St",
        "city": "Testville",
        "state": "TS",
        "postal_code": "12345",
        "country": "Testland",
        "latitude": 10.0,
        "longitude": 20.0,
        "has_official_document": False,
        "exterior_photo_url": "http://example.com/exterior.jpg",
        "interior_photo_url": "http://example.com/interior.jpg"
    }

    # We need to simulate a logged-in user (g.user)
    # This often requires mocking the jwt_required decorator or using a test fixture
    # For now, let's assume the endpoint can be called and we can pass the user ID.
    # A better approach is to use an authentication fixture.

    # Create a test user to be the applicant
    applicant = User(email='applicant@test.com', name='Test Applicant', role='Client')
    db.session.add(applicant)
    db.session.commit()

    # We will call the service function directly to test the logic
    from project.services import application_service
    new_app = application_service.submit_application(applicant, application_data)

    assert new_app is not None
    assert new_app.official_name == "Test Masjid"
    assert new_app.applicant == applicant
    assert new_app.status == 'pending'

    # Verify it's in the database
    db_app = MasjidApplication.query.get(new_app.id)
    assert db_app is not None
    assert db_app.city == "Testville"


def test_verification_process_auto_approves_high_score(mocker, db):
    """
    GIVEN a new application
    WHEN the verification process runs and all checks pass
    THEN the application status should be updated to 'approved'
    """
    # Mock the external services
    mocker.patch('project.services.third_party.image_hashing_service.generate_phash_from_url', return_value='test_hash')
    mocker.patch('project.services.third_party.image_hashing_service.compare_phashes', return_value=10) # Not a duplicate
    mocker.patch('project.services.application_service._check_for_nearby_masjids', return_value=(False, None))
    mocker.patch('project.services.third_party.google_vision_service.detect_text_in_document_from_url', return_value='Text containing Test Masjid')
    mock_send_email = mocker.patch('project.services.notification_service.send_approval_email')

    # Setup data
    from project.services import application_service
    from project.models import db, User, MasjidApplication
    applicant = User(email='good@user.com', name='Good User', role='Client')
    db.session.add(applicant)
    db.session.commit()
    app = application_service.submit_application(applicant, {
        "official_name": "Test Masjid",
        "address_line_1": "123 Test St",
        "city": "Testville",
        "state": "TS",
        "postal_code": "12345",
        "country": "Testland",
        "latitude": 10.0,
        "longitude": 20.0,
        "has_official_document": True,
        "exterior_photo_url": "http://example.com/exterior.jpg",
        "interior_photo_url": "http://example.com/interior.jpg"
    })

    # Run the process
    application_service.start_verification_process(app.id)

    # Check results
    updated_app = MasjidApplication.query.get(app.id)
    assert updated_app.status == 'approved'
    assert updated_app.trust_score > 60
    mock_send_email.assert_called_once()


def test_verification_process_flags_for_duplicate_image(mocker, db):
    """
    GIVEN a new application with a duplicate image
    WHEN the verification process runs
    THEN the application status should be 'needs_manual_review'
    """
    # Mock services to simulate a duplicate image
    mocker.patch('project.services.third_party.image_hashing_service.generate_phash_from_url', return_value='duplicate_hash')
    mocker.patch('project.services.application_service._check_internal_image_duplicates', return_value=(True, 123))
    mocker.patch('project.services.application_service._check_for_nearby_masjids', return_value=(False, None))

    # Setup data
    from project.services import application_service
    from project.models import db, User, MasjidApplication
    applicant = User(email='bad@user.com', name='Bad User', role='Client')
    db.session.add(applicant)
    db.session.commit()
    app = application_service.submit_application(applicant, {
        "official_name": "Duplicate Masjid",
        "address_line_1": "123 Test St",
        "city": "Testville",
        "state": "TS",
        "postal_code": "12345",
        "country": "Testland",
        "latitude": 10.0,
        "longitude": 20.0,
        "has_official_document": False,
        "exterior_photo_url": "http://example.com/exterior.jpg",
        "interior_photo_url": "http://example.com/interior.jpg"
    })

    # Run the process
    application_service.start_verification_process(app.id)

    # Check results
    updated_app = MasjidApplication.query.get(app.id)
    assert updated_app.status == 'needs_manual_review'
    assert 'duplicate of images' in updated_app.rejection_reason


def test_admin_can_approve_pending_application(mocker, db):
    """
    GIVEN a pending application
    WHEN an admin approves it
    THEN the applicant's role should be changed to 'Masjid'
    """
    mock_send_email = mocker.patch('project.services.notification_service.send_approval_email')
    
    from project.services import application_service
    from project.models import db, User, MasjidApplication
    applicant = User(email='pending@user.com', name='Pending User', role='Client')
    admin = User(email='admin@noortime.com', name='Admin', role='Super Admin')
    db.session.add_all([applicant, admin])
    db.session.commit()
    
    app = MasjidApplication(
        applicant=applicant, 
        official_name="Pending Masjid", 
        status='needs_manual_review',
        address_line_1="123 Test St",
        city="Testville",
        state="TS",
        postal_code="12345",
        country="Testland",
        latitude=10.0,
        longitude=20.0,
        exterior_photo_url="http://example.com/exterior.jpg",
        interior_photo_url="http://example.com/interior.jpg"
    )
    db.session.add(app)
    db.session.commit()

    # Admin approves
    application_service.approve_application(app, admin)

    # Check results
    assert app.status == 'approved'
    assert applicant.role == 'Masjid'
    assert app.reviewed_by == admin
    mock_send_email.assert_called_once_with(app)