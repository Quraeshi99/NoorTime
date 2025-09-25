
import requests
from flask import current_app
from .base_adapter import BaseGeocodingAdapter

class LocationIQAdapter(BaseGeocodingAdapter):
    """
    Geocoding adapter for the LocationIQ API.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://us1.locationiq.com/v1"

    def geocode(self, city_name):
        """
        Fetches location data (lat, lon) for a city name using LocationIQ.
        """
        if not self.api_key:
            current_app.logger.error("Geocoding failed: LocationIQ API key is not configured.")
            return {"error": "Geocoding service is not configured."}

        endpoint = f"{self.base_url}/search.php"
        params = {
            "key": self.api_key,
            "q": city_name,
            "format": "json",
            "limit": 1
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
            
            # LocationIQ provides a detailed address string
            display_name_parts = location.get('display_name', '').split(',')
            country = display_name_parts[-1].strip() if display_name_parts else None
            city = display_name_parts[0].strip() if display_name_parts else city_name

            return {
                "city": city,
                "lat": float(lat),
                "lon": float(lon),
                "country": country
            }
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"LocationIQ geocoding request failed: {e}")
            return {"error": "Failed to connect to geocoding service."}
        except (KeyError, IndexError) as e:
            current_app.logger.error(f"Failed to parse LocationIQ geocoding response: {e}")
            return {"error": "Invalid response from geocoding service."}

    def reverse_geocode(self, lat, lon):
        """
        Performs reverse geocoding (coordinates to address) using LocationIQ.
        Extracts administrative levels.
        """
        if not self.api_key:
            current_app.logger.error("Reverse geocoding failed: LocationIQ API key is not configured.")
            return {"error": "Reverse geocoding service is not configured."}

        endpoint = f"{self.base_url}/reverse.php"
        params = {
            "key": self.api_key,
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 10 # A zoom level that typically returns administrative boundaries
        }

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data or "error" in data:
                error_message = data.get("error", "Unknown error from LocationIQ reverse geocoding.")
                current_app.logger.error(f"LocationIQ reverse geocoding failed: {error_message}")
                return {"error": error_message}

            address = data.get('address', {})
            
            # Extract administrative levels
            country_code = address.get('country_code', '').upper()
            admin_1_name = address.get('state') # Admin Level 1
            admin_2_name = address.get('county') or address.get('state_district') # Admin Level 2
            admin_3_name = address.get('city') or address.get('town') or address.get('village') or address.get('suburb') # Admin Level 3

            return {
                'country_code': country_code,
                'admin_1_name': admin_1_name,
                'admin_2_name': admin_2_name,
                'admin_3_name': admin_3_name,
                'display_name': data.get('display_name')
            }
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"LocationIQ reverse geocoding request failed: {e}")
            return {"error": "Failed to connect to reverse geocoding service."}
        except (KeyError, IndexError) as e:
            current_app.logger.error(f"Failed to parse LocationIQ reverse geocoding response: {e}")
            return {"error": "Invalid response from reverse geocoding service."}

    def autocomplete(self, query):
        """
        Fetches autocomplete suggestions from LocationIQ.
        """
        if not self.api_key:
            return {"error": "Geocoding service is not configured."}

        endpoint = f"{self.base_url}/autocomplete.php"
        params = {
            "key": self.api_key,
            "q": query,
            "limit": 5, # Limit to 5 suggestions
            "format": "json"
        }
        try:
            response = requests.get(endpoint, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"LocationIQ autocomplete request failed: {e}")
            return {"error": "Failed to connect to autocomplete service."}

    def get_directions(self, origin_lat, origin_lon, dest_lat, dest_lon):
        raise NotImplementedError("Directions are not yet implemented for LocationIQ.")
