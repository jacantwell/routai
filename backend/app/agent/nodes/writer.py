import logging
from typing import Dict, Any
from langchain_core.messages import HumanMessage

from app.agent.schemas.state import AgentState
from app.agent.config.llm import create_llm
from app.agent.config.constants import ITINERARY_PROMPT_TEMPLATE, METERS_PER_KM

logger = logging.getLogger(__name__)

# Initialize LLM for itinerary writing
_llm = create_llm()


def itinerary_writer_node(state: AgentState) -> Dict[str, Any]:
    """Generate a friendly itinerary summary for the user.
    
    This node takes the calculated route and waypoints and uses an LLM
    to generate a natural language, day-by-day itinerary that's easy
    for the user to understand and use.
    
    Args:
        state: Current agent state with route, waypoints, and requirements
        
    Returns:
        Dictionary with itinerary message to send to user
        
    Raises:
        ValueError: If required data is missing from state
    """
    requirements = state.requirements
    route = state.route
    waypoints = state.waypoints
    
    # Validate all required data is present
    if not requirements:
        error_msg = "Itinerary generation requires validated requirements"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not route:
        error_msg = "Itinerary generation requires a calculated route"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not waypoints:
        error_msg = "Itinerary generation requires generated waypoints"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("Generating itinerary summary")
    
    # Format waypoints for display
    waypoints_str = "\n".join(
        f"Day {i+1}: {wp}" 
        for i, wp in enumerate(waypoints)
    )
    
    # Construct the system prompt with route data
    system_prompt = ITINERARY_PROMPT_TEMPLATE.format(
        origin=requirements.origin.name,
        destination=requirements.destination.name,
        distance_km=route.distance / METERS_PER_KM,
        daily_distance_km=requirements.daily_distance_km,
        waypoints=waypoints_str,
    )
    
    try:
        # Generate the itinerary
        response = _llm.invoke(
            [HumanMessage(
                content="Please create a day-by-day itinerary based on the route data."
            )],
            system=system_prompt,
        )
        
        logger.info("Itinerary generated successfully")
        
        return {"messages": [response]}
        
    except Exception as e:
        error_msg = f"Itinerary generation failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e