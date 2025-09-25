
from abc import ABC, abstractmethod

class BaseGeocodingAdapter(ABC):
    """
    Abstract base class for a geocoding adapter.
    Defines the common interface for all geocoding services.
    """

    @abstractmethod
    def geocode(self, city_name):
        """
        Converts a city name to coordinates.
        Returns a dictionary with 'lat', 'lon', 'city', 'country'.
        """
        pass

    @abstractmethod
    def reverse_geocode(self, lat, lon):
        """
        Converts coordinates to a human-readable address.
        """
        pass

    @abstractmethod
    def autocomplete(self, query):
        """
        Provides address suggestions based on user input.
        """
        pass

    @abstractmethod
    def get_directions(self, origin_lat, origin_lon, dest_lat, dest_lon):
        """
        Gets routing information between two points.
        """
        pass
