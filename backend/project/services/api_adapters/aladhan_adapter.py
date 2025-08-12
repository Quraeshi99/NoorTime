# project/services/api_adapters/aladhan_adapter.py

import datetime
import requests
from flask import current_app # To access app.logger and app.config
from .base_adapter import BasePrayerTimeAdapter

class AlAdhanAdapter(BasePrayerTimeAdapter):
    """
    API Adapter for AlAdhan.com Prayer Times API.
    """

    # Mapping from user-friendly keys (stored in UserSettings.default_calculation_method)
    # to AlAdhan API's method ID and Asr juristic method (0=Standard/Shafii, 1=Hanafi)
    # These values should align with AlAdhan API documentation: http://api.aladhan.com/v1/methods
    # This map allows user to select "Hanafi" or "Shafii (Standard)" in UI,
    # and we translate that to correct API parameters.
    METHOD_MAPPING = {
        # User-friendly Key: {"id": AlAdhan_Method_ID, "asr_juristic": 0_or_1, "name_for_api": "API Method Name if needed"}
        "MWL":             {"id": 4, "asr_juristic": 0, "description": "Muslim World League (Standard Asr)"},
        "ISNA":            {"id": 2, "asr_juristic": 0, "description": "Islamic Society of North America (ISNA) (Standard Asr)"},
        "Egyptian":        {"id": 5, "asr_juristic": 0, "description": "Egyptian General Authority of Survey (Standard Asr)"},
        "Makkah":          {"id": 3, "asr_juristic": 0, "description": "Umm al-Qura University, Makkah (Standard Asr) - Note: Some APIs use ID 4 for Makkah like MWL."},
        "Karachi":         {"id": 1, "asr_juristic": 0, "description": "University of Islamic Sciences, Karachi (Standard Asr)"},
        "Tehran":          {"id": 0, "asr_juristic": 0, "description": "Institute of Geophysics, University of Tehran (Standard Asr)"},
        "Jafari":          {"id": 7, "asr_juristic": 0, "description": "Shia Ithna-Ashari (Jafari)"},
        # Specific Hanafi versions often mean using a standard method ID with asr_juristic=1
        "Karachi_Hanafi":  {"id": 1, "asr_juristic": 1, "description": "University of Islamic Sciences, Karachi (Hanafi Asr)"},
        "ISNA_Hanafi":     {"id": 2, "asr_juristic": 1, "description": "ISNA (Hanafi Asr)"}, # Assuming ISNA can be used with Hanafi Asr via param
        # Add more mappings as needed. The key is what's stored in UserSettings.
        # UI should present "Hanafi" and "Shafii/Standard (Maliki, Hanbali)".
        # "Hanafi" can map to "Karachi_Hanafi" or another appropriate one.
        # "Shafii/Standard" can map to "ISNA", "MWL", or "Karachi" (with asr_juristic=0).
    }


    def __init__(self, base_url, api_key=None): # api_key is not used by AlAdhan v1 timings endpoint
        super().__init__(base_url, api_key)
        # AlAdhan specific initializations if any

    def map_calculation_method_key(self, user_selected_method_key):
        """
        Maps a user-friendly key like "Hanafi" or "Shafii_Standard"
        to AlAdhan specific method ID and Asr juristic setting.
        """
        # This is where you define how the user's choice in settings page (e.g., "Hanafi")
        # maps to one of the detailed keys in self.METHOD_MAPPING (e.g., "Karachi_Hanafi")
        if user_selected_method_key == "Hanafi":
            # Default to Karachi with Hanafi Asr for "Hanafi" selection
            return self.METHOD_MAPPING.get("Karachi_Hanafi", {"id": 1, "asr_juristic": 1}) 
        elif user_selected_method_key in ["Shafii", "Maliki", "Hanbali", "Standard", "Shafii_Standard"]:
            # Default to ISNA (or MWL/Karachi) with Standard Asr for others
            return self.METHOD_MAPPING.get("ISNA", {"id": 2, "asr_juristic": 0})
        elif user_selected_method_key in self.METHOD_MAPPING:
            # If the key itself is a direct map (e.g., user chose 'ISNA' from a list of all methods)
            return self.METHOD_MAPPING[user_selected_method_key]
        else:
            # Fallback to a general default if key is unrecognized
            current_app.logger.warning(f"AlAdhanAdapter: Unrecognized calculation_method_key '{user_selected_method_key}'. Falling back to ISNA.")
            return self.METHOD_MAPPING.get("ISNA", {"id": 2, "asr_juristic": 0})


    def fetch_prayer_times(self, date_obj, latitude, longitude, calculation_method_key):
        """
        Fetches prayer times from AlAdhan.com API.
        calculation_method_key is the user's high-level choice (e.g., "Hanafi", "Shafii_Standard")
        """
        date_str = date_obj.strftime("%d-%m-%Y")
        
        # Get API-specific parameters from the user's high-level choice
        api_method_params = self.map_calculation_method_key(calculation_method_key)
        
        method_id = api_method_params.get("id")
        school_param = api_method_params.get("asr_juristic") # For Asr (0 for Standard, 1 for Hanafi)

        # Some APIs might take lat, lon as strings
        lat_str = str(latitude)
        lon_str = str(longitude)

        # Endpoint for timings by date, lat, lon
        # Example: http://api.aladhan.com/v1/timings/DD-MM-YYYY?latitude=X&longitude=Y&method=Z&school=A
        endpoint = f"{self.base_url}/timings/{date_str}"
        params = {
            "latitude": lat_str,
            "longitude": lon_str,
            "method": method_id,
            "school": school_param # Asr juristic method
            # "tune": "0,0,0,0,0,0,0,0,0" # Optional minute adjustments
        }
        current_app.logger.info(f"AlAdhanAdapter: Fetching times for {date_str} with params: {params}")

        try:
            response = requests.get(endpoint, params=params, timeout=15)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            data = response.json()

            if data.get("code") == 200 and "data" in data:
                timings = data["data"]["timings"]
                date_info_api = data["data"]["date"]
                
                dhuhr_time_obj = datetime.datetime.strptime(timings.get("Dhuhr", "00:00"), "%H:%M")
                zawal_start_approx = (dhuhr_time_obj - datetime.timedelta(minutes=10)).strftime("%H:%M")

                # Standardized output format (must match BasePrayerTimeAdapter docstring)
                standardized_data = {
                    "Fajr": timings.get("Fajr"), "Sunrise": timings.get("Sunrise"),
                    "Dhuhr": timings.get("Dhuhr"), "Asr": timings.get("Asr"),
                    "Sunset": timings.get("Sunset"), "Maghrib": timings.get("Maghrib"),
                    "Isha": timings.get("Isha"), "Imsak": timings.get("Imsak"),
                    "Midnight": timings.get("Midnight"), # AlAdhan provides Midnight
                    "Zawal_Start_Approx": zawal_start_approx,
                    "Zawal_End_Approx": timings.get("Dhuhr"),
                    
                    "gregorian_date": date_info_api["gregorian"]["date"],
                    "gregorian_weekday": date_info_api["gregorian"]["weekday"]["en"],
                    "gregorian_month": date_info_api["gregorian"]["month"]["en"],
                    "gregorian_year": date_info_api["gregorian"]["year"],

                    "hijri_date": date_info_api["hijri"]["date"],
                    "hijri_weekday": date_info_api["hijri"]["weekday"]["en"],
                    "hijri_month_en": date_info_api["hijri"]["month"]["en"],
                    "hijri_month_ar": date_info_api["hijri"]["month"]["ar"],
                    "hijri_year": date_info_api["hijri"]["year"],

                    # Attempt to get temperature from another API if needed (not part of AlAdhan)
                    # For now, these will be None.
                    "temperatureC": None, 
                    "weather_description": None
                }
                current_app.logger.info(f"AlAdhanAdapter: Successfully fetched times for {date_str}")
                return standardized_data
            else:
                current_app.logger.error(f"AlAdhanAdapter: API error for {date_str} - Code: {data.get('code')}, Status: {data.get('status')}")
                return None
        except requests.exceptions.Timeout:
            current_app.logger.error(f"AlAdhanAdapter: Timeout error fetching prayer times for {date_str}.")
            return None
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"AlAdhanAdapter: RequestException for {date_str}: {e}", exc_info=True)
            return None
        except Exception as e:
            current_app.logger.error(f"AlAdhanAdapter: Unexpected error for {date_str}: {e}", exc_info=True)
            return None

# You can add other adapter classes here for different APIs in the future,
# e.g., MuslimSalatAdapter, IslamicFinderAdapter, etc.