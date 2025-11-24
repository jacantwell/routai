import logging
from typing import Any, Dict

from langchain_core.messages import ToolMessage, HumanMessage

from app.agent.config import (
    REVIEWER_CONFIRMED_PROMPT,
    REVIEWER_INITIAL_PROMPT,
    REVIEWER_RESPONSE_PROMPT,
    create_llm_with_tools,
)
from app.models.state import AgentState
from app.tools import get_weather

logger = logging.getLogger(__name__)

_llm = create_llm_with_tools([get_weather])


def _check_for_recent_changes(state: AgentState) -> str:
    """Check if optimiser made recent changes based on tool usage."""
    if not state.messages or len(state.messages) < 2:
        return ""

    recent_tools_used = []
    for msg in reversed(state.messages[-5:]):  # Check last 5 messages
        if hasattr(msg, "tool_calls") and msg.tool_calls:  # type: ignore
            for tool_call in msg.tool_calls:  # type: ignore
                tool_name = tool_call.get("name", "")
                if tool_name and tool_name != "confirm_route":
                    recent_tools_used.append(tool_name)

    if not recent_tools_used:
        return ""

    # Create a summary of what was done
    changes = []
    tool_set = set(recent_tools_used)

    if "get_segment_details" in tool_set:
        changes.append("Retrieved detailed segment information")
    if "get_route_summary" in tool_set:
        changes.append("Analyzed route summary")
    if "search_accommodation" in tool_set:
        changes.append("Searched for additional accommodation options")
    if "adjust_segment_distance" in tool_set or "modify_waypoint" in tool_set:
        changes.append("Modified route segments")

    return ", ".join(changes) if changes else ""


def _get_recent_tool_outputs(state: AgentState) -> str:
    """Extract content from recent tool executions (like weather data).
    
    The Reviewer generates its overview from static state (segments/route).
    However, if the Optimiser (or Reviewer) just called a tool like get_weather,
    that data exists in the message history as a ToolMessage, not in the static state.
    We need to fish it out so the LLM can see it.
    """
    if not state.messages:
        return ""

    tool_outputs = []
    # Look back through recent history (last 10 messages to be safe)
    # We are looking for ToolMessages that might contain relevant info (like weather)
    for msg in reversed(state.messages[-10:]):
        if isinstance(msg, ToolMessage):
            # We found data!
            tool_outputs.append(f"Data from {msg.name}: {msg.content}")
    
    if not tool_outputs:
        return ""
        
    return "\n\n".join(tool_outputs)


def _build_state_summary(state: AgentState) -> str:
    # Validate required data is present
    if not state.requirements:
        raise ValueError("Overview generation requires validated requirements")
    if not state.route:
        raise ValueError("Overview generation requires a calculated route")
    if not state.segments:
        raise ValueError("Overview generation requires generated segments")

    # Serialize the state for the LLM
    state_summary = f"""Current Route State:

    Requirements:
    - Origin: {state.requirements.origin.name}
    - Destination: {state.requirements.destination.name}
    - Daily Distance Target: {state.requirements.daily_distance_km} km

    Overall Route:
    - Total Distance: {state.route.distance / 1000:.1f} km
    - Days: {len(state.segments)}

    Daily Segments:
    """

    for seg in state.segments:
        state_summary += f"""
    Day {seg.day}: {seg.route.distance / 1000:.1f} km, {seg.route.origin.name} -> {seg.route.destination.name}
    """

    # Check for recent optimiser changes (Actions taken)
    recent_changes = _check_for_recent_changes(state)

    if recent_changes:
        state_summary += f"\n\nRecent Actions Taken: {recent_changes}"
    else:
        state_summary += "\n\nThis is the initial route overview."

    return state_summary


def reviewer_node(state: AgentState) -> Dict[str, Any]:
    """Present overview based on state."""

    # Determine mode
    if state.user_confirmed:
        prompt = REVIEWER_CONFIRMED_PROMPT
    else:
        # Check if optimiser just ran
        optimiser_just_ran = not state.critical_optimization_done

        if optimiser_just_ran:
            prompt = REVIEWER_INITIAL_PROMPT
        else:
            # This is a response after user feedback
            prompt = REVIEWER_RESPONSE_PROMPT

    # 1. Build the base summary from the Route Object
    base_summary = _build_state_summary(state)
    
    # 2. Fetch any "hidden" data from the message history (The Fix)
    tool_data = _get_recent_tool_outputs(state)

    # 3. Combine them
    full_context = base_summary
    if tool_data:
        full_context += f"\n\n=== RECENT TOOL DATA (Weather/Info) ===\n{tool_data}\n\nINSTRUCTION: Incorporate the tool data above into your overview if relevant."

    logger.info(f"Reviewer context length: {len(full_context)}")

    response = _llm.invoke(
        [HumanMessage(content=full_context)],
        system=prompt,
    )

    updates = {"messages": [response]}
    
    # Ensure we set the waiting flag if not confirmed (from previous fix)
    if not state.user_confirmed:
        updates["awaiting_user_response"] = True

    return updates