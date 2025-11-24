import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage

from app.agent.config import REVIEWER_SYSTEM_PROMPT, create_llm_with_tools
from app.models.state import AgentState
from app.tools import get_location

logger = logging.getLogger(__name__)

_llm = create_llm_with_tools(tools=[get_location])


def reviewer_node(state: AgentState) -> Dict[str, Any]:
    """Generate route overview with full state access.
    
    This node creates a comprehensive summary of the planned route by giving
    the LLM direct access to all state data. The LLM can intelligently analyze
    and present the route information based on the current confirmation status.
    
    Args:
        state: Current agent state with route, segments, and requirements
        
    Returns:
        Dictionary with overview message to send to user
        
    Raises:
        ValueError: If required data is missing from state
    """
    # Validate required data is present
    if not state.requirements:
        error_msg = "Overview generation requires validated requirements"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not state.route:
        error_msg = "Overview generation requires a calculated route"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not state.segments:
        error_msg = "Overview generation requires generated segments"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    mode = "confirmed" if state.user_confirmed else "asking"
    logger.info(f"Generating route overview (mode: {mode})")
    
    # Serialize the state for the LLM
    state_summary = f"""Current Route State:

Requirements:
- Origin: {state.requirements.origin.name} ({state.requirements.origin.coordinates})
- Destination: {state.requirements.destination.name} ({state.requirements.destination.coordinates})
- Daily Distance Target: {state.requirements.daily_distance_km} km
- Intermediate Stops: {len(state.requirements.intermediates)}
- Context: {state.requirements.context or 'None provided'}

Overall Route:
- Total Distance: {state.route.distance / 1000:.1f} km
- Total Elevation Gain: {state.route.elevation_gain} m
- Number of Days: {len(state.segments)}

Daily Segments:
"""
    
    for seg in state.segments:
        accommodation_count = len(seg.accommodation_options)
        state_summary += f"""
Day {seg.day}:
  - Distance: {seg.route.distance / 1000:.1f} km
  - Elevation Gain: {seg.route.elevation_gain} m
  - Start: {seg.route.origin.name}
  - End: {seg.route.destination.name}
  - Accommodation Options: {accommodation_count}
"""
    
    state_summary += f"\nUser Confirmed: {state.user_confirmed}"
    
    try:
        # Generate the overview with full state context
        response = _llm.invoke(
            [HumanMessage(content=state_summary)],
            system=REVIEWER_SYSTEM_PROMPT,
        )
        
        logger.info(f"Route overview generated (mode: {mode})")
        
        return {"messages": [response]}
        
    except Exception as e:
        error_msg = f"Overview generation failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e