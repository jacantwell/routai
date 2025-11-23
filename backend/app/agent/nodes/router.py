import logging
from typing import Dict, Any, List

from app.agent.schemas.state import AgentState
from app.agent.utils import fetch_route, calculate_waypoints
from app.agent.config.constants import METERS_PER_KM
from app.models.models import Waypoint

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
    intermediate_coords = [
        point.coordinates 
        for point in requirements.intermediates
    ]
    
    try:
        route = fetch_route(
            origin=requirements.origin.coordinates,
            destination=requirements.destination.coordinates,
            intermediates=intermediate_coords,
        )
        
        logger.info(
            f"Route calculated successfully: {route.distance / METERS_PER_KM:.2f} km"
        )
        
        return {"route": route}
        
    except Exception as e:
        error_msg = f"Route calculation failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def generate_waypoints_node(state: AgentState) -> Dict[str, Any]:
    """Generate daily waypoints along the calculated route.
    
    This node divides the route into daily segments based on the
    user's target daily distance.
    
    Args:
        state: Current agent state with route and requirements
        
    Returns:
        Dictionary with generated waypoints
        
    Raises:
        ValueError: If route or requirements are missing
        RuntimeError: If waypoint generation fails
    """
    route = state.route
    requirements = state.requirements
    
    if not route:
        error_msg = "Waypoint generation requires a calculated route"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not requirements:
        error_msg = "Waypoint generation requires validated requirements"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    daily_distance_m = requirements.daily_distance_km * METERS_PER_KM
    
    logger.info(
        f"Generating waypoints for {requirements.daily_distance_km}km/day target "
        f"(total distance: {route.distance / METERS_PER_KM:.2f}km)"
    )
    
    try:
        waypoints: List[Waypoint] = calculate_waypoints(
            route.polyline,
            daily_distance_m,
            route.distance,
        )
        
        logger.info(f"Generated {len(waypoints)} waypoints")
        
        return {"waypoints": waypoints}
        
    except Exception as e:
        error_msg = f"Waypoint generation failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e