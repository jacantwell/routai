import logging
from typing import Optional, Sequence

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from app.models import Location
from app.tools.utils import (
    convert_place_names_to_locations,
    geocode_location,
    recalculate_segments_with_accommodation,
    validate_route_state,
    validate_segments_state,
)
from app.utils import fetch_route

logger = logging.getLogger(__name__)


@tool
def confirm_route(runtime: ToolRuntime) -> Command:
    """Signal that the route is ready and user has confirmed.

    Use this tool when:
    - User explicitly confirms the route overview is suitable (e.g., "yes", "looks good", "generate itinerary")
    """

    return Command(
        update={
            "user_confirmed": True,
            "messages": [
                ToolMessage(
                    content="Route confirmed. Proceeding to generate detailed itinerary.",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


@tool
def get_route_summary(runtime: ToolRuntime) -> dict:
    """Get an overview of the entire route.

    Use this to understand the current route configuration, including
    total distance, number of days, and accommodation availability.

    Returns:
        Dictionary with route summary including:
        - total_distance_km: Total route distance
        - total_elevation_gain_m: Total elevation gain
        - num_days: Number of daily segments
        - avg_distance_km: Average daily distance
        - days_with_accommodation: Number of days with accommodation found
        - days_without_accommodation: List of day numbers lacking accommodation
    """
    route, requirements = validate_route_state(runtime)
    segments = validate_segments_state(runtime)

    days_without_accommodation = [
        seg.day for seg in segments if len(seg.accommodation_options) == 0
    ]

    total_elevation = sum(seg.route.elevation_gain for seg in segments)

    return {
        "total_distance_km": round(route.distance / 1000, 1),
        "total_elevation_gain_m": total_elevation,
        "num_days": len(segments),
        "avg_distance_km": round(route.distance / 1000 / len(segments), 1),
        "target_daily_distance_km": requirements.daily_distance_km,
        "days_with_accommodation": len(segments) - len(days_without_accommodation),
        "days_without_accommodation": days_without_accommodation,
        "origin": requirements.origin.name,
        "destination": requirements.destination.name,
        "num_intermediates": len(requirements.intermediates),
    }


@tool
def adjust_daily_distance(runtime: ToolRuntime, new_daily_distance_km: int) -> Command:
    """Adjust the target daily cycling distance and recalculate all segments.

    Use this when segments are too long or too short. Decreasing the daily
    distance creates more, shorter days. Increasing it creates fewer, longer days.
    This can help ensure accommodation is available at each stop.

    Args:
        new_daily_distance_km: New target distance per day in kilometers

    Returns:
        Command to update segments in state

    Example:
        If days are 120km but accommodation is sparse, try 80km to create
        more stopping points in towns along the route.
    """
    route, requirements = validate_route_state(runtime)

    logger.info(
        f"Adjusting daily distance from {requirements.daily_distance_km}km "
        f"to {new_daily_distance_km}km"
    )

    if new_daily_distance_km < 20 or new_daily_distance_km > 200:
        raise ValueError(
            "Daily distance must be between 20km and 200km. "
            f"Got: {new_daily_distance_km}km"
        )

    # Recalculate segments with new daily distance
    new_segments = recalculate_segments_with_accommodation(route, new_daily_distance_km)

    # Update requirements with new daily distance
    updated_requirements = requirements.model_copy(
        update={"daily_distance_km": new_daily_distance_km}
    )

    return Command(
        update={
            "segments": new_segments,
            "requirements": updated_requirements,
            "messages": [
                ToolMessage(
                    content="New daily distance set.", tool_call_id=runtime.tool_call_id
                )
            ],
        }
    )


@tool
def add_intermediate_waypoint(
    runtime: ToolRuntime, waypoint_name: str, insert_position: Optional[int] = None
) -> Command:
    """Add a waypoint to force the route through a specific location.

    Use this to redirect the route through towns or cities that have
    accommodation. The waypoint will be added to the route and all
    segments will be recalculated.

    Args:
        waypoint_name: Place name to route through (e.g., "Toulouse, France")
        insert_position: Optional position in waypoint list (0-indexed).
                        If not provided, adds at the end.

    Returns:
        Command to update route, segments, and requirements in state

    Example:
        If day 3 has no accommodation but "Lyon" is nearby, add Lyon as
        a waypoint to ensure the route passes through the city.
    """
    route, requirements = validate_route_state(runtime)

    logger.info(f"Adding intermediate waypoint: {waypoint_name}")

    # Geocode the waypoint
    try:
        waypoint_coords = geocode_location(waypoint_name)
    except Exception as e:
        raise ValueError(f"Failed to add waypoint '{waypoint_name}': {str(e)}")

    waypoint_location = Location(name=waypoint_name, coordinates=waypoint_coords)

    # Insert waypoint at specified position or append to end
    new_intermediates = requirements.intermediates.copy()
    if insert_position is not None:
        if insert_position < 0 or insert_position > len(new_intermediates):
            raise ValueError(
                f"Insert position {insert_position} out of range. "
                f"Must be between 0 and {len(new_intermediates)}"
            )
        new_intermediates.insert(insert_position, waypoint_location)
    else:
        new_intermediates.append(waypoint_location)

    try:
        new_route = fetch_route(route.origin, route.destination, new_intermediates)
    except Exception as e:
        raise ValueError(f"Failed to recalculate route with new waypoint: {str(e)}")

    # Recalculate segments
    new_segments = recalculate_segments_with_accommodation(
        new_route, requirements.daily_distance_km
    )

    # Update requirements
    updated_requirements = requirements.model_copy(
        update={"intermediates": new_intermediates}
    )

    logger.info(
        f"Successfully added waypoint. Route now has {len(new_intermediates)} intermediates"
    )

    return Command(
        update={
            "route": new_route,
            "segments": new_segments,
            "requirements": updated_requirements,
            "messages": [
                ToolMessage(
                    content="Waypoint added.", tool_call_id=runtime.tool_call_id
                )
            ],
        }
    )


@tool
def remove_intermediate_waypoint(runtime: ToolRuntime, waypoint_index: int) -> Command:
    """Remove a waypoint from the route by its position.

    Use this to undo a waypoint addition or simplify the route.
    All segments will be recalculated after removal.

    Args:
        waypoint_index: Position of waypoint to remove (0-indexed)

    Returns:
        Command to update route, segments, and requirements in state
    """
    route, requirements = validate_route_state(runtime)

    if not requirements.intermediates:
        raise ValueError("No intermediate waypoints to remove")

    if waypoint_index < 0 or waypoint_index >= len(requirements.intermediates):
        raise ValueError(
            f"Invalid waypoint index {waypoint_index}. "
            f"Must be between 0 and {len(requirements.intermediates) - 1}"
        )

    removed_waypoint = requirements.intermediates[waypoint_index]
    logger.info(f"Removing intermediate waypoint: {removed_waypoint.name}")

    # Remove waypoint
    new_intermediates = requirements.intermediates.copy()
    new_intermediates.pop(waypoint_index)

    try:
        new_route = fetch_route(route.origin, route.destination, new_intermediates)
    except Exception as e:
        raise ValueError(f"Failed to recalculate route after removal: {str(e)}")

    # Recalculate segments
    new_segments = recalculate_segments_with_accommodation(
        new_route, requirements.daily_distance_km
    )

    # Update requirements
    updated_requirements = requirements.model_copy(
        update={"intermediates": new_intermediates}
    )

    logger.info(
        f"Successfully removed waypoint. Route now has {len(new_intermediates)} intermediates"
    )

    return Command(
        update={
            "route": new_route,
            "segments": new_segments,
            "requirements": updated_requirements,
            "messages": [
                ToolMessage(
                    content="Waypoint removed.", tool_call_id=runtime.tool_call_id
                )
            ],
        }
    )


@tool
def recalculate_complete_route(
    runtime: ToolRuntime,
    new_origin: Optional[str] = None,
    new_destination: Optional[str] = None,
    intermediate_names: Sequence[str] = (),
) -> Command:
    """Completely recalculate the route with new start, end, or waypoints.

    Use this for major route changes. If you only need to adjust one aspect,
    consider using more specific tools like add_intermediate_waypoint or
    adjust_daily_distance instead.

    Args:
        new_origin: Place name for new starting point (e.g., "Amsterdam")
        new_destination: Place name for new endpoint (e.g., "Berlin")
        intermediate_names: List of places to route through in order

    Returns:
        Command to update route, segments, and requirements in state

    Example:
        recalculate_complete_route(
            new_origin="Paris, France",
            new_destination="Barcelona, Spain",
            intermediate_names=["Lyon", "Toulouse"]
        )
    """
    _, requirements = validate_route_state(runtime)

    logger.info("Recalculating complete route")

    # Determine origin (use new or existing)
    if new_origin:
        try:
            origin_coords = geocode_location(new_origin)
            origin_location = Location(name=new_origin, coordinates=origin_coords)
        except Exception as e:
            raise ValueError(f"Failed to geocode new origin: {str(e)}")
    else:
        origin_location = requirements.origin
        origin_coords = origin_location.coordinates

    if new_destination:
        try:
            destination_coords = geocode_location(new_destination)
            destination_location = Location(
                name=new_destination, coordinates=destination_coords
            )
        except Exception as e:
            raise ValueError(f"Failed to geocode new destination: {str(e)}")
    else:
        destination_location = requirements.destination
        destination_coords = destination_location.coordinates

    if intermediate_names:
        try:
            intermediates = convert_place_names_to_locations(intermediate_names)
        except Exception as e:
            raise ValueError(f"Failed to geocode intermediates: {str(e)}")
    else:
        intermediates = requirements.intermediates

    try:
        new_route = fetch_route(origin_location, destination_location, intermediates)
    except Exception as e:
        raise ValueError(f"Failed to calculate new route: {str(e)}")

    # Recalculate segments
    new_segments = recalculate_segments_with_accommodation(
        new_route, requirements.daily_distance_km
    )

    # Update requirements
    updated_requirements = requirements.model_copy(
        update={
            "origin": origin_location,
            "destination": destination_location,
            "intermediates": intermediates,
        }
    )

    logger.info("Successfully recalculated complete route")

    return Command(
        update={
            "route": new_route,
            "segments": new_segments,
            "requirements": updated_requirements,
            "messages": [
                ToolMessage(
                    content="Route recalculated.", tool_call_id=runtime.tool_call_id
                )
            ],
        }
    )
