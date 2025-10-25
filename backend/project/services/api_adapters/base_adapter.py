# This module defines the base interface for all prayer time API adapters.
from abc import ABC, abstractmethod

class BasePrayerAdapter(ABC):
    """
    Abstract base class for prayer time API adapters. It ensures that all adapters
    adhere to a common interface, returning data in a standardized format.
    """

    @abstractmethod
    def fetch_daily_timings(self, date_obj, latitude, longitude, method_id, asr_juristic_id, high_latitude_method_id):
        """Fetches prayer times for a single day and returns them in a standardized format."""
        pass

    @abstractmethod
    def fetch_yearly_calendar(self, year, latitude, longitude, method_id, asr_juristic_id, high_latitude_method_id):
        """Fetches a full year's prayer calendar and returns it in a standardized format."""
        pass
