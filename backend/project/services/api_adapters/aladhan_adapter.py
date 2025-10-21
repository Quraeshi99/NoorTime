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

    def fetch_daily_timings(self, date_obj, latitude, longitude, method_id, asr_juristic_id, high_latitude_method_id):
        """
        Fetches prayer times for a single day from the AlAdhan.com API.
        """
        date_str = date_obj.strftime("%d-%m-%Y")
        current_app.logger.info(f"AlAdhanAdapter: Fetching daily timings for {date_str} at ({latitude}, {longitude})")

        endpoint = f"{self.base_url}/timings/{date_str}"
        params = {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "method": method_id,
            "school": asr_juristic_id,
            "latitudeAdjustmentMethod": high_latitude_method_id,
        }
        
        current_app.logger.debug(f"AlAdhanAdapter: Fetching daily with params: {params}")

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 200 and "data" in data:
                current_app.logger.info(f"AlAdhanAdapter: Successfully fetched daily timings for {date_str}.")
                # The daily endpoint returns a slightly different structure
                # We need to return the 'timings' dictionary
                return data["data"]
            else:
                current_app.logger.error(f"AlAdhanAdapter: API error for daily timings {date_str}. Code: {data.get('code')}, Status: {data.get('status')}")
                return None

        except requests.exceptions.Timeout:
            current_app.logger.error(f"AlAdhanAdapter: Timeout error fetching daily prayer times for {date_str}.")
            return None
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"AlAdhanAdapter: RequestException for daily timings {date_str}: {e}", exc_info=True)
            return None
        except Exception as e:
            current_app.logger.error(f"AlAdhanAdapter: Unexpected error for daily timings {date_str}: {e}", exc_info=True)
            return None

    def fetch_yearly_calendar(self, year, latitude, longitude, method_id, asr_juristic_id, high_latitude_method_id):
        """
        Fetches a full year's prayer time calendar from the AlAdhan.com API.
        """
        current_app.logger.info(f"AlAdhanAdapter: Fetching yearly calendar for {year} at ({latitude}, {longitude}) with method:{method_id}, asr:{asr_juristic_id}, high_lat:{high_latitude_method_id}")

        endpoint = f"{self.base_url}/calendar"
        
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
