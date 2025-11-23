import logging

from langchain.tools import tool, ToolRuntime

from app.models.models import Accommodation
from app.utils.utils import get_accommodation
from app.tools.utils import validate_segments_state, geocode_location

logger = logging.getLogger(__name__)


@tool
def find_accommodation_at_location(
    place_name: str, radius_km: int = 5
) -> list[Accommodation]:
    """Find accommodation options near a specific location.

    Use this to search for hotels, hostels, and lodging near any place.

    Args:
        place_name: Name of the location to search near (e.g., "Lyon, France")
        radius_km: Search radius in kilometers (default: 5km)

    Returns:
        List of accommodation options with names, addresses, ratings, and map links
    """
    coords = geocode_location(place_name)
    return get_accommodation(coords, radius=radius_km)


@tool
def search_accommodation_for_day(
    runtime: ToolRuntime, day_number: int, search_radius_km: int = 10
) -> list[Accommodation]:
    """Search for accommodation near a specific day's endpoint with custom radius.

    Use this when a day lacks accommodation options. Increasing the search
    radius can help find options in nearby towns.

    Args:
        day_number: Which day to search accommodation for (starting from 1)
        search_radius_km: Search radius in kilometers (default: 10km)

    Returns:
        List of accommodation options found within the radius
    """
    segments = validate_segments_state(runtime)

    if day_number < 1 or day_number > len(segments):
        raise ValueError(
            f"Invalid day number {day_number}. Route has {len(segments)} days."
        )

    segment = segments[day_number - 1]

    logger.info(
        f"Searching accommodation for day {day_number} with {search_radius_km}km radius"
    )

    accommodation = get_accommodation(
        segment.route.destination, radius=search_radius_km
    )

    return accommodation
