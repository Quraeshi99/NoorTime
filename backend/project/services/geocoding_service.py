
from flask import current_app
from ..models import GeocodingCache
from .. import db

# Import the adapter classes
from .geocoding_adapters.locationiq_adapter import LocationIQAdapter
from .geocoding_adapters.openweathermap_adapter import OpenWeatherMapAdapter

def get_geocoding_adapter():
    """
    Factory function to get the configured geocoding adapter.
    Reads the provider name and API key from the app config.
    """
    provider = current_app.config.get('GEOCODING_PROVIDER', 'OpenWeatherMap').lower()
    
    if provider == 'locationiq':
        api_key = current_app.config.get('LOCATIONIQ_API_KEY')
        if not api_key:
            raise ValueError("LocationIQ API key is not configured.")
        return LocationIQAdapter(api_key=api_key)
    
    elif provider == 'openweathermap':
        api_key = current_app.config.get('OPENWEATHERMAP_API_KEY')
        if not api_key:
            raise ValueError("OpenWeatherMap API key is not configured.")
        return OpenWeatherMapAdapter(api_key=api_key)
        
    else:
        raise ValueError(f"Unsupported geocoding provider: {provider}")

def get_geocoded_location_with_cache(city_name):
    """
    Fetches location data (lat, lon) for a city name, using a database cache
    to avoid repeated API calls. It uses the adapter selected in the config.
    """
    normalized_city_name = city_name.strip().lower()
    
    # 1. Check cache first
    cached_location = GeocodingCache.query.filter_by(city_name=normalized_city_name).first()
    if cached_location:
        current_app.logger.info(f"Geocoding cache HIT for city: {normalized_city_name}")
        return {
            "city": city_name,
            "lat": cached_location.latitude,
            "lon": cached_location.longitude,
            "country": cached_location.country
        }

    current_app.logger.info(f"Geocoding cache MISS for city: {normalized_city_name}. Calling API.")
    
    try:
        # 2. If not in cache, get the configured adapter and call the API
        adapter = get_geocoding_adapter()
        location_data = adapter.geocode(city_name)

        if location_data and not location_data.get("error"):
            # 3. Save the new location to the cache
            new_cache_entry = GeocodingCache(
                city_name=normalized_city_name,
                latitude=location_data['lat'],
                longitude=location_data['lon'],
                country=location_data['country']
            )
            db.session.add(new_cache_entry)
            db.session.commit()
            current_app.logger.info(f"Successfully cached new geocoding data for city: {normalized_city_name}")
            return location_data
        else:
            return location_data # Return the error from the adapter

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"An unexpected error occurred during geocoding for city: {city_name}: {e}", exc_info=True)
        return {"error": "An unexpected server error occurred."}

def get_autocomplete_suggestions(query):
    """
    Fetches autocomplete suggestions. Caching is not used for autocomplete.
    """
    try:
        adapter = get_geocoding_adapter()
        suggestions = adapter.autocomplete(query)
        return suggestions
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during autocomplete for query: {query}: {e}", exc_info=True)
        return {"error": "An unexpected server error occurred."}


def get_admin_levels_from_coords(latitude, longitude):
    """
    Fetches administrative level data for a given coordinate using the configured geocoding adapter.

    This function uses the reverse geocoding capability of the selected adapter
    to convert coordinates into human-readable administrative boundaries.

    Args:
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.

    Returns:
        dict: A dictionary containing the administrative levels (country_code, admin_1_name, admin_2_name, admin_3_name),
              or None if not found or an error occurs.
    """
    try:
        adapter = get_geocoding_adapter()
        if not hasattr(adapter, 'reverse_geocode'):
            current_app.logger.error(f"Configured geocoding adapter ({adapter.__class__.__name__}) does not support reverse geocoding.")
            return None

        admin_levels_data = adapter.reverse_geocode(latitude, longitude)

        if admin_levels_data and not admin_levels_data.get("error"):
            return {
                'country_code': admin_levels_data.get('country_code'),
                'admin_1_name': admin_levels_data.get('admin_1_name'),
                'admin_2_name': admin_levels_data.get('admin_2_name'),
                'admin_3_name': admin_levels_data.get('admin_3_name')
            }
        else:
            error_msg = admin_levels_data.get("error", "Unknown error during reverse geocoding.") if admin_levels_data else "No data from reverse geocoding."
            current_app.logger.error(f"Failed to get admin levels from reverse geocoding: {error_msg}")
            return None

    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during get_admin_levels_from_coords: {e}", exc_info=True)
        return None

