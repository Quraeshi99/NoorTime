import pytest
from unittest.mock import patch
import json

# The 'app', 'db', and 'test_client' fixtures are defined in conftest.py

def test_initial_prayer_data_guest(test_client, mocker):
    """
    GIVEN a guest user
    WHEN the /api/initial_prayer_data endpoint is called without params
    THEN it should return default prayer times with correct mocking.
    """
    # Mock the service functions where they are used in the route
    mock_prayer_times = {
        "timings": {"Fajr": "05:00", "Sunrise": "06:30", "Dhuhr": "13:00", "Asr": "17:00", "Maghrib": "18:45", "Isha": "20:00"},
        "date": {
            "gregorian": {"date": "06-09-2025", "weekday": {"en": "Saturday"}},
            "hijri": {"date": "13-03-1447", "month": {"en": "Rabi' al-awwal"}, "year": "1447"}
        }
    }
    # Patch the functions in the module where they are imported and used
    mocker.patch('project.routes.api_routes.get_api_prayer_times_for_date_from_service', return_value=mock_prayer_times)
    mocker.patch('project.routes.api_routes.get_current_prayer_period_from_service', return_value={'name': 'ASR'})
    mocker.patch('project.routes.api_routes._get_single_prayer_info', return_value={'azan': '20:15', 'jamaat': '20:30'})

    response = test_client.get('/api/initial_prayer_data')
    
    assert response.status_code == 200
    data = response.get_json()
    assert "prayerTimes" in data
    assert data["currentLocationName"] == "Default Location"
    # Check if the offset logic is applied correctly based on the default UserSettings
    assert data["prayerTimes"]["fajr"]["azan"] == "05:10" 

def test_geocode_valid_city(test_client, mocker):
    """
    GIVEN a guest user
    WHEN the /api/geocode endpoint is called with a valid city
    THEN it should return the geocoded location.
    """
    # Mock the service function where it is used in the route
    try:
        mocker.patch(
            'project.routes.api_routes.get_geocoded_location_with_cache',
            return_value={
                "latitude": 51.5074,
                "longitude": -0.1278,
                "city_name": "London",
                "country_name": "United Kingdom"
            }
        )
    except Exception as e:
        print(f"Error patching: {e}")
    
    response = test_client.get('/api/geocode?city=London')
    assert response.status_code == 200
    data = response.get_json()
    assert data["city_name"] == "London"
    assert data["latitude"] == 51.5074

def test_geocode_invalid_city(test_client):
    """
    GIVEN a guest user
    WHEN the /api/geocode endpoint is called with an invalid city
    THEN it should return a 400 error.
    """
    # This test does not involve mocking as it should fail validation before calling the service
    response = test_client.get('/api/geocode?city=')
    assert response.status_code == 400
    data = response.get_json()
    assert "message" in data
