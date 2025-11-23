import operator
from typing import Annotated, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage

from app.models.models import Route, Waypoint, Location


class RouteRequirements(BaseModel):
    """Requirements for route calculation.
    
    This schema is used as a tool for the LLM to submit
    all gathered information about the route.
    """
    
    origin: Location = Field(
        description="Starting location with coordinates and name"
    )
    destination: Location = Field(
        description="Ending location with coordinates and name"
    )
    intermediates: List[Location] = Field(
        default_factory=list,
        description="Optional intermediate stops along the route"
    )
    daily_distance_km: int = Field(
        gt=0,
        description="Target distance to cover each day in kilometers"
    )
    context: Optional[str] = Field(
        default=None,
        description="Additional context or preferences for the route"
    )


class AgentState(BaseModel):
    """State container for the route planning workflow.
    
    This state is passed between nodes in the LangGraph workflow
    and accumulates information as the planning progresses.
    """
    
    class Config:
        arbitrary_types_allowed = True
    
    # Chat History - accumulated across all interactions
    messages: Annotated[List[BaseMessage], operator.add] = Field(
        default_factory=list,
        description="Conversation history with the user"
    )
    
    # Phase 1: Requirements gathering
    requirements: Optional[RouteRequirements] = Field(
        default=None,
        description="Validated route requirements from the user"
    )
    
    # Phase 2: Route calculation
    route: Optional[Route] = Field(
        default=None,
        description="Calculated route with polyline and distance"
    )
    
    # Phase 3: Waypoint generation
    waypoints: Optional[List[Waypoint]] = Field(
        default=None,
        description="Daily waypoints along the route"
    )