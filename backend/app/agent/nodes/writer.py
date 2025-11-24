import logging
from typing import Any, Dict

from langchain_core.messages import HumanMessage

from app.agent.config import ITINERARY_PROMPT_TEMPLATE, create_llm
from app.models import AgentState

logger = logging.getLogger(__name__)

_llm = create_llm()


def itinerary_writer_node(state: AgentState) -> Dict[str, Any]:
    """Generate a friendly itinerary summary for the user.

    This node takes the calculated route and segments and uses an LLM
    to generate a natural language, day-by-day itinerary that's easy
    for the user to understand and use.

    Args:
        state: Current agent state with route, segments, and requirements

    Returns:
        Dictionary with itinerary message to send to user

    Raises:
        ValueError: If required data is missing from state
    """
    requirements = state.requirements
    route = state.route
    segments = state.segments

    # Validate all required data is present
    if not requirements:
        error_msg = "Itinerary generation requires validated requirements"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not route:
        error_msg = "Itinerary generation requires a calculated route"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not segments:
        error_msg = "Itinerary generation requires generated segments"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("Generating itinerary summary")

    # Format segments for display
    segments_str = "\n".join(f"Day {i+1}: {wp}" for i, wp in enumerate(segments))

    # Construct the system prompt with route data
    system_prompt = ITINERARY_PROMPT_TEMPLATE.format(
        origin=requirements.origin.name,
        destination=requirements.destination.name,
        distance_km=route.distance / 1000,
        daily_distance_km=requirements.daily_distance_km,
        segments=segments_str,
    )

    try:
        # Generate the itinerary
        response = _llm.invoke(
            [
                HumanMessage(
                    content="Please create a day-by-day itinerary based on the route data."
                )
            ],
            system=system_prompt,
        )

        logger.info("Itinerary generated successfully")

        return {"messages": [response]}

    except Exception as e:
        error_msg = f"Itinerary generation failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
