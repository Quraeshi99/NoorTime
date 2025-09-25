
import requests
from flask import current_app
from .base_adapter import BaseGeocodingAdapter

class OpenWeatherMapAdapter(BaseGeocodingAdapter):
    """
    Geocoding adapter for the OpenWeatherMap API.
    This encapsulates the original geocoding logic.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/geo/1.0"

    def geocode(self, city_name):
        """
        Fetches location data (lat, lon) for a city name using OpenWeatherMap.
        """
        if not self.api_key:
            current_app.logger.error("Geocoding failed: OpenWeatherMap API key is not configured.")
            return {"error": "Geocoding service is not configured."}

        endpoint = f"{self.base_url}/direct"
        params = {
            "q": city_name,
            "limit": 1,
            "appid": self.api_key
        }

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data:
                return {"error": "City not found."}

            location = data[0]
            lat = location.get('lat')
            lon = location.get('lon')
            country = location.get('country')
            city = location.get('name', city_name)

            return {
                "city": city,
                "lat": lat,
                "lon": lon,
                "country": country
            }
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"OpenWeatherMap geocoding request failed: {e}")
            return {"error": "Failed to connect to geocoding service."}
        except (KeyError, IndexError) as e:
            current_app.logger.error(f"Failed to parse OpenWeatherMap geocoding response: {e}")
            return {"error": "Invalid response from geocoding service."}

    def reverse_geocode(self, lat, lon):
        raise NotImplementedError("Reverse geocoding is not implemented for OpenWeatherMap in this adapter.")

    def autocomplete(self, query):
        raise NotImplementedError("Autocomplete is not implemented for OpenWeatherMap.")

    def get_directions(self, origin_lat, origin_lon, dest_lat, dest_lon):
        raise NotImplementedError("Directions are not implemented for OpenWeatherMap.")
