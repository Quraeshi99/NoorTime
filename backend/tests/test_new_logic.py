import datetime
import pytest
from freezegun import freeze_time

# Test for the main API endpoint with mocking
@freeze_time("2025-08-14 13:00:00") # Thursday, 1 PM
def test_initial_data_on_thursday(mocker, test_client):
    """
    GIVEN: Today is a Thursday (controlled by freeze_time).
    WHEN: The /api/initial_prayer_data endpoint is called during Dhuhr time.
    THEN: The 'nextDayPrayerDisplay' should be for 'Jummah'.
    """
    # --- ARRANGE ---
    # No need to patch datetime, freezegun handles it.

    # Mock the service functions that make external calls
    mock_times = {
        'timings': {
            'Fajr': '04:30',
            'Sunrise': '06:00',
            'Dhuhr': '12:30',
            'Asr': '15:45',
            'Maghrib': '18:30',
            'Isha': '20:00'
        },
        'date': {
            'gregorian': {
                'date': '14-08-2025',
                'weekday': {'en': 'Thursday'}
            },
            'hijri': {
                'date': '18-02-1447',
                'month': {'en': 'Safar'},
                'year': '1447'
            }
        }
    }
    mocker.patch(
        'project.routes.api_routes.get_api_prayer_times_for_date_from_service',
        side_effect=[mock_times, mock_times, mock_times]
    )

    mocker.patch(
        'project.routes.api_routes.get_current_prayer_period_from_service',
        return_value={'name': 'DHUHR'}
    )
    
    mocker.patch(
        'project.routes.api_routes.calculate_display_times_from_service',
        return_value=({'fajr': {'azan': '04:30', 'jamaat': '04:50'}, 'dhuhr': {'azan': '12:30', 'jamaat': '12:50'}, 'asr': {'azan': '15:45', 'jamaat': '16:05'}, 'maghrib': {'azan': '18:30', 'jamaat': '18:35'}, 'isha': {'azan': '20:00', 'jamaat': '20:20'}, 'jummah': {'azan': '12:30', 'jamaat': '12:50'}, 'chasht': {'azan': '06:20', 'jamaat': 'N/A'}}, False)
    )
    
    mock_jummah_info = {'azan': '01:30', 'jamaat': '01:45'}
    mocker.patch(
        'project.routes.api_routes._get_single_prayer_info',
        return_value=mock_jummah_info
    )

    # --- ACT ---
    response = test_client.get('/api/initial_prayer_data')

    # --- ASSERT ---
    assert response.status_code == 200
    json_data = response.get_json()
    
    next_day_prayer = json_data.get('nextDayPrayerDisplay')
    assert next_day_prayer is not None
    assert next_day_prayer.get('name') == 'Jummah'

@freeze_time("2025-08-15 13:00:00") # Friday, 1 PM
def test_initial_data_on_friday(mocker, test_client):
    """
    GIVEN: Today is a Friday.
    WHEN: The /api/initial_prayer_data endpoint is called during Dhuhr/Jummah time.
    THEN: The 'nextDayPrayerDisplay' should be for 'Dhuhr' (for Saturday).
    """
    # --- ARRANGE ---
    mock_times = {
        'timings': {
            'Fajr': '04:30',
            'Sunrise': '06:00',
            'Dhuhr': '12:30',
            'Asr': '15:45',
            'Maghrib': '18:30',
            'Isha': '20:00'
        },
        'date': {
            'gregorian': {
                'date': '15-08-2025',
                'weekday': {'en': 'Friday'}
            },
            'hijri': {
                'date': '19-02-1447',
                'month': {'en': 'Safar'},
                'year': '1447'
            }
        }
    }
    mocker.patch(
        'project.routes.api_routes.get_api_prayer_times_for_date_from_service',
        side_effect=[mock_times, mock_times, mock_times]
    )
    mocker.patch(
        'project.routes.api_routes.get_current_prayer_period_from_service',
        return_value={'name': 'DHUHR'} # On Friday, Dhuhr period is Jummah
    )
    mocker.patch(
        'project.routes.api_routes.calculate_display_times_from_service',
        return_value=({'fajr': {'azan': '04:30', 'jamaat': '04:50'}, 'dhuhr': {'azan': '12:30', 'jamaat': '12:50'}, 'asr': {'azan': '15:45', 'jamaat': '16:05'}, 'maghrib': {'azan': '18:30', 'jamaat': '18:35'}, 'isha': {'azan': '20:00', 'jamaat': '20:20'}, 'jummah': {'azan': '12:30', 'jamaat': '12:50'}, 'chasht': {'azan': '06:20', 'jamaat': 'N/A'}}, False)
    )
    mock_dhuhr_info = {'azan': '01:15', 'jamaat': '01:30'}
    mocker.patch(
        'project.routes.api_routes._get_single_prayer_info',
        return_value=mock_dhuhr_info
    )

    # --- ACT ---
    response = test_client.get('/api/initial_prayer_data')

    # --- ASSERT ---
    assert response.status_code == 200
    json_data = response.get_json()
    next_day_prayer = json_data.get('nextDayPrayerDisplay')
    assert next_day_prayer is not None
    assert next_day_prayer.get('name') == 'Dhuhr'

@freeze_time("2025-08-11 16:00:00") # Monday, 4 PM
def test_initial_data_on_normal_day(mocker, test_client):
    """
    GIVEN: Today is a Monday.
    WHEN: The /api/initial_prayer_data endpoint is called during Asr time.
    THEN: The 'nextDayPrayerDisplay' should be for 'Asr'.
    """
    # --- ARRANGE ---
    mock_times = {
        'timings': {
            'Fajr': '04:30',
            'Sunrise': '06:00',
            'Dhuhr': '12:30',
            'Asr': '15:45',
            'Maghrib': '18:30',
            'Isha': '20:00'
        },
        'date': {
            'gregorian': {
                'date': '11-08-2025',
                'weekday': {'en': 'Monday'}
            },
            'hijri': {
                'date': '15-02-1447',
                'month': {'en': 'Safar'},
                'year': '1447'
            }
        }
    }
    mocker.patch(
        'project.routes.api_routes.get_api_prayer_times_for_date_from_service',
        side_effect=[mock_times, mock_times, mock_times]
    )
    mocker.patch(
        'project.routes.api_routes.get_current_prayer_period_from_service',
        return_value={'name': 'ASR'}
    )
    mocker.patch(
        'project.routes.api_routes.calculate_display_times_from_service',
        return_value=({'fajr': {'azan': '04:30', 'jamaat': '04:50'}, 'dhuhr': {'azan': '12:30', 'jamaat': '12:50'}, 'asr': {'azan': '15:45', 'jamaat': '16:05'}, 'maghrib': {'azan': '18:30', 'jamaat': '18:35'}, 'isha': {'azan': '20:00', 'jamaat': '20:20'}, 'jummah': {'azan': '12:30', 'jamaat': '12:50'}, 'chasht': {'azan': '06:20', 'jamaat': 'N/A'}}, False)
    )
    mock_asr_info = {'azan': '05:00', 'jamaat': '05:20'}
    mocker.patch(
        'project.routes.api_routes._get_single_prayer_info',
        return_value=mock_asr_info
    )

    # --- ACT ---
    response = test_client.get('/api/initial_prayer_data')

    # --- ASSERT ---
    assert response.status_code == 200
    json_data = response.get_json()
    next_day_prayer = json_data.get('nextDayPrayerDisplay')
    assert next_day_prayer is not None
    assert next_day_prayer.get('name') == 'Asr'
