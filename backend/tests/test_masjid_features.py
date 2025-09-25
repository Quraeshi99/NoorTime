# tests/test_masjid_features.py

import pytest
import json
from flask import g

from project.models import User, UserSettings, MasjidAnnouncement, UserMasjidFollow, Permission, RolePermission
from project.services.masjid_service import generate_unique_masjid_code

@pytest.fixture
def setup_community_features(db):
    """Set up users, a masjid, permissions, and roles for testing."""
    # 1. Create Permissions
    perm_create_announcement = Permission(name='can_create_announcements', description='Can create announcements for their own masjid')
    db.session.add(perm_create_announcement)
    db.session.commit()

    # 2. Assign Permissions to Roles
    role_perm = RolePermission(role_name='Masjid', permission_id=perm_create_announcement.id)
    db.session.add(role_perm)

    # 3. Create a Masjid User
    masjid_user = User(
        email='masjid@example.com',
        name='Test Masjid',
        role='Masjid',
        masjid_code=generate_unique_masjid_code(),
        default_latitude=41.0082, # Istanbul
        default_longitude=28.9784,
        default_city_name='Istanbul',
        default_calculation_method='MWL'
    )
    masjid_settings = UserSettings(fajr_fixed_azan="05:00", isha_fixed_azan="21:00")
    masjid_user.settings = masjid_settings
    db.session.add(masjid_user)

    # 4. Create a Client User
    client_user = User(email='client@example.com', name='Test Client', role='Client')
    client_settings = UserSettings(fajr_fixed_azan="06:30") # Personal setting
    client_user.settings = client_settings
    db.session.add(client_user)
    
    db.session.commit()
    return client_user, masjid_user

# Helper to mock authentication
def mock_authentication(mocker, user, permissions=None):
    if permissions is None:
        permissions = set()
    
    def mock_validate(*args, **kwargs):
        g.user = user
        g.user_permissions = permissions
        return True, None

    mocker.patch('project.utils.auth._validate_token_and_get_user', side_effect=mock_validate)

def test_follow_masjid(test_client, setup_community_features, mocker):
    """Test a user can follow a masjid."""
    client_user, masjid_user = setup_community_features
    mock_authentication(mocker, client_user)

    response = test_client.post(f'/api/masjids/{masjid_user.id}/follow')
    assert response.status_code == 200
    assert b"Successfully followed the Masjid" in response.data

    follow_relation = UserMasjidFollow.query.filter_by(user_id=client_user.id, masjid_id=masjid_user.id).first()
    assert follow_relation is not None
    assert follow_relation.is_default is True

def test_initial_data_with_followed_masjid(test_client, setup_community_features, mocker):
    """Test initial_prayer_data uses the followed masjid's settings."""
    client_user, masjid_user = setup_community_features
    mock_authentication(mocker, client_user)
    
    test_client.post(f'/api/masjids/{masjid_user.id}/follow') # Follow the masjid

    response = test_client.get('/api/initial_prayer_data')
    assert response.status_code == 200
    data = json.loads(response.data)

    assert data['is_following_default_masjid'] is True
    assert data['default_masjid_info']['id'] == masjid_user.id
    assert data['prayerTimes']['fajr']['azan'] == "05:00" # Masjid's time, not 06:30

def test_update_settings_while_following_fails(test_client, setup_community_features, mocker):
    """Test a user cannot update prayer settings while following a masjid."""
    client_user, masjid_user = setup_community_features
    mock_authentication(mocker, client_user)
    test_client.post(f'/api/masjids/{masjid_user.id}/follow')

    update_data = {"settings": {"fajr_fixed_azan": "09:00"}}
    response = test_client.post('/api/client/settings', data=json.dumps(update_data), content_type='application/json')
    assert response.status_code == 403

def test_masjid_announcements(test_client, setup_community_features, mocker):
    """Test creating and viewing masjid announcements."""
    client_user, masjid_user = setup_community_features
    
    # Mock Masjid User to create announcement
    mock_authentication(mocker, masjid_user, permissions={'can_create_announcements'})
    announcement_data = {"title": "Community Dinner", "content": "Join us this Friday!"}
    response = test_client.post(f'/api/masjids/{masjid_user.id}/announcements', data=json.dumps(announcement_data), content_type='application/json')
    assert response.status_code == 201

    # Mock Client User to view announcement
    mock_authentication(mocker, client_user)
    response = test_client.get(f'/api/masjids/{masjid_user.id}/announcements')
    assert response.status_code == 200
    announcements = json.loads(response.data)
    assert len(announcements) == 1
    assert announcements[0]['title'] == "Community Dinner"

    # Verify client cannot create announcement
    response = test_client.post(f'/api/masjids/{masjid_user.id}/announcements', data=json.dumps(announcement_data), content_type='application/json')
    assert response.status_code == 403