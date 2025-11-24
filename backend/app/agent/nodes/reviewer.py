import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage

from app.agent.config import OVERVIEW_PROMPT_ASKING, OVERVIEW_PROMPT_CONFIRMED, create_llm
from app.models.state import AgentState

logger = logging.getLogger(__name__)

_llm = create_llm()


def reviewer_node(state: AgentState) -> Dict[str, Any]:
    """Generate route overview based on confirmation state.
    
    This node creates a summary of the planned route including:
    - Total distance and duration
    - Daily breakdown
    - Accommodation availability
    - Any potential issues
    
    Behavior depends on user_confirmed flag:
    - If False: Asks user to confirm or request changes
    - If True: Confirms route is ready and proceeds
    
    Args:
        state: Current agent state with route, segments, and requirements
        
    Returns:
        Dictionary with overview message to send to user
        
    Raises:
        ValueError: If required data is missing from state
    """
    requirements = state.requirements
    route = state.route
    segments = state.segments
    user_confirmed = state.user_confirmed
    
    # Validate all required data is present
    if not requirements:
        error_msg = "Overview generation requires validated requirements"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not route:
        error_msg = "Overview generation requires a calculated route"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not segments:
        error_msg = "Overview generation requires generated segments"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    mode = "confirmed" if user_confirmed else "asking"
    logger.info(f"Generating route overview (mode: {mode})")
    
    # Calculate accommodation statistics
    days_with_accommodation = sum(
        1 for seg in segments if len(seg.accommodation_options) > 0
    )
    days_without_accommodation = len(segments) - days_with_accommodation
    
    if days_without_accommodation == 0:
        accommodation_summary = f"✓ Accommodation found for all {len(segments)} days"
    else:
        missing_days = [
            seg.day for seg in segments if len(seg.accommodation_options) == 0
        ]
        accommodation_summary = (
            f"⚠ Accommodation found for {days_with_accommodation}/{len(segments)} days\n"
            f"Days without accommodation: {', '.join(map(str, missing_days))}"
        )
    
    # Create segments summary
    segments_summary = []
    for seg in segments:
        distance = seg.route.distance / 1000
        accommodation_status = "✓" if len(seg.accommodation_options) > 0 else "⚠"
        segments_summary.append(
            f"Day {seg.day}: {distance:.1f} km {accommodation_status}"
        )
    segments_str = "\n".join(segments_summary)
    
    # Calculate total elevation
    total_elevation = sum(seg.route.elevation_gain for seg in segments)
    
    # Choose prompt based on confirmation state
    prompt_template = OVERVIEW_PROMPT_CONFIRMED if user_confirmed else OVERVIEW_PROMPT_ASKING
    
    # Construct the system prompt with route data
    system_prompt = prompt_template.format(
        origin=requirements.origin.name,
        destination=requirements.destination.name,
        distance_km=route.distance / 1000,
        daily_distance_km=requirements.daily_distance_km,
        num_days=len(segments),
        elevation_gain=total_elevation,
        segments_summary=segments_str,
        accommodation_summary=accommodation_summary,
    )
    
    try:
        # Generate the overview
        response = _llm.invoke(
            [HumanMessage(
                content="Please create a route overview."
            )],
            system=system_prompt,
        )
        
        logger.info(f"Route overview generated (mode: {mode})")
        
        return {"messages": [response]}
        
    except Exception as e:
        error_msg = f"Overview generation failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e