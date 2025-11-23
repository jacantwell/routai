import logging
from typing import Literal, Type
from langgraph.graph import END

from app.agent.schemas.state import AgentState

logger = logging.getLogger(__name__)


def route_planner(
    state: AgentState,
):  #TODO: Add typing
    """Determine next step after planner node.
    
    This function examines the last message from the planner to decide
    what should happen next:
    
    1. If RouteRequirements tool was called -> move to parser
    2. If other tools were called (e.g., get_location) -> execute tools
    3. If no tools called -> end (LLM asked user a question)
    
    Args:
        state: Current agent state
        
    Returns:
        Next node to execute or END
    """
    last_message = state.messages[-1]
    
    # Check if the LLM called any tools
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:  # type: ignore
        logger.info("Planner route: No tool calls, ending for user response")
        return END
    
    # Get the first tool call (should only be one in our setup)
    tool_call = last_message.tool_calls[0]  # type: ignore
    tool_name = tool_call.get("name")
    
    if tool_name == "RouteRequirements":
        logger.info("Planner route: Requirements submitted, moving to parser")
        return "parser"
    
    logger.info(f"Planner route: Tool call detected ({tool_name}), executing tools")
    return "planner_tools"