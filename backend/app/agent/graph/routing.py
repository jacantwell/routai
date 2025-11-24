import logging

from langgraph.graph import END

from app.models import AgentState

logger = logging.getLogger(__name__)


def route_planner(
    state: AgentState,
) -> str:
    """Determine next step after planner node.

    This function examines the state and last message to decide routing:

    1. If route exists and user just provided feedback after review -> route to optimiser
    2. If RouteRequirements tool was called -> move to parser
    3. If other tools were called (e.g., get_location) -> execute tools
    4. If no tools called -> end (LLM asked user a question)

    Args:
        state: Current agent state

    Returns:
        Next node to execute or END
    """
    # Check if we're in feedback mode (route exists, not confirmed, user just responded)
    if state.route and state.segments and not state.user_confirmed:
        # Check if last message is from human (user feedback)
        if state.messages and len(state.messages) >= 2:
            last_msg = state.messages[-1]
            if hasattr(last_msg, "type") and last_msg.type == "human":
                # Check if previous message was reviewer asking for confirmation
                second_last = state.messages[-2]
                if hasattr(second_last, "type") and second_last.type == "ai":
                    content_lower = second_last.content.lower()  # type: ignore
                    if any(
                        phrase in content_lower
                        for phrase in [
                            "overview",
                            "proceed",
                            "make adjustments",
                            "would you like to",
                        ]
                    ):
                        logger.info(
                            "Planner route: User feedback after review detected, routing to optimiser"
                        )
                        return "optimiser"

    last_message = state.messages[-1]

    # Check if the LLM called any tools
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:  # type: ignore
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


def route_optimiser(state: AgentState) -> str:
    """Determine next step after optimiser node.

    This function examines the last message from the optimiser to decide
    what should happen next:

    1. If confirm_route tool was called -> move to reviewer
    2. If other tools were called -> execute them and loop back to optimiser
    3. If no tools called -> move to reviewer (for first overview)

    Args:
        state: Current agent state

    Returns:
        Next node to execute
    """
    last_message = state.messages[-1]

    # Check if the optimiser called any tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:  # type: ignore
        tool_calls = last_message.tool_calls  # type: ignore
        tool_names = [tc.get("name") for tc in tool_calls]

        # Check if confirm_route was called
        if "confirm_route" in tool_names:
            logger.info("Optimiser route: Route confirmed, moving to reviewer")
            return "reviewer"

        # Other tools were called
        logger.info(
            f"Optimiser route: Tools called ({', '.join(tool_names)}), executing"
        )
        return "optimiser_tools"

    # No tools called - first time through, show overview
    logger.info("Optimiser route: No tools called, moving to reviewer for overview")
    return "reviewer"


def route_reviewer(state: AgentState) -> str:
    """Determine next step after reviewer node.

    This function checks the user_confirmed flag:

    1. If user_confirmed is True -> move to writer for final itinerary
    2. If user_confirmed is False -> wait for user response (END)

    Args:
        state: Current agent state

    Returns:
        Next node to execute or END
    """
    if state.user_confirmed:
        logger.info("Reviewer route: Route confirmed, moving to writer")
        return "writer"

    logger.info("Reviewer route: Waiting for user confirmation")
    return END
