# project/services/api_adapters/aladhan_adapter.py

import datetime
import requests
from flask import current_app # To access app.logger and app.config
from .base_adapter import BasePrayerTimeAdapter

class AlAdhanAdapter(BasePrayerTimeAdapter):
    """
    API Adapter for AlAdhan.com Prayer Times API.
    """

    def __init__(self, base_url, api_key=None):
        super().__init__(base_url, api_key)

    def fetch_yearly_calendar(self, year, latitude, longitude, method_id, asr_juristic_id, high_latitude_method_id):
        """
        Fetches a full year's prayer time calendar from the AlAdhan.com API.

        This function is updated to accept granular settings for calculation method,
        Asr juristic preference, and high-latitude adjustments, providing full
        flexibility as per the application's requirements.

        Args:
            year (int): The calendar year.
            latitude (float): The latitude of the location.
            longitude (float): The longitude of the location.
            method_id (int): The ID of the calculation method (e.g., 3 for MWL).
            asr_juristic_id (int): The school for Asr calculation (0 for Standard, 1 for Hanafi).
            high_latitude_method_id (int): The adjustment rule for high latitudes.

        Returns:
            list: A list of daily prayer time data for the year, or None on error.
        """
        current_app.logger.info(f"AlAdhanAdapter: Fetching yearly calendar for {year} at ({latitude}, {longitude}) with method:{method_id}, asr:{asr_juristic_id}, high_lat:{high_latitude_method_id}")

        endpoint = f"{self.base_url}/calendar"
        
        # Prepare parameters for the AlAdhan API call.
        # This now includes the new flexibility options.
        params = {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "method": method_id,
            "school": asr_juristic_id,
            "latitudeAdjustmentMethod": high_latitude_method_id,
            "year": year
        }
        
        current_app.logger.debug(f"AlAdhanAdapter: Fetching full year with params: {params}")

        try:
            # Using a longer timeout for a large annual data request.
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 200 and "data" in data and isinstance(data["data"], dict):
                # The API returns a dictionary with month numbers as keys.
                # We need to flatten this into a single list of daily objects.
                full_year_data = []
                for month_key in sorted(data["data"].keys(), key=int):
                    full_year_data.extend(data["data"][month_key])
                
                if not full_year_data:
                    current_app.logger.error(f"AlAdhanAdapter: API returned empty data for year {year}.")
                    return None

                current_app.logger.info(f"AlAdhanAdapter: Successfully fetched and processed full yearly calendar for {year}.")
                return full_year_data
            else:
                current_app.logger.error(f"AlAdhanAdapter: API error for year {year}. Code: {data.get('code')}, Status: {data.get('status')}")
                return None

        except requests.exceptions.Timeout:
            current_app.logger.error(f"AlAdhanAdapter: Timeout error fetching yearly prayer times for {year}.")
            return None
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"AlAdhanAdapter: RequestException for year {year}: {e}", exc_info=True)
            return None
        except Exception as e:
            current_app.logger.error(f"AlAdhanAdapter: Unexpected error for year {year}: {e}", exc_info=True)
            return None
        
        current_app.logger.debug(f"AlAdhanAdapter: Fetching full year with params: {params}")

        try:
            # Using a longer timeout for a large annual data request.
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 200 and "data" in data and isinstance(data["data"], dict):
                # The API returns a dictionary with month numbers as keys.
                # We need to flatten this into a single list of daily objects.
                full_year_data = []
                for month_key in sorted(data["data"].keys(), key=int):
                    full_year_data.extend(data["data"][month_key])
                
                if not full_year_data:
                    current_app.logger.error(f"AlAdhanAdapter: API returned empty data for year {year}.")
                    return None

                current_app.logger.info(f"AlAdhanAdapter: Successfully fetched and processed full yearly calendar for {year}.")
                return full_year_data
            else:
                current_app.logger.error(f"AlAdhanAdapter: API error for year {year}. Code: {data.get('code')}, Status: {data.get('status')}")
                return None

        except requests.exceptions.Timeout:
            current_app.logger.error(f"AlAdhanAdapter: Timeout error fetching yearly prayer times for {year}.")
            return None
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"AlAdhanAdapter: RequestException for year {year}: {e}", exc_info=True)
            return None
        except Exception as e:
            current_app.logger.error(f"AlAdhanAdapter: Unexpected error for year {year}: {e}", exc_info=True)
            return None


# You can add other adapter classes here for different APIs in the future,
# e.g., MuslimSalatAdapter, IslamicFinderAdapter, etc.
