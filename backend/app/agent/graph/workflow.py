import logging
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from app.agent.schemas.state import AgentState
from app.agent.nodes.logistics import find_accommodation_node
from app.agent.nodes.planner import planner_node, parse_requirements_node
from app.agent.nodes.router import calculate_route_node, calculate_segments_node
from app.agent.nodes.optimiser import optimiser_node
from app.agent.nodes.reviewer import reviewer_node
from app.agent.nodes.writer import itinerary_writer_node
from app.agent.graph.routing import (
    route_planner,
    route_optimiser,
    route_reviewer,
)
from app.tools import get_location
from app.tools import OPTIMISATION_TOOLS

logger = logging.getLogger(__name__)


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
        - Optimizer: Analyzes route, makes modifications, interprets user feedback
        - Optimizer Tools: Executes route modification tools
        - Optimizer: Decides if route is confirmed (calls RouteConfirmed tool)
    
    Phase 4 - Review & Output:
        - Reviewer: Presents overview
          - If NOT confirmed: Asks for confirmation → END (wait for user)
          - If confirmed: Confirms route → Writer
        - [If waiting: User responds → Back to Planner → Optimizer interprets feedback]
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
    workflow.add_node("writer", itinerary_writer_node)
    
    # === Define Workflow Edges ===
    
    # Entry point - always start from planner
    # Planner is smart enough to detect existing state and route appropriately
    workflow.set_entry_point("planner")
    
    # Phase 1: Planning - conversational loop
    workflow.add_conditional_edges(
        "planner",
        route_planner,
        {
            "planner_tools": "planner_tools",  # Execute location lookup tools
            "parser": "parser",                 # Validate requirements
            "optimiser": "optimiser",           # User feedback after review
            END: END,                           # Wait for user response
        },
    )
    workflow.add_edge("planner_tools", "planner")  # Loop back after tool execution
    
    # Transition to calculation phase
    workflow.add_edge("parser", "calculate_route")
    
    # Phase 2: Calculation - deterministic sequence
    workflow.add_edge("calculate_route", "generate_waypoints")
    workflow.add_edge("generate_waypoints", "find_accommodation")

    # Phase 3: Optimization & Confirmation loop
    workflow.add_edge("find_accommodation", "optimiser")  # First time to optimizer
    
    workflow.add_conditional_edges(
        "optimiser",
        route_optimiser,
        {
            "optimiser_tools": "optimiser_tools",  # Execute modification tools
            "reviewer": "reviewer",                # Move to review (confirmed or first time)
        },
    )
    workflow.add_edge("optimiser_tools", "optimiser")  # Loop back after tool execution
    
    # Phase 4: Review & Output
    workflow.add_conditional_edges(
        "reviewer",
        route_reviewer,
        {
            "writer": "writer",  # Route confirmed, generate final itinerary
            END: END,            # Wait for user response
        },
    )
    
    # When user responds after reviewer (and not confirmed):
    # - Conversation resumes at entry point (planner)
    # - Planner will see we have route/segments and route to END
    # - This triggers optimizer on next invoke
    # Actually, we need planner to be smarter or have a different entry point
    
    # Phase 5: Final output
    workflow.add_edge("writer", END)
    
    # === Compile with Persistence ===
    logger.info("Compiling graph with memory persistence")
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    logger.info("Route planner graph compiled successfully")
    return app


# Create the compiled application
app = create_route_planner_graph()