# backend/tests/test_api_routes.py

import json
import pytest
from unittest.mock import patch, MagicMock
from project.models import User, Permission, UserPermission, db, UserSettings
from project.utils.constants import Roles
import datetime

# --- GUEST Endpoint Tests ---

def test_initial_prayer_data_guest(test_client):
    with patch('project.routes.api_routes.get_api_prayer_times_for_date_from_service') as mock_prayer_times_service, \
         patch('project.routes.api_routes.calculate_display_times_from_service') as mock_calculate_display_times, \
         patch('project.routes.api_routes.get_current_prayer_period_from_service') as mock_current_period, \
         patch('project.routes.api_routes._get_single_prayer_info') as mock_single_prayer_info, \
         patch('project.routes.api_routes.UserSettings') as mock_user_settings:

        # Mocking the return values for the services
        mock_prayer_times_service.side_effect = [
            {'timings': {'Fajr': '05:00', 'Dhuhr': '13:00', 'Asr': '17:00', 'Maghrib': '19:00', 'Isha': '20:30'}, 'date': {'gregorian': {'date': '10-08-2025', 'weekday': {'en': 'Sunday'}}, 'hijri': {'date': '06-02-1447', 'month': {'en': 'Rajab'}, 'year': '1447'}}}, 
            {'timings': {'Fajr': '05:01', 'Dhuhr': '13:01', 'Asr': '17:01', 'Maghrib': '19:01', 'Isha': '20:31'}},
            {'timings': {'Fajr': '05:02', 'Dhuhr': '13:02', 'Asr': '17:02', 'Maghrib': '19:02', 'Isha': '20:32'}}
        ]
        mock_calculate_display_times.return_value = ({ 
            'fajr': {'azan': '05:00', 'jamaat': '05:30'},
            'dhuhr': {'azan': '13:00', 'jamaat': '13:30'},
            'asr': {'azan': '17:00', 'jamaat': '17:30'},
            'maghrib': {'azan': '19:00', 'jamaat': '19:15'},
            'isha': {'azan': '20:30', 'jamaat': '21:00'},
            'jummah': {'azan': '13:00', 'jamaat': '13:45'},
            'chasht': {'azan': '09:00', 'jamaat': '09:15'}
        }, False)
        mock_current_period.return_value = {'name': 'FAJR'}
        mock_single_prayer_info.return_value = {'name': 'FAJR', 'azan': '05:01', 'jamaat': '05:31'}
        mock_user_settings.return_value.last_api_times_for_threshold = None

        response = test_client.get('/api/initial_prayer_data?lat=40.7128&lon=-74.0060&method=ISNA')
        
        assert response.status_code == 200

def test_geocode_city(test_client):
    with patch('project.routes.api_routes.get_geocoded_location_with_cache') as mock_geocode, \
         patch('project.routes.api_routes.current_app.logger.error') as mock_logger:
        mock_geocode.return_value = {"error": "Service unavailable"}
    
        response = test_client.get('/api/geocode?city=London')
        assert response.status_code == 404

# --- AUTHENTICATED Client Endpoint Tests ---

def test_update_client_settings_unauthenticated(test_client):
    """WHEN '/api/client/settings' is POSTed without a token, THEN check for a 401 error."""
    response = test_client.post('/api/client/settings', json={})
    assert response.status_code == 401

def test_update_client_settings_authenticated_with_permission(test_client, auth_headers_for_client, client_user_in_db):
    """
    GIVEN an authenticated Client with 'can_update_own_settings' permission
    WHEN '/api/client/settings' is POSTed with valid data
    THEN check that the settings are updated successfully.
    """
    with patch('project.routes.api_routes.db.session.commit') as mock_commit:
        client_user_in_db.settings = UserSettings()
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
        assert data == {"message": "Settings updated successfully."}
        mock_commit.assert_called()

def test_update_client_settings_authenticated_without_permission(test_client, auth_headers_for_client, client_user_in_db):
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
    assert "Permission 'can_update_own_settings' required" in data['error']

    # Verify data was NOT written
    user = User.query.filter_by(id=client_user_in_db.id).first()
    assert user.name != "Should Not Update"