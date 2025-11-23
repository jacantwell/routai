import logging

from langgraph.graph import END

from app.agent.schemas.state import AgentState

logger = logging.getLogger(__name__)


def route_planner(
    state: AgentState,
):  # TODO: Add typing
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

    1. If tools were called -> execute them and loop back to optimiser
    2. If no tools called -> optimiser is done, move to writer

    Args:
        state: Current agent state

    Returns:
        Next node to execute
    """
    last_message = state.messages[-1]

    # Check if the optimiser called any tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:  # type: ignore
        tool_names = [tc.get("name") for tc in last_message.tool_calls]  # type: ignore
        logger.info(
            f"Optimizer route: Tools called ({', '.join(tool_names)}), executing"
        )
        return "optimiser_tools"

    # No tools called - optimiser is satisfied with the route
    logger.info("Optimizer route: No tools called, moving to writer")
    return "writer"


# def should_optimise_route(state: AgentState) -> str:
#     """Decide whether route optimisation is needed.

#     This conditional routing function checks if the route has any
#     accommodation issues or other problems that require optimisation.

#     Args:
#         state: Current agent state

#     Returns:
#         "optimiser" if optimisation needed, "writer" if route is acceptable
#     """
#     segments = state.segments
#     requirements = state.requirements

#     if not segments:
#         logger.warning("No segments to optimise, skipping to writer")
#         return "writer"

#     # Check for accommodation issues
#     days_without_accommodation = [
#         seg.day for seg in segments if len(seg.accommodation_options) == 0
#     ]

#     # Check if user has specific requirements (could be extended)
#     needs_optimisation = len(days_without_accommodation) > 0

#     if needs_optimisation:
#         logger.info(
#             f"Route needs optimisation: {len(days_without_accommodation)} days "
#             f"without accommodation"
#         )
#         return "optimiser"

#     logger.info("Route acceptable, skipping optimisation")
#     return "writer"
