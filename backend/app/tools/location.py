import logging

from langchain.tools import tool
from pydantic_extra_types.coordinate import Coordinate

from app.tools.utils import geocode_location

logger = logging.getLogger(__name__)


@tool
def get_location(place_name: str) -> Coordinate:
    """Convert a place name to coordinates using Google Geocoding API.

    Use this tool to get the coordinates of any city, town, landmark, or address.

    Examples:
        - "Amsterdam, Netherlands"
        - "Eiffel Tower, Paris"
        - "Lake District, UK"

    Args:
        place_name: The name of a place, city, or address

    Returns:
        Coordinate object with latitude and longitude

    Raises:
        ValueError: If the place cannot be found
    """
    return geocode_location(place_name)
