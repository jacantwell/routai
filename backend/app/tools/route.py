from langchain.tools import tool
from pydantic_extra_types.coordinate import  Coordinate
import requests

from app.config.config import settings

GOOGLE_ROUTES_API_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
GOOGLE_GEOCODING_API_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

@tool
def get_location(place_name: str) -> Coordinate:
    """Convert a place name to a coordinates object using Google Geocoding API.

    Args:
        place_name: The name of a place, e.g Amsterdam

    Returns:
        Coordinate: A Coordinate object with latitude and longitude

    Raises:
        ValueError: If the place cannot be found or API request fails
    """
    params = {"address": place_name, "key": settings.GOOGLE_API_KEY}

    try:
        response = requests.get(GOOGLE_GEOCODING_API_ENDPOINT, params=params)
        response.raise_for_status()

        data = response.json()

        if data["status"] != "OK" or not data.get("results"):
            raise ValueError(
                f"Could not find location: {place_name}. Status: {data['status']}"
            )

        # Get the first result
        location = data["results"][0]["geometry"]["location"]

        return Coordinate(latitude=location["lat"], longitude=location["lng"])

    except requests.RequestException as e:
        raise ValueError(f"Failed to geocode location '{place_name}': {str(e)}")
