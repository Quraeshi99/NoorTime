# project/services/api_adapters/base_adapter.py

from abc import ABC, abstractmethod # Abstract Base Classes

class BasePrayerTimeAdapter(ABC):
    """
    Abstract base class for all prayer time API adapters.
    Ensures that all adapters implement a common interface.
    """

    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        # Any other common initialization for all adapters

    @abstractmethod
    def fetch_prayer_times(self, date_obj, latitude, longitude, calculation_method_key_or_params):
        """
        Fetches prayer times for a given date, location, and calculation method.

        :param date_obj: datetime.date object for the desired date.
        :param latitude: float, latitude of the location.
        :param longitude: float, longitude of the location.
        :param calculation_method_key_or_params: String key (e.g., "Karachi", "ISNA") 
                                                 or a dictionary of API-specific parameters
                                                 representing the calculation method.
        :return: A dictionary containing prayer times and other relevant data in a
                 standardized format, or None if an error occurs.
                 Example standardized format:
                 {
                     "Fajr": "HH:MM", "Sunrise": "HH:MM", "Dhuhr": "HH:MM", 
                     "Asr": "HH:MM", "Sunset": "HH:MM", "Maghrib": "HH:MM", 
                     "Isha": "HH:MM", "Imsak": "HH:MM", "Midnight": "HH:MM",
                     "gregorian_date": "DD-MM-YYYY", "gregorian_weekday": "DayName", ...
                     "hijri_date": "DD-MM-YYYY", "hijri_weekday": "DayName", ...
                     "temperatureC": float (optional), "weather_description": str (optional)
                 }
        """
        pass

    @abstractmethod
    def map_calculation_method_key(self, user_selected_method_key):
        """
        Maps a user-friendly calculation method key (e.g., "Hanafi", "Shafii_Standard")
        to the API-specific parameters required by this adapter.

        :param user_selected_method_key: String, the key selected by the user in settings.
        :return: API-specific method parameters (e.g., an integer ID, a dictionary of params).
        """
        pass

    # You can add other common methods here if needed by all adapters,
    # e.g., a method to check API health or validate parameters.