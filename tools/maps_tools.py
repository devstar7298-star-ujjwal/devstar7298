import os
import requests
import logging

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())

MAPS_API_KEY = os.environ.get("MAPS_API_KEY")

def get_geocode_and_place_id(address: str) -> dict:
    """
    Tool to get geographic coordinates (lat/lon) and a Place ID for a given address using Google Geocoding API.
    """
    if not MAPS_API_KEY:
        logging.error("MAPS_API_KEY environment variable not set in get_geocode_and_place_id.")
        return {"error": "MAPS_API_KEY environment variable not set."}

    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={MAPS_API_KEY}"
    try:
        logging.info(f"Calling Geocoding API for address: {address[:50]}...")
        response = requests.get(geocode_url, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if data["status"] == "OK" and data["results"]:
            location = data["results"][0]["geometry"]["location"]
            place_id = data["results"][0]["place_id"]
            formatted_address = data["results"][0]["formatted_address"]
            
            # Extract components for demographics and comparables
            city, state, zip_code = None, None, None
            for component in data['results'][0]['address_components']:
                if 'locality' in component['types']:
                    city = component['long_name']
                if 'administrative_area_level_1' in component['types']: # e.g., CA, NY
                    state = component['short_name'] # Use short_name for state abbreviations
                if 'postal_code' in component['types']:
                    zip_code = component['long_name']

            logging.info(f"Geocoding successful for {address}. Lat: {location['lat']}, Lng: {location['lng']}")
            return {
                "latitude": location["lat"],
                "longitude": location["lng"],
                "place_id": place_id,
                "formatted_address": formatted_address,
                "city": city,
                "state": state,
                "zip_code": zip_code
            }
        logging.warning(f"Geocoding API status: {data.get('status')}. Message: {data.get('error_message')}. Address: {address}")
        return {"error": f"Could not geocode address: {address}. Status: {data.get('status')}."}
    except requests.exceptions.Timeout:
        logging.error(f"Geocoding API request timed out for address: {address}")
        return {"error": f"Geocoding API request timed out for address: {address}."}
    except requests.exceptions.RequestException as e:
        logging.error(f"Geocoding API request failed for address '{address}': {e}")
        return {"error": f"Geocoding API request failed: {e}."}
    except Exception as e:
        logging.error(f"An unexpected error occurred during geocoding for '{address}': {e}", exc_info=True)
        return {"error": f"An unexpected error occurred during geocoding: {e}."}

def get_aerial_view_insights(latitude: float, longitude: float) -> dict:
    """
    Conceptual tool to get aerial view insights. For a hackathon, this provides a link.
    Actual Aerial View API integration for property features (roof type, solar potential) is complex.
    """
    if not MAPS_API_KEY:
        logging.error("MAPS_API_KEY environment variable not set in get_aerial_view_insights.")
        return {"error": "MAPS_API_KEY environment variable not set."}

    logging.info(f"Getting conceptual aerial view insights for Lat: {latitude}, Lng: {longitude}")
    
    # Generate a Google Maps link for visual inspection
    map_link = f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
    
    # You could integrate with Solar API, Photorealistic 3D Tiles, or Street View Static API here.
    # For hackathon, the conceptual output is fine.
    return {
        "aerial_view_summary": "Access detailed aerial imagery and potential insights like roof geometry, solar panel suitability, or building footprints. Full API integration (e.g., Solar API, 3D Tiles) is complex and beyond hackathon scope for detailed feature extraction.",
        "visual_inspection_link": map_link
    }
