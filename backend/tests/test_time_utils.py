import datetime
import pytest
from backend.project.utils.time_utils import get_prayer_key_for_tomorrow

# Test case for a normal day (e.g., Monday)
def test_get_prayer_key_for_tomorrow_normal_day():
    # Monday
    test_date = datetime.date(2025, 8, 11)
    assert get_prayer_key_for_tomorrow('DHUHR', test_date) == 'Dhuhr'
    assert get_prayer_key_for_tomorrow('ASR', test_date) == 'Asr'

# Test case for Thursday
def test_get_prayer_key_for_tomorrow_thursday():
    # Thursday (Today's date from the context)
    test_date = datetime.date(2025, 8, 14)
    # During Dhuhr period on a Thursday, it should show Jummah for tomorrow
    assert get_prayer_key_for_tomorrow('DHUHR', test_date) == 'Jummah'
    # For other prayers, it should be the same
    assert get_prayer_key_for_tomorrow('ASR', test_date) == 'Asr'

# Test case for Friday
def test_get_prayer_key_for_tomorrow_friday():
    # Friday
    test_date = datetime.date(2025, 8, 15)
    # During Dhuhr (Jummah) period on a Friday, it should show Dhuhr for tomorrow (Saturday)
    assert get_prayer_key_for_tomorrow('DHUHR', test_date) == 'Dhuhr'
    assert get_prayer_key_for_tomorrow('ASR', test_date) == 'Asr'

# Test case for non-prayer periods
def test_get_prayer_key_for_tomorrow_non_prayer_period():
    test_date = datetime.date(2025, 8, 11)
    # If the current period is something like 'SUNRISE' or invalid, it should default to 'Fajr'
    assert get_prayer_key_for_tomorrow('SUNRISE', test_date) == 'Fajr'
    assert get_prayer_key_for_tomorrow('ANYTHING_ELSE', test_date) == 'Fajr'