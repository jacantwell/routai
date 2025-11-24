import logging
from typing import Any, Dict

from langchain_core.messages import HumanMessage

from app.agent.config import OPTIMISER_SYSTEM_PROMPT, create_llm_with_tools
from app.models import AgentState
from app.tools import OPTIMISATION_TOOLS

logger = logging.getLogger(__name__)

_llm_with_tools = create_llm_with_tools(tools=OPTIMISATION_TOOLS)


def optimiser_node(state: AgentState) -> Dict[str, Any]:
    """Enhanced optimiser that handles both optimization and confirmation."""
    logger.info("Optimizer node: Starting optimization/confirmation check")

    optimization_request = _build_optimization_request(state)

    response = _llm_with_tools.invoke(
        state.messages + [optimization_request], system=OPTIMISER_SYSTEM_PROMPT
    )

    updates = {"messages": [response], "awaiting_user_response": False}

    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_names = [tc.get("name") for tc in response.tool_calls]
        if "confirm_route" in tool_names:
            logger.info("Optimizer confirmed route is ready")
        else:
            logger.info(f"Optimizer requesting tools: {tool_names}")

    return updates


def _build_optimization_request(state: AgentState) -> Any:
    """Build a message requesting route optimization/confirmation."""
    segments = state.segments
    requirements = state.requirements

    if not segments or not requirements:
        raise ValueError(
            "Route optimization requires generated segments and requirements"
        )

    has_user_feedback = False
    if len(state.messages) > 0:
        last_msg = state.messages[-1]
        if hasattr(last_msg, "type") and last_msg.type == "human":
            has_user_feedback = True

    optimiser_already_ran = False
    if not has_user_feedback and len(state.messages) > 5:
        for msg in reversed(state.messages[-10:]):
            if hasattr(msg, "tool_calls") and msg.tool_calls:  # type:ignore
                tool_names = [tc.get("name") for tc in msg.tool_calls]  # type: ignore
                if any(
                    tool in tool_names
                    for tool in [
                        "adjust_daily_distance",
                        "search_accommodation",
                        "modify_waypoint",
                    ]
                ):
                    optimiser_already_ran = True
                    break

    if has_user_feedback:
        request = (
            f"The user has responded to the route overview.\n"
            f"Current route status: {len(segments)} days, {requirements.daily_distance_km}km/day target\n"
            f"Tasks: Interpret intent, modify route if requested, or confirm_route if satisfied."
        )
    elif optimiser_already_ran:
        request = "Route already optimized. Do not change. Proceed to reviewer."
    else:
        request = (
            f"First optimization pass. {len(segments)} days.\n"
            f"Only fix CRITICAL issues (missing accommodation, dangerous distances).\n"
            f"If no critical issues, call NO tools."
        )

    return HumanMessage(content=request)
