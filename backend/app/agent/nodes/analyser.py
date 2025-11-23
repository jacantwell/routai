"""Route optimisation node for improving accommodation availability.

This node uses an LLM with route modification tools to iteratively
improve the route based on user preferences, particularly ensuring
accommodation is available at each stop.
"""

import logging
from typing import Dict, Any

from app.agent.schemas.state import AgentState
from app.agent.config.llm import create_llm_with_tools
from app.agent.config.constants import OPTIMISER_SYSTEM_PROMPT
from app.tools import OPTIMISATION_TOOLS

logger = logging.getLogger(__name__)


# Initialize LLM with optimisation tools
_llm_with_tools = create_llm_with_tools(tools=OPTIMISATION_TOOLS)


def optimiser_node(state: AgentState) -> Dict[str, Any]:
    """Analyses the initially generate route
    
    This node analyzes the current route and uses available tools to:
    1. Identify segments without accommodation
    2. Adjust daily distances to create better stopping points
    3. Add intermediate waypoints through towns with accommodation
    4. Search for accommodation with wider search radii
    
    The node operates in an agentic loop, making multiple tool calls
    until the route meets requirements or no further improvements can be made.
    
    Args:
        state: Current agent state with route, segments, and requirements
        
    Returns:
        Dictionary with new messages to add to state
    """
    logger.info("Optimizer node: Analyzing route for improvements")
    
    # Build the optimisation request message
    optimisation_request = _build_optimisation_request(state)
    
    # Invoke LLM with tools to optimise the route
    response = _llm_with_tools.invoke(
        state.messages + [optimisation_request],
        system=OPTIMISER_SYSTEM_PROMPT
    )
    
    # Log tool calls if any
    if hasattr(response, 'tool_calls') and response.tool_calls:
        tool_names = [tc.get('name') for tc in response.tool_calls]
        logger.info(f"Optimizer requesting tools: {tool_names}")
    
    return {"messages": [response]}


def _build_optimisation_request(state: AgentState) -> Any:
    """Build a message requesting route optimisation.
    
    Analyzes current route state and creates a message highlighting
    issues that need to be addressed (e.g., missing accommodation).
    
    Args:
        state: Current agent state
        
    Returns:
        Message object requesting optimisation
    """
    from langchain_core.messages import HumanMessage
    
    segments = state.segments
    requirements = state.requirements
    
    if not segments:
        logger.error("Cannot optimise route without segments")
        raise ValueError("Route optimisation requires generated segments")
    
    # Analyze accommodation availability
    days_without_accommodation = [
        seg.day for seg in segments 
        if len(seg.accommodation_options) == 0
    ]
    
    # Build optimisation request
    if days_without_accommodation:
        request = (
            f"The route has been calculated with {len(segments)} days. "
            f"However, the following days lack accommodation options: "
            f"{', '.join(map(str, days_without_accommodation))}. "
            f"\n\nPlease analyze the route and use the available tools to "
            f"ensure accommodation is available at each stop. You may need to:\n"
            f"- Adjust the daily distance to create stops in towns\n"
            f"- Add intermediate waypoints through cities with accommodation\n"
            f"- Search with a wider radius around segment endpoints\n\n"
            f"Use get_route_summary and get_segment_details to understand "
            f"the current route, then make appropriate modifications."
        )
    else:
        request = (
            f"The route has been calculated with {len(segments)} days and "
            f"accommodation is available at all stops. Please review the route "
            f"using get_route_summary to ensure it meets the user's requirements."
        )
    
    logger.info(f"Optimization request: {len(days_without_accommodation)} days need accommodation")
    
    return HumanMessage(content=request)


def should_continue_optimisation(state: AgentState) -> bool:
    """Check if optimisation should continue.
    
    Determines whether the optimiser should run another iteration or
    if the route is acceptable.
    
    Args:
        state: Current agent state
        
    Returns:
        True if optimisation should continue, False otherwise
    """
    segments = state.segments
    
    if not segments:
        return False
    
    # Check if all days have accommodation
    days_without_accommodation = [
        seg.day for seg in segments 
        if len(seg.accommodation_options) == 0
    ]
    
    has_accommodation_issues = len(days_without_accommodation) > 0
    
    logger.info(
        f"Optimization check: {len(days_without_accommodation)} days without accommodation"
    )
    
    return has_accommodation_issues