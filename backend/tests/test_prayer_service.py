# backend/tests/test_prayer_service.py

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from project.services.prayer_time_service import _get_zone_id_from_coords, get_api_prayer_times_for_date_from_service


def test_get_zone_id_from_coords(app):
    """Tests the zone ID generation logic."""
    with app.app_context():
        app.config['PRAYER_ZONE_GRID_SIZE'] = 0.2
        # Test with positive coordinates
        assert _get_zone_id_from_coords(28.6, 77.2) == "grid_28.6_77.2"
        # Test with negative coordinates
        assert _get_zone_id_from_coords(-33.86, 151.2) == "grid_-34.0_151.0"
        # Test with coordinates on the edge of a grid
        assert _get_zone_id_from_coords(28.8, 77.4) == "grid_28.8_77.4"


@patch('project.services.prayer_time_service.get_selected_api_adapter')
def test_get_api_prayer_times_for_leap_year(mock_get_adapter, test_client):
    """Tests if the service can handle a leap year date correctly."""
    # Mock the adapter and its fetch_yearly_calendar method
    mock_adapter = MagicMock()
    mock_get_adapter.return_value = mock_adapter

    # Create mock data for a leap year
    mock_yearly_data = []
    for i in range(1, 367):
        day = date(2024, 1, 1) + timedelta(days=i-1)
        mock_yearly_data.append({
            'date': {'gregorian': {'date': day.strftime("%d-%m-%Y")}},
            'timings': {'Fajr': '05:00'}
        })

    mock_adapter.fetch_yearly_calendar.return_value = mock_yearly_data

    # Request prayer times for a leap day
    with test_client.application.app_context():
        result = get_api_prayer_times_for_date_from_service(date(2024, 2, 29), 28.6, 77.2, "Karachi")

    # Check if the correct data is returned
    assert result is not None
    assert result['date']['gregorian']['date'] == "29-02-2024"""

@patch('project.services.prayer_time_service.datetime')
def test_calculate_zohwa_e_kubra_times(mock_datetime, app):
    """Tests the calculation of Zohwa-e-Kubra start and end times."""
    from project.services.prayer_time_service import calculate_display_times_from_service
    from project.models import UserSettings # Assuming UserSettings is available or mocked

    # Mock datetime.date.today() for consistent midpoint calculation
    mock_datetime.date.today.return_value = date(2024, 1, 1)
    mock_datetime.datetime = datetime.datetime # Ensure datetime.datetime is available

    # Mock user settings
    mock_user_settings = MagicMock(spec=UserSettings)
    mock_user_settings.threshold_minutes = 0
    # Mock other prayer settings to avoid errors, though not directly tested here
    mock_user_settings.fajr_is_fixed = False
    mock_user_settings.dhuhr_is_fixed = False
    mock_user_settings.asr_is_fixed = False
    mock_user_settings.maghrib_is_fixed = False
    mock_user_settings.isha_is_fixed = False
    mock_user_settings.jummah_is_fixed = False
    mock_user_settings.last_api_times_for_threshold = "{}" # Empty JSON string

    # Mock API times for today
    api_times_today = {
        "Fajr": "05:00",
        "Sunrise": "06:00",
        "Sunset": "18:00",
        "Dhuhr": "12:30", # Required for other calculations, not Zohwa-e-Kubra
        "Asr": "16:00",
        "Maghrib": "18:00",
        "Isha": "19:30",
        "Imsak": "04:50"
    }
    api_times_tomorrow = {} # Not relevant for this test
    app_config = {} # Not relevant for this test

    with app.app_context():
        calculated_times, _ = calculate_display_times_from_service(
            mock_user_settings, api_times_today, api_times_tomorrow, app_config
        )

    # Assert Zohwa-e-Kubra Start Time: Midpoint of Fajr (05:00) and Sunset (18:00)
    # Duration = 13 hours (780 minutes). Midpoint = 6.5 hours (390 minutes) after 05:00.
    # 05:00 + 6h 30m = 11:30
    assert calculated_times["zohwa_kubra"]["start"] == "11:30"

    # Assert Zohwa-e-Kubra End Time: Midpoint of Sunrise (06:00) and Sunset (18:00)
    # Duration = 12 hours (720 minutes). Midpoint = 6 hours (360 minutes) after 06:00.
    # 06:00 + 6h = 12:00
    assert calculated_times["zohwa_kubra"]["end"] == "12:00"