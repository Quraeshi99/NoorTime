# project/services/api_adapters/islamicfinder_adapter.py

import requests
import datetime
import json
from flask import current_app

class IslamicFinderAdapter:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        current_app.logger.info(f"IslamicFinderAdapter initialized with base_url: {base_url}")

    def fetch_prayer_times(self, date_obj, latitude, longitude, calculation_method_key):
        """
        Fetches prayer times from IslamicFinder API.
        IslamicFinder uses different method IDs. We need to map our keys to theirs.
        """
        # Example mapping (you might need to adjust these based on IslamicFinder's actual IDs)
        # This is a simplified mapping. A more robust solution would involve a comprehensive map
        # or fetching available methods from IslamicFinder API if they provide such an endpoint.
        method_map = {
            "Karachi": 1,  # University of Islamic Sciences, Karachi
            "ISNA": 2,     # Islamic Society of North America
            "MWL": 3,      # Muslim World League
            "Egyptian": 4, # Egyptian General Authority of Survey
            "Makkah": 5,   # Umm Al-Qura University, Makkah
            "Tehran": 7,   # Institute of Geophysics, University of Tehran
            "Jafari": 8,   # Shia Ithna-Ashari
            # Add more mappings as needed
        }
        method_id = method_map.get(calculation_method_key, 3) # Default to MWL if not found

        # IslamicFinder API often requires a specific date format
        date_str = date_obj.strftime("%Y-%m-%d")

        # Construct the API URL and parameters
        # This is a hypothetical endpoint based on common API patterns.
        # You would need to consult IslamicFinder's actual API documentation.
        api_url = f"{self.base_url}/prayertimes"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "date": date_str,
            "method": method_id,
            "format": "json",
            # "key": self.api_key # IslamicFinder might require an API key
        }
        
        # Remove None values from params
        params = {k: v for k, v in params.items() if v is not None}

        current_app.logger.info(f"IslamicFinder: Fetching for {date_str} with method {method_id}")
        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            # Parse and return data in a consistent format (similar to AlAdhan)
            # This parsing logic needs to be adapted based on IslamicFinder's actual response structure
            if data and data.get("code") == 200 and data.get("status") == "OK":
                timings = data["data"]["timings"]
                # Example mapping to AlAdhan-like keys
                return {
                    "Fajr": timings.get("Fajr"),
                    "Sunrise": timings.get("Sunrise"),
                    "Dhuhr": timings.get("Dhuhr"),
                    "Asr": timings.get("Asr"),
                    "Maghrib": timings.get("Maghrib"),
                    "Isha": timings.get("Isha"),
                    "gregorian_date": data["data"]["date"]["gregorian"]["date"],
                    "gregorian_weekday": data["data"]["date"]["gregorian"]["weekday"]["en"],
                    "hijri_date": data["data"]["date"]["hijri"]["date"],
                    "hijri_month_en": data["data"]["date"]["hijri"]["month"]["en"],
                    "hijri_year": data["data"]["date"]["hijri"]["year"],
                    # Add other fields if available and needed
                }
            else:
                current_app.logger.warning(f"IslamicFinder: API returned error or no data: {data.get('status', 'Unknown')}")
                return None
        except requests.exceptions.Timeout:
            current_app.logger.error("IslamicFinder: Request timed out.")
            return None
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"IslamicFinder: Request error: {e}", exc_info=True)
            return None
        except (json.JSONDecodeError, KeyError) as e:
            current_app.logger.error(f"IslamicFinder: JSON parsing or key access error during fetch: {e}", exc_info=True)
            return None
