import logging
from typing import Dict, Any

from app.agent.config import OPTIMISER_SYSTEM_PROMPT, create_llm_with_tools
from app.models import AgentState
from app.tools import OPTIMISATION_TOOLS

logger = logging.getLogger(__name__)

# Initialize LLM with optimisation tools + confirmation tool
_llm_with_tools = create_llm_with_tools(
    tools=OPTIMISATION_TOOLS
)


def optimiser_node(state: AgentState) -> Dict[str, Any]:
    """Enhanced optimizer that handles both optimization and confirmation.
    
    This node:
    1. Analyzes the current route state
    2. Checks if user's last message indicates confirmation or change request
    3. Uses tools to modify route if needed
    4. Calls confirm_route tool when user confirms and route is ready
    
    The optimizer operates in different modes based on context:
    - Initial optimization: Fix accommodation issues, verify requirements
    - User feedback mode: Interpret feedback and make requested changes
    - Confirmation mode: Check if user is satisfied and ready to proceed
    
    Args:
        state: Current agent state with route, segments, and messages
        
    Returns:
        Dictionary with new messages and optionally user_confirmed flag
    """
    logger.info("Optimizer node: Starting optimization/confirmation check")
    
    # Build the optimization request based on state
    optimization_request = _build_optimization_request(state)
    
    # Invoke LLM with all tools
    response = _llm_with_tools.invoke(
        state.messages + [optimization_request],
        system=OPTIMISER_SYSTEM_PROMPT
    )
    
    # Check if optimizer called RouteConfirmed
    updates = {"messages": [response]}
    
    if hasattr(response, 'tool_calls') and response.tool_calls:
        tool_names = [tc.get('name') for tc in response.tool_calls]
        
        if 'confirm_route' in tool_names:
            logger.info("Optimizer confirmed route is ready")
        else:
            logger.info(f"Optimizer requesting tools: {tool_names}")
    
    return updates


def _build_optimization_request(state: AgentState) -> Any:
    """Build a message requesting route optimization/confirmation.
    
    Analyzes current state to determine what the optimizer should focus on:
    - First time: Check for accommodation issues
    - After user feedback: Interpret and address feedback
    - Ready to confirm: Check if route meets requirements
    
    Args:
        state: Current agent state
        
    Returns:
        Message object for the optimizer
    """
    from langchain_core.messages import HumanMessage
    
    segments = state.segments
    requirements = state.requirements
    
    if not segments:
        logger.error("Cannot optimize without segments")
        raise ValueError("Route optimization requires generated segments")
    
    if not requirements:
        logger.error("Cannot optimize without requirements")
        raise ValueError("Route optimization requires requirements")
    
    # Check if we have user feedback (human message after reviewer)
    has_user_feedback = False
    if len(state.messages) > 0:
        last_msg = state.messages[-1]
        if hasattr(last_msg, 'type') and last_msg.type == 'human':
            # Check if there's a reviewer message before this
            for msg in reversed(state.messages[:-1]):
                if hasattr(msg, 'type') and msg.type == 'ai':
                    content_lower = msg.content.lower() # type: ignore
                    if any(phrase in content_lower for phrase in [
                        'overview', 'proceed', 'make adjustments'
                    ]):
                        has_user_feedback = True
                        break
    
    # Check if optimizer already made changes (to prevent infinite loops)
    # Look for tool calls from optimizer in recent messages
    optimizer_already_ran = False
    if not has_user_feedback and len(state.messages) > 5:
        # Check if we see optimizer tool calls in the message history
        for msg in reversed(state.messages[-10:]):
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_names = [tc.get('name') for tc in msg.tool_calls]
                # If we see route modification tools, optimizer already ran
                if any(tool in tool_names for tool in ['adjust_daily_distance', 'search_accommodation', 'modify_waypoint']):
                    optimizer_already_ran = True
                    logger.info("Optimizer detected previous optimization attempt - will not optimize again")
                    break
    
    # Analyze accommodation availability
    days_without_accommodation = [
        seg.day for seg in segments 
        if len(seg.accommodation_options) == 0
    ]
    
    # Build request based on context
    if has_user_feedback:
        # User has provided feedback after seeing overview
        request = (
            f"The user has responded to the route overview. Their message may contain:\n"
            f"- Confirmation that they're happy with the route\n"
            f"- Requests for changes or adjustments\n"
            f"- Questions or concerns about the route\n\n"
            f"Current route status:\n"
            f"- {len(segments)} days, {requirements.daily_distance_km}km/day target\n"
            f"- Days without accommodation: {days_without_accommodation if days_without_accommodation else 'None'}\n\n"
            f"Your tasks:\n"
            f"1. Interpret the user's last message to understand their intent\n"
            f"2. If they want changes: use appropriate tools to modify the route\n"
            f"3. If they're satisfied and confirming: call the confirm_route tool\n"
            f"4. If unclear: ask for clarification or make reasonable assumptions\n\n"
            f"Use get_route_summary first to understand the current state, then decide."
        )
    elif optimizer_already_ran:
        # Optimizer already made changes, don't optimize again
        request = (
            f"The route has already been optimized in a previous pass.\n\n"
            f"Current route status:\n"
            f"- {len(segments)} days, {requirements.daily_distance_km}km/day target\n"
            f"- Days without accommodation: {days_without_accommodation if days_without_accommodation else 'None'}\n\n"
            f"DO NOT call any tools. DO NOT make any more changes.\n"
            f"The route is ready to be presented to the user for review.\n"
            f"Simply acknowledge this and let the workflow proceed to the reviewer."
        )
    else:
        # First optimization pass - check for obvious issues
        request = (
            f"This is the first optimization pass. The route has been calculated and accommodation searched.\n\n"
            f"Current route status:\n"
            f"- {len(segments)} days, {requirements.daily_distance_km}km/day target\n"
            f"- Days without accommodation: {days_without_accommodation if days_without_accommodation else 'None'}\n\n"
            f"Your task: Determine if any CRITICAL optimization is needed BEFORE showing the route to the user.\n\n"
            f"CRITICAL issues that require action:\n"
            f"- Days completely missing accommodation → Use search_accommodation tool\n"
            f"- Extremely dangerous daily distances (>150km or <20km) → Use adjust_daily_distance\n\n"
            f"NON-CRITICAL issues (do NOT fix these automatically):\n"
            f"- Daily distances slightly off target (within ±20km)\n"
            f"- Route could be slightly more optimized\n"
            f"- Minor accommodation preferences\n\n"
            f"IMPORTANT RULES:\n"
            f"1. Only call tools if there's a CRITICAL issue that must be fixed\n"
            f"2. Once you call a tool, check the result ONCE and stop\n"
            f"3. DO NOT repeatedly call get_route_summary or get_segment_details\n"
            f"4. DO NOT repeatedly adjust the same parameter\n"
            f"5. If no critical issues OR if you already made one optimization → Call NO tools\n"
            f"6. The route will proceed to review where the user can request further changes\n\n"
            f"Most routes are fine as-is. Trust the initial calculation unless there's a critical problem."
        )
    
    logger.info(f"Optimization mode: {'user_feedback' if has_user_feedback else 'initial_check'}")
    
    return HumanMessage(content=request)