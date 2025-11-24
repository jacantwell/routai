import logging

from langchain.tools import tool, ToolRuntime

from app.tools.utils import validate_segments_state

logger = logging.getLogger(__name__)


@tool
def get_segment_details(runtime: ToolRuntime, day_number: int) -> dict:
    """Get detailed information about a specific day's segment.

    Use this to inspect a particular day of the route, including distance,
    elevation, start/end points, and accommodation options.

    Args:
        day_number: Which day to inspect (starting from 1)

    Returns:
        Dictionary with segment details including:
        - day: Day number
        - distance_km: Distance in kilometers
        - elevation_gain_m: Elevation gain in meters
        - origin: Starting coordinates
        - destination: Ending coordinates
        - accommodation_count: Number of accommodation options found
        - has_accommodation: Whether accommodation is available
    """
    segments = validate_segments_state(runtime)

    if day_number < 1 or day_number > len(segments):
        raise ValueError(
            f"Invalid day number {day_number}. Route has {len(segments)} days."
        )

    segment = segments[day_number - 1]

    return {
        "day": segment.day,
        "distance_km": round(segment.route.distance / 1000, 1),
        "elevation_gain_m": segment.route.elevation_gain,
        "origin": {
            "latitude": segment.route.origin.coordinates.latitude,
            "longitude": segment.route.origin.coordinates.longitude,
        },
        "destination": {
            "latitude": segment.route.destination.coordinates.latitude,
            "longitude": segment.route.destination.coordinates.longitude,
        },
        "accommodation_count": len(segment.accommodation_options),
        "has_accommodation": len(segment.accommodation_options) > 0,
        "accommodation_options": [
            acc.model_dump() for acc in segment.accommodation_options
        ],
    }
