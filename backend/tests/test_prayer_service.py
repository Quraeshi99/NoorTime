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
    assert result['date']['gregorian']['date'] == "29-02-2024"