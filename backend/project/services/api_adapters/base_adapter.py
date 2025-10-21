# project/services/api_adapters/base_adapter.py

from abc import ABC, abstractmethod # Abstract Base Classes

class BasePrayerTimeAdapter(ABC):
    """
    Abstract base class for all prayer time API adapters.
    Ensures that all adapters implement a common, consistent interface.
    """

    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url
        self.api_key = api_key

    @abstractmethod
    def fetch_daily_timings(self, date_obj, latitude, longitude, method_id, asr_juristic_id, high_latitude_method_id):
        """
        Fetches prayer times for a single given date, location, and calculation settings.

        Args:
            date_obj (datetime.date): The desired date.
            latitude (float): The latitude of the location.
            longitude (float): The longitude of the location.
            method_id (int): The ID of the calculation method.
            asr_juristic_id (int): The school for Asr calculation (0 for Standard, 1 for Hanafi).
            high_latitude_method_id (int): The adjustment rule for high latitudes.

        Returns:
            dict: A dictionary containing the prayer times for the single day,
                  or None if an error occurs.
        """
        pass

    @abstractmethod
    def fetch_yearly_calendar(self, year, latitude, longitude, method_id, asr_juristic_id, high_latitude_method_id):
        """
        Fetches a full year's prayer time calendar from the API.

        Args:
            year (int): The calendar year.
            latitude (float): The latitude of the location.
            longitude (float): The longitude of the location.
            method_id (int): The ID of the calculation method.
            asr_juristic_id (int): The school for Asr calculation (0 for Standard, 1 for Hanafi).
            high_latitude_method_id (int): The adjustment rule for high latitudes.

        Returns:
            list: A list of daily prayer time data for the entire year, or None if an error occurs.
        """
        pass
