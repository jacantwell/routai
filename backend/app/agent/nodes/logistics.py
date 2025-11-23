import logging
from typing import Dict, Any
from langchain_core.messages import ToolMessage

from app.agent.schemas.state import AgentState, RouteRequirements
from app.agent.config.llm import create_llm_with_tools
from app.agent.config.constants import PLANNER_SYSTEM_PROMPT
from app.tools import get_location
from app.utils.utils import get_accommodation

logger = logging.getLogger(__name__)


def find_accommodation_node(state: AgentState) -> Dict[str, Any]:
    """Find accommodation options for all segments in the route
    
    Args:
        state: Current agent state with requirements
        
    Returns:
        Dictionary with update segments
    """

    segments = state.segments

    if not segments:
        error_msg = "Accommodaion search requires validated segments"
        raise ValueError(error_msg)    
    
    logger.info(f"Accommodation node: Finding accommodation options for {len(segments)} nights")

    days_with_no_accommodation = []

    for sm in segments:
        # Searching for accommodation for the end of each day
        accommodation_opts = get_accommodation(sm.route.destination)    
        sm.accommodation_options += accommodation_opts
        if len(sm.accommodation_options) == 0:
            days_with_no_accommodation.append(sm.day)

    logger.info(f"Accommodation node: Unable to find accommodation for nights: {days_with_no_accommodation}")

        
    return {"segments": segments}