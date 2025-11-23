import logging
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from app.agent.schemas.state import AgentState
from app.agent.nodes.planner import planner_node, parse_requirements_node
from app.agent.nodes.router import calculate_route_node, generate_waypoints_node
from app.agent.nodes.writer import itinerary_writer_node
from app.agent.graph.routing import route_planner
from app.tools.route import get_location

logger = logging.getLogger(__name__)


def create_route_planner_graph() -> CompiledStateGraph:
    """Create and compile the route planner workflow graph.
    
    The workflow consists of three main phases:
    
    Phase 1 - Planning (Conversational):
        - Planner: Gathers requirements from user
        - Planner Tools: Executes location lookups
        - Parser: Validates and stores requirements
    
    Phase 2 - Calculation (Deterministic):
        - Calculate Route: Gets route from Google Routes API
        - Generate Waypoints: Divides route into daily segments
    
    Phase 3 - Output (Generative):
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
    workflow.add_node("generate_waypoints", generate_waypoints_node)
    
    # === Phase 3: Output Generation ===
    workflow.add_node("writer", itinerary_writer_node)
    
    # === Define Workflow Edges ===
    
    # Entry point
    workflow.set_entry_point("planner")
    
    # Planning phase - conversational loop
    workflow.add_conditional_edges(
        "planner",
        route_planner,
        {
            "planner_tools": "planner_tools",  # Execute tools
            "parser": "parser",                 # Validate requirements
            END: END,                           # Wait for user response
        },
    )
    workflow.add_edge("planner_tools", "planner")  # Loop back after tools
    
    # Transition to deterministic phase
    workflow.add_edge("parser", "calculate_route")
    
    # Calculation phase - deterministic sequence
    workflow.add_edge("calculate_route", "generate_waypoints")
    workflow.add_edge("generate_waypoints", "writer")
    
    # Final output
    workflow.add_edge("writer", END)
    
    # === Compile with Persistence ===
    logger.info("Compiling graph with memory persistence")
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    logger.info("Route planner graph compiled successfully")
    return app


# Create the compiled application
app = create_route_planner_graph()