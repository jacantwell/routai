import logging
from typing import Any, Dict, List

from app.models import AgentState, Segment
from app.utils import calculate_segments, fetch_route

logger = logging.getLogger(__name__)


def calculate_route_node(state: AgentState) -> Dict[str, Any]:
    """Calculate the route based on validated requirements.

    This node uses the Google Routes API to calculate the optimal
    route between origin and destination, including any intermediate stops.

    Args:
        state: Current agent state with requirements

    Returns:
        Dictionary with calculated route

    Raises:
        ValueError: If requirements are missing
        RuntimeError: If route calculation fails
    """
    requirements = state.requirements

    if not requirements:
        error_msg = "Route calculation requires validated requirements"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(
        f"Calculating route: {requirements.origin.name} -> "
        f"{requirements.destination.name}"
    )

    if requirements.intermediates:
        intermediate_names = [loc.name for loc in requirements.intermediates]
        logger.info(f"Intermediate stops: {', '.join(intermediate_names)}")

    # Extract coordinates for API call
    intermediate_coords = [point.coordinates for point in requirements.intermediates]

    try:
        route = fetch_route(
            origin=requirements.origin.coordinates,
            destination=requirements.destination.coordinates,
            intermediates=intermediate_coords,
        )

        logger.info(f"Route calculated successfully: {route.distance / 1000:.2f} km")

        return {"route": route}

    except Exception as e:
        error_msg = f"Route calculation failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def calculate_segments_node(state: AgentState) -> Dict[str, Any]:
    """Generate daily segments along the calculated route.

    This node divides the route into daily segments based on the
    user's target daily distance.

    Args:
        state: Current agent state with route and requirements

    Returns:
        Dictionary with generated segments

    Raises:
        ValueError: If route or requirements are missing
        RuntimeError: If segment generation fails
    """
    route = state.route
    requirements = state.requirements

    if not route:
        error_msg = "Segment generation requires a calculated route"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not requirements:
        error_msg = "Segment generation requires validated requirements"
        logger.error(error_msg)
        raise ValueError(error_msg)

    daily_distance_m = requirements.daily_distance_km * 1000

    logger.info(
        f"Generating segments for {requirements.daily_distance_km}km/day target "
        f"(total distance: {route.distance / 1000:.2f}km)"
    )

    try:
        segments: List[Segment] = calculate_segments(route.polyline, daily_distance_m)

        logger.info(f"Generated {len(segments)} segments")

        return {"segments": segments}

    except Exception as e:
        error_msg = f"Segment generation failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
