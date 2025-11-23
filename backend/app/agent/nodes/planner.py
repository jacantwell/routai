import logging
from typing import Dict, Any
from langchain_core.messages import ToolMessage

from app.agent.schemas.state import AgentState, RouteRequirements
from app.agent.config.llm import create_llm_with_tools
from app.agent.config.constants import PLANNER_SYSTEM_PROMPT
from app.tools import get_location

logger = logging.getLogger(__name__)


# Initialize LLM with tools
_llm_with_tools = create_llm_with_tools(
    tools=[get_location, RouteRequirements]
)


def planner_node(state: AgentState) -> Dict[str, Any]:
    """Main planning node that gathers route requirements from the user.
    
    This node uses an LLM to:
    1. Ask for missing information (origin, destination, daily distance)
    2. Call get_location tool to resolve location names to coordinates
    3. Submit RouteRequirements when all info is gathered
    
    Args:
        state: Current agent state with message history
        
    Returns:
        Dictionary with new messages to add to state
    """
    logger.info("Planner node: Processing user request")
    logger.info(f"Message history: {state.messages}")
    
    response = _llm_with_tools.invoke(
        state.messages,
        system=PLANNER_SYSTEM_PROMPT
    )
    
    # Log tool calls if any
    if hasattr(response, 'tool_calls') and response.tool_calls:
        tool_names = [tc.get('name') for tc in response.tool_calls]
        logger.info(f"Planner requesting tools: {tool_names}")
    
    return {"messages": [response]}


def parse_requirements_node(state: AgentState) -> Dict[str, Any]:
    """Parse and validate RouteRequirements from tool call.
    
    This node extracts the RouteRequirements tool call from the last
    message and validates it using Pydantic. If valid, it stores the
    requirements in state and creates a success message.
    
    Args:
        state: Current agent state
        
    Returns:
        Dictionary with validated requirements and tool success message
        
    Raises:
        ValueError: If requirements cannot be parsed or validated
    """
    logger.info("Parsing route requirements from tool call")
    
    last_message = state.messages[-1]
    
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:  # type: ignore
        error_msg = "Expected RouteRequirements tool call but found none"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    tool_call = last_message.tool_calls[0]  # type: ignore
    
    if tool_call.get("name") != "RouteRequirements":
        error_msg = f"Expected RouteRequirements, got {tool_call.get('name')}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Validate and parse requirements
        requirements = RouteRequirements(**tool_call["args"])
        
        logger.info(
            f"Requirements validated: {requirements.origin.name} -> "
            f"{requirements.destination.name} ({requirements.daily_distance_km}km/day)"
        )
        
        # Create success message
        tool_msg = ToolMessage(
            tool_call_id=tool_call["id"],
            content="Route requirements validated and stored successfully.",
        )
        
        return {
            "requirements": requirements,
            "messages": [tool_msg]
        }
        
    except Exception as e:
        logger.error(f"Failed to validate requirements: {str(e)}")
        raise ValueError(f"Invalid route requirements: {str(e)}") from e