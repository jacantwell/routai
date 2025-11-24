import logging

from langgraph.graph import END

from app.models import AgentState

logger = logging.getLogger(__name__)


def route_planner(state: AgentState) -> str:
    """Route based only on tool calls."""
    last_message = state.messages[-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:  # type: ignore
        return END

    tool_name = last_message.tool_calls[0].get("name")  # type: ignore
    if tool_name == "RouteRequirements":
        return "parser"
    return "planner_tools"


def route_after_accommodation(state: AgentState) -> str:
    """Skip optimiser if no critical issues."""
    if state.critical_optimization_done:
        return "reviewer"
    return "optimiser"


def route_optimiser(state: AgentState) -> str:
    """Execute tools or move to reviewer."""
    last_message = state.messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:  # type: ignore
        return "optimiser_tools"

    # Mark optimisation as done to prevent re-runs
    state.critical_optimization_done = True
    return "reviewer"


def route_reviewer(state: AgentState) -> str:
    """Check confirmation or wait for user, or execute tools."""
    last_message = state.messages[-1]

    # Check if the reviewer decided to call a tool (like get_weather)
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:  # type: ignore
        return "reviewer_tools"

    # Check confirmation
    if state.user_confirmed:
        return "writer"

    return END
