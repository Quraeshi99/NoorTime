# This module will contain all functions related to interacting with the prayer time API.
from flask import current_app # To access app.logger and app.config
from .base_adapter import BasePrayerAdapter
from typing import Dict, Any, Optional, List

class AlAdhanAdapter(BasePrayerAdapter):
    """
    API Adapter for AlAdhan.com Prayer Times API.
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        super().__init__(base_url, api_key)

    def fetch_daily_timings(self, date_obj: datetime.date, latitude: float, longitude: float, method_id: int, asr_juristic_id: int, high_latitude_method_id: int) -> Optional[Dict[str, Any]]:
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
                raw_data = data["data"]
                return {
                    "date": raw_data.get("date", {}).get("gregorian", {}).get("date"),
                    "timings": raw_data.get("timings", {})
                }
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

    def fetch_yearly_calendar(self, year: int, latitude: float, longitude: float, method_id: int, asr_juristic_id: int, high_latitude_method_id: int) -> Optional[List[Dict[str, Any]]]:
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
                    for day_data in data["data"][month_key]:
                        full_year_data.append({
                            "date": day_data.get("date", {}).get("gregorian", {}).get("date"),
                            "timings": day_data.get("timings", {})
                        })
                
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

def get_selected_api_adapter():
    """
    Instantiates and returns the API adapter based on configuration.
    """
    adapter_name = current_app.config.get('PRAYER_API_ADAPTER', "AlAdhanAdapter")
    base_url = current_app.config.get('PRAYER_API_BASE_URL')
    api_key = current_app.config.get('PRAYER_API_KEY')

    if adapter_name == "AlAdhanAdapter":
        if not base_url:
            current_app.logger.error("AlAdhan API base URL is not configured.")
            return None
        from ...api_adapters.aladhan_adapter import AlAdhanAdapter
        return AlAdhanAdapter(base_url=base_url, api_key=api_key)
    else:
        current_app.logger.error(f"Unsupported Prayer API Adapter: {adapter_name}")
        return None

def get_daily_prayer_times_from_api(date_obj, latitude, longitude, method_id, asr_juristic_id, high_latitude_method_id):
    """
    Fetches prayer times for a single day directly from the API adapter.
    This is used for the 'instant gratification' part of the hybrid cache strategy.
    """
    adapter = get_selected_api_adapter()
    if not adapter:
        return None
    
    try:
        # Call the new daily fetch method on the adapter
        daily_data = adapter.fetch_daily_timings(
            date_obj=date_obj,
            latitude=latitude,
            longitude=longitude,
            method_id=method_id,
            asr_juristic_id=asr_juristic_id,
            high_latitude_method_id=high_latitude_method_id
        )
        return daily_data
    except Exception as e:
        current_app.logger.error(f"Exception during single-day API fetch: {e}", exc_info=True)
        return None
