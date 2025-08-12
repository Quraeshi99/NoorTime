# backend/tests/test_api_routes.py

import json
import pytest
from unittest.mock import patch
from project.models import User, Permission, UserPermission
from project.utils.constants import Roles

# --- GUEST Endpoint Tests ---

def test_initial_prayer_data_guest(test_client, init_database):
    response = test_client.get('/api/initial_prayer_data?lat=40.7128&lon=-74.0060&method=ISNA')
    assert response.status_code == 200
    data = json.loads(response.data.decode('utf-8'))
    assert 'prayerTimes' in data
    assert data['isUserAuthenticated'] is False
    assert 'chasht' in data['prayerTimes'] # Check for Chasht time
    assert 'azan' in data['prayerTimes']['chasht'] # Check for Azan in Chasht

def test_geocode_city(test_client, init_database):
    with patch('project.routes.api_routes.get_geocoded_location') as mock_geocode:
        mock_geocode.return_value = {"lat": 51.5074, "lon": -0.1278, "city_name": "London"}
        response = test_client.get('/api/geocode?city=London')
        assert response.status_code == 200

# --- AUTHENTICATED Client Endpoint Tests ---

def test_update_client_settings_unauthenticated(test_client, init_database):
    """WHEN '/api/client/settings' is POSTed without a token, THEN check for a 401 error."""
    response = test_client.post('/api/client/settings', json={})
    assert response.status_code == 401

def test_update_client_settings_authenticated_with_permission(test_client, init_database, auth_headers_for_client, mock_jwks_client, client_user_in_db):
    """
    GIVEN an authenticated Client with 'can_update_own_settings' permission
    WHEN '/api/client/settings' is POSTed with valid data
    THEN check that the settings are updated successfully.
    """
    # Ensure the client has the permission (default for Client role)
    # This is implicitly handled by default_role_permissions fixture in conftest.py
    
    settings_data = {
        "name": "Test Client Updated",
        "default_city_name": "Test City Updated",
        "time_format_preference": "24h",
        "settings": {
            "fajr_is_fixed": True,
            "fajr_fixed_jamaat": "06:30"
        }
    }
    response = test_client.post('/api/client/settings', headers=auth_headers_for_client, json=settings_data)
    
    assert response.status_code == 200
    data = json.loads(response.data.decode('utf-8'))
    assert data['message'] == "Settings updated successfully."

    # Verify the data was actually written to the database
    user = User.query.filter_by(id=client_user_in_db.id).first()
    assert user is not None
    assert user.name == "Test Client Updated"
    assert user.time_format_preference == "24h"
    assert user.settings.fajr_is_fixed is True
    assert user.settings.fajr_fixed_jamaat == "06:30"

def test_update_client_settings_authenticated_without_permission(test_client, init_database, auth_headers_for_client, mock_jwks_client, client_user_in_db):
    """
    GIVEN an authenticated Client without 'can_update_own_settings' permission
    WHEN '/api/client/settings' is POSTed
    THEN check that a 403 Forbidden error is returned.
    """
    # Revoke the default permission for this specific test user
    perm = Permission.query.filter_by(name='can_update_own_settings').first()
    if perm:
        user_perm = UserPermission(user_id=client_user_in_db.id, permission_id=perm.id, has_permission=False)
        db.session.add(user_perm)
        db.session.commit()

    settings_data = {"name": "Should Not Update"}
    response = test_client.post('/api/client/settings', headers=auth_headers_for_client, json=settings_data)
    
    assert response.status_code == 403
    data = json.loads(response.data.decode('utf-8'))
    assert data['error'] == "Permission 'can_update_own_settings' required."

    # Verify data was NOT written
    user = User.query.filter_by(id=client_user_in_db.id).first()
    assert user.name != "Should Not Update"