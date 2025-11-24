from .accommodation import (find_accommodation_at_location,
                            search_accommodation_for_day)
from .location import get_location
from .route import (add_intermediate_waypoint, adjust_daily_distance,
                    confirm_route, get_route_summary,
                    recalculate_complete_route, remove_intermediate_waypoint)
from .segment import get_segment_details
from .weather import get_weather

# Basic tools for initial planning phase
PLANNING_TOOLS = [
    get_location,
    find_accommodation_at_location,
]

# Tools for the route optimization/modification phase
OPTIMISATION_TOOLS = [
    confirm_route,
    get_route_summary,
    get_segment_details,
    search_accommodation_for_day,
    adjust_daily_distance,
    add_intermediate_waypoint,
    remove_intermediate_waypoint,
    recalculate_complete_route,
    get_weather,
]

# All tools combined
ALL_ROUTE_TOOLS = PLANNING_TOOLS + OPTIMISATION_TOOLS
