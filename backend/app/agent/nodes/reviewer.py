import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage

from app.agent.config import create_llm
from app.models.state import AgentState

logger = logging.getLogger(__name__)

_llm = create_llm()


def _check_for_recent_changes(state: AgentState) -> str:
    """Check if optimizer made recent changes based on tool usage.
    
    Looks at recent messages for optimizer tool calls to understand
    what changes were made (if any).
    
    Args:
        state: Current agent state
        
    Returns:
        Description of recent changes or empty string if none
    """
    if not state.messages or len(state.messages) < 2:
        return ""
    
    # Look at last few messages for tool usage
    recent_tools_used = []
    for msg in reversed(state.messages[-5:]):  # Check last 5 messages
        if hasattr(msg, 'tool_calls') and msg.tool_calls:   # type: ignore
            for tool_call in msg.tool_calls:    # type: ignore
                tool_name = tool_call.get('name', '')
                if tool_name and tool_name != 'confirm_route':
                    recent_tools_used.append(tool_name)
    
    if not recent_tools_used:
        return ""
    
    # Create a summary of what was done
    changes = []
    tool_set = set(recent_tools_used)
    
    if 'get_segment_details' in tool_set:
        changes.append("Retrieved detailed segment information")
    if 'get_route_summary' in tool_set:
        changes.append("Analyzed route summary")
    if 'search_accommodation' in tool_set:
        changes.append("Searched for additional accommodation options")
    if 'adjust_segment_distance' in tool_set or 'modify_waypoint' in tool_set:
        changes.append("Modified route segments")
    
    return ", ".join(changes) if changes else ""


REVIEWER_SYSTEM_PROMPT = """You are a route review assistant for a bikepacking route planner.

Your task is to create a comprehensive route overview based on the current state.

You have access to the full route state including:
- requirements: User's route requirements (origin, destination, daily distance target, etc.)
- route: The calculated overall route with total distance and elevation
- segments: Daily route segments with accommodation options
- user_confirmed: Whether the user has already confirmed the route
- recent_actions: What the optimizer just did (if anything)

Your responsibilities:

1. **Analyze the route state**:
   - Review all segments, distances, and elevation gains
   - Check accommodation availability for each day
   - Identify any potential issues or concerns
   - Note any recent actions taken by the system

2. **Create a clear overview**:
   - Summarize the route (origin to destination, total distance/days)
   - Highlight key statistics (total elevation, daily averages)
   - Note accommodation status (which days have/lack options)
   - Mention any warnings or recommendations
   - If recent actions were taken (like retrieving segment details), incorporate that information naturally

3. **Answer user questions directly**:
   - If the user asked a question (indicated by "Retrieved detailed segment information" or similar), answer it with specific data from the state
   - Be direct and specific - e.g., "Day 1 is 95.2 km, Day 2 is 103.7 km, etc."
   - Don't apologize for not having information - you have all the segment data available

4. **Guide the user appropriately**:
   - If user_confirmed is False: Present the overview and ask if they want to proceed or make changes
   - If user_confirmed is True: Acknowledge confirmation and indicate the route is ready for detailed itinerary generation

Keep your overview concise but informative. Use a friendly, conversational tone. Present the information clearly so users can make informed decisions about their route."""


def reviewer_node(state: AgentState) -> Dict[str, Any]:
    """Generate route overview with full state access.
    
    This node creates a comprehensive summary of the planned route by giving
    the LLM direct access to all state data. The LLM can intelligently analyze
    and present the route information based on the current confirmation status.
    
    Args:
        state: Current agent state with route, segments, and requirements
        
    Returns:
        Dictionary with overview message to send to user
        
    Raises:
        ValueError: If required data is missing from state
    """
    # Validate required data is present
    if not state.requirements:
        error_msg = "Overview generation requires validated requirements"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not state.route:
        error_msg = "Overview generation requires a calculated route"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not state.segments:
        error_msg = "Overview generation requires generated segments"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    mode = "confirmed" if state.user_confirmed else "asking"
    logger.info(f"Generating route overview (mode: {mode})")
    
    # Check for recent optimizer changes
    recent_changes = _check_for_recent_changes(state)
    
    # Serialize the state for the LLM
    state_summary = f"""Current Route State:

Requirements:
- Origin: {state.requirements.origin.name} ({state.requirements.origin.coordinates})
- Destination: {state.requirements.destination.name} ({state.requirements.destination.coordinates})
- Daily Distance Target: {state.requirements.daily_distance_km} km
- Intermediate Stops: {len(state.requirements.intermediates)}
- Context: {state.requirements.context or 'None provided'}

Overall Route:
- Total Distance: {state.route.distance / 1000:.1f} km
- Total Elevation Gain: {state.route.elevation_gain} m
- Number of Days: {len(state.segments)}

Daily Segments:
"""
    
    for seg in state.segments:
        accommodation_count = len(seg.accommodation_options)
        state_summary += f"""
Day {seg.day}:
  - Distance: {seg.route.distance / 1000:.1f} km
  - Elevation Gain: {seg.route.elevation_gain} m
  - Start: {seg.route.origin.name}
  - End: {seg.route.destination.name}
  - Accommodation Options: {accommodation_count}
"""
    
    state_summary += f"\nUser Confirmed: {state.user_confirmed}"
    
    # Add recent changes context if any
    if recent_changes:
        state_summary += f"\n\nRecent Actions Taken: {recent_changes}"
        state_summary += "\nNote: If the user asked a question, make sure to answer it directly based on the current state data."
    else:
        state_summary += "\n\nThis is the initial route overview - no changes have been made yet."
    
    try:
        # Generate the overview with full state context
        response = _llm.invoke(
            [HumanMessage(content=state_summary)],
            system=REVIEWER_SYSTEM_PROMPT,
        )
        
        logger.info(f"Route overview generated (mode: {mode})")
        
        return {"messages": [response]}
        
    except Exception as e:
        error_msg = f"Overview generation failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e