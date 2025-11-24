import logging
from typing import Sequence

from langchain.tools import ToolRuntime
from pydantic_extra_types.coordinate import Coordinate
import requests

from app.config import settings
from app.models import AgentState, RouteRequirements, Location, Route, Segment
from app.utils import calculate_segments, get_accommodation

logger = logging.getLogger(__name__)


def validate_route_state(runtime: ToolRuntime) -> tuple[Route, RouteRequirements]:
    """Extract and validate route state from runtime.

    Args:
        runtime: LangGraph tool runtime with state access

    Returns:
        Tuple of (route, requirements)

    Raises:
        ValueError: If route or requirements are missing from state
    """

    state: AgentState = runtime.state  # type: ignore
    route = state.route
    requirements = state.requirements

    if not route:
        raise ValueError("Route calculation required. No route found in state.")
    if not requirements:
        raise ValueError(
            "Requirements validation required. No requirements found in state."
        )

    return route, requirements


def validate_segments_state(runtime: ToolRuntime) -> list[Segment]:
    """Extract and validate segments from runtime state.

    Args:
        runtime: LangGraph tool runtime with state access

    Returns:
        List of route segments

    Raises:
        ValueError: If segments are missing from state
    """
    state: AgentState = runtime.state  # type: ignore
    segments = state.segments

    if not segments:
        raise ValueError("Segment generation required. No segments found in state.")

    return segments


def geocode_location(place_name: str) -> Coordinate:
    """Convert a place name to coordinates using Google Geocoding API.

    Args:
        place_name: Name of the place to geocode

    Returns:
        Coordinate object with latitude and longitude

    Raises:
        ValueError: If geocoding fails
    """
    params = {"address": place_name, "key": settings.GOOGLE_API_KEY}

    try:
        response = requests.get(settings.GOOGLE_GEOCODING_API_ENDPOINT, params=params)
        response.raise_for_status()

        data = response.json()

        if data["status"] != "OK" or not data.get("results"):
            raise ValueError(
                f"Could not find location: {place_name}. Status: {data['status']}"
            )

        location = data["results"][0]["geometry"]["location"]
        return Coordinate(latitude=location["lat"], longitude=location["lng"])

    except requests.RequestException as e:
        raise ValueError(f"Failed to geocode location '{place_name}': {str(e)}")


def convert_place_names_to_locations(place_names: Sequence[str]) -> list[Location]:
    """Convert a list of place names to Location objects with coordinates.

    Args:
        place_names: List of place names to geocode

    Returns:
        List of Location objects with coordinates

    Raises:
        ValueError: If any place name cannot be geocoded
    """
    locations = []

    for place_name in place_names:
        try:
            coords = geocode_location(place_name)
            location = Location(name=place_name, coordinates=coords)
            locations.append(location)
        except Exception as e:
            raise ValueError(f"Failed to geocode '{place_name}': {str(e)}")

    return locations


def recalculate_segments_with_accommodation(
    route: Route, daily_distance_km: int, accommodation_radius_km: int = 5
) -> list[Segment]:
    """Calculate route segments and find accommodation for each endpoint.

    This is a pure function that takes a route and returns segments with
    accommodation options populated.

    Args:
        route: The route to divide into segments
        daily_distance_km: Target distance per day in kilometers
        accommodation_radius_km: Search radius for accommodation in kilometers

    Returns:
        List of segments with accommodation options
    """
    logger.info(f"Calculating segments with {daily_distance_km}km daily distance")

    # Calculate segments based on daily distance
    segments = calculate_segments(
        route.polyline, daily_distance_km * 1000, route.origin, route.destination
    )

    # Find accommodation for each segment endpoint
    for segment in segments:
        logger.debug(f"Searching accommodation for day {segment.day}")
        try:
            accommodation_options = get_accommodation(
                segment.route.destination.coordinates, radius=accommodation_radius_km
            )
            segment.accommodation_options = accommodation_options
        except Exception as e:
            logger.error(f"Failed to find accommodation for day {segment.day}: {e}")
            segment.accommodation_options = []

    logger.info(f"Generated {len(segments)} segments with accommodation data")
    return segments
