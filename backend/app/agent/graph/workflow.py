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
from app.agent.nodes.writer import itinerary_writer_node
from app.agent.graph.routing import route_planner
from app.agent.graph.routing import route_optimiser
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
    
    Phase 3 - Optimization (Agentic):
        - Should Optimize: Checks if route needs improvement
        - Optimizer: Analyzes route and makes modifications via tools
        - Optimizer Tools: Executes route modification tools
    
    Phase 4 - Output (Generative):
        - Writer: Creates friendly itinerary summary
    
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

    # === Phase 3: Route Optimization Nodes ===
    workflow.add_node("optimiser", optimiser_node)
    workflow.add_node("optimiser_tools", ToolNode(OPTIMISATION_TOOLS))

    # === Phase 4: Output Generation ===
    workflow.add_node("writer", itinerary_writer_node)
    
    # === Define Workflow Edges ===
    
    # Entry point
    workflow.set_entry_point("planner")
    
    # Phase 1: Planning - conversational loop
    workflow.add_conditional_edges(
        "planner",
        route_planner,
        {
            "planner_tools": "planner_tools",  # Execute location lookup tools
            "parser": "parser",                 # Validate requirements
            END: END,                           # Wait for user response
        },
    )
    workflow.add_edge("planner_tools", "planner")  # Loop back after tool execution
    
    # Transition to calculation phase
    workflow.add_edge("parser", "calculate_route")
    
    # Phase 2: Calculation - deterministic sequence
    workflow.add_edge("calculate_route", "generate_waypoints")
    workflow.add_edge("generate_waypoints", "find_accommodation")

    # Optimization loop
    workflow.add_conditional_edges(
        "find_accommodation",
        route_optimiser,
        {
            "optimiser_tools": "optimiser_tools",  # Execute modification tools
            "writer": "writer",                    # Optimization complete
        },
    )
    workflow.add_edge("optimiser_tools", "optimiser")  # Loop back after tool execution
    
    # Phase 4: Final output
    workflow.add_edge("writer", END)
    
    # === Compile with Persistence ===
    logger.info("Compiling graph with memory persistence")
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    logger.info("Route planner graph compiled successfully")
    return app


# Create the compiled application
app = create_route_planner_graph()