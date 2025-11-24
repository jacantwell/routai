import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from app.agent.graph.routing import (route_after_accommodation,
                                     route_optimiser, route_planner,
                                     route_reviewer)
from app.agent.nodes.logistics import find_accommodation_node
from app.agent.nodes.optimiser import optimiser_node
from app.agent.nodes.planner import parse_requirements_node, planner_node
from app.agent.nodes.reviewer import reviewer_node
from app.agent.nodes.router import (calculate_route_node,
                                    calculate_segments_node)
from app.agent.nodes.writer import itinerary_writer_node
from app.models.state import AgentState
from app.tools import OPTIMISATION_TOOLS, get_location, get_weather

logger = logging.getLogger(__name__)


def determine_entry_point(state: AgentState) -> str:
    """Determine where to enter based on state."""

    # 1. If the route is confirmed, go to writer
    if state.user_confirmed:
        return "writer"

    # 2. If we are waiting for response (flag set by reviewer node previously)
    if state.awaiting_user_response and state.route and not state.user_confirmed:
        # Note: We don't clear the flag here; we let the optimiser node handle the state update
        return "optimiser"

    # 3. Fallback for unexpected states or re-entry without waiting flag
    if state.route and state.requirements:
        return "reviewer"

    # 4. Otherwise, start at planner (initial request)
    return "planner"


def create_route_planner_graph() -> CompiledStateGraph:
    """Create and compile the route planner workflow graph.

    The workflow consists of four main phases:

    Phase 1 - Planning (Conversational):
        - Planner: Gathers requirements from user via conversation
        - Planner Tools: Executes location lookups
        - Parser: Validates and stores requirements

    Phase 2 - Calculation (Deterministic):
        - Calculate Route: Gets route from Google Routes API
        - Generate Waypoints: Divides route into daily segments
        - Find Accommodation: Searches for lodging at each segment endpoint

    Phase 3 - Optimization (Agentic & Confirmation):
        - optimiser: Analyzes route, makes modifications, interprets user feedback
        - optimiser Tools: Executes route modification tools
        - optimiser: Decides if route is confirmed (calls RouteConfirmed tool)

    Phase 4 - Review & Output:
        - Reviewer: Presents overview
          - If NOT confirmed: Asks for confirmation → END (wait for user)
          - If confirmed: Confirms route → Writer
        - [If waiting: User responds → Back to Planner → optimiser interprets feedback]
        - Writer: Creates detailed itinerary when confirmed

    Returns:
        Compiled LangGraph workflow with memory persistence
    """
    logger.info("Building route planner workflow graph")

    # Initialize the graph
    workflow = StateGraph(AgentState)

    # === Phase 1: Planning Nodes ===
    workflow.add_node("planner", planner_node)
    workflow.add_node("planner_tools", ToolNode([get_location]))
    workflow.add_node("parser", parse_requirements_node)

    # === Phase 2: Route Calculation Nodes ===
    workflow.add_node("calculate_route", calculate_route_node)
    workflow.add_node("generate_waypoints", calculate_segments_node)
    workflow.add_node("find_accommodation", find_accommodation_node)

    # === Phase 3: Optimization & Confirmation ===
    workflow.add_node("optimiser", optimiser_node)
    workflow.add_node("optimiser_tools", ToolNode(OPTIMISATION_TOOLS))

    # === Phase 4: Review & Output ===
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("reviewer_tools", ToolNode([get_weather]))
    workflow.add_node("writer", itinerary_writer_node)

    # === Define Workflow Edges ===

    workflow.set_conditional_entry_point(determine_entry_point)

    workflow.add_conditional_edges(
        "planner",
        route_planner,
        {
            "planner_tools": "planner_tools",  # Execute location lookup tools
            "parser": "parser",  # Validate requirements
            "optimiser": "optimiser",  # User feedback after review
            END: END,  # Wait for user response
        },
    )
    workflow.add_edge("planner_tools", "planner")  # Loop back after tool execution

    # Transition to calculation phase
    workflow.add_edge("parser", "calculate_route")

    # Phase 2: Calculation - deterministic sequence
    workflow.add_edge("calculate_route", "generate_waypoints")
    workflow.add_edge("generate_waypoints", "find_accommodation")

    workflow.add_conditional_edges(
        "find_accommodation",
        route_after_accommodation,
        {
            "optimiser": "optimiser",
            "reviewer": "reviewer",
        },
    )

    workflow.add_conditional_edges(
        "optimiser",
        route_optimiser,
        {
            "optimiser_tools": "optimiser_tools",  # Execute modification tools
            "reviewer": "reviewer",  # Move to review (confirmed or first time)
        },
    )
    workflow.add_edge("optimiser_tools", "optimiser")  # Loop back after tool execution

    # Phase 4: Review & Output
    workflow.add_conditional_edges(
        "reviewer",
        route_reviewer,
        {
            "reviewer_tools": "reviewer_tools",  # Tool execution (get_weather)
            "writer": "writer",  # Final transition after confirmation
            END: END,  # Wait for user response
        },
    )

    workflow.add_edge("reviewer_tools", "reviewer")  # Loop back after tool execution
    workflow.add_edge(
        "writer", END
    )  # Add the final edge to complete the successful path

    # === Compile with Persistence ===
    logger.info("Compiling graph with memory persistence")
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    logger.info("Route planner graph compiled successfully")
    return app


# Create the compiled application
app = create_route_planner_graph()
