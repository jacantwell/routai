import operator
from typing import Annotated, List, Optional

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field, ConfigDict

from app.models import Location, Route, Segment

class RouteRequirements(BaseModel):
    """Requirements for route calculation.

    This schema is used as a tool for the LLM to submit
    all gathered information about the route.
    """

    origin: Location = Field(description="Starting location with coordinates and name")
    destination: Location = Field(
        description="Ending location with coordinates and name"
    )
    intermediates: List[Location] = Field(
        default_factory=list, description="Optional intermediate stops along the route"
    )
    daily_distance_km: int = Field(
        gt=0, description="Target distance to cover each day in kilometers"
    )
    context: Optional[str] = Field(
        default=None, description="Additional context or preferences for the route"
    )


class AgentState(BaseModel):
    """State container for the route planning workflow.

    This state is passed between nodes in the LangGraph workflow
    and accumulates information as the planning progresses.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)  

    # Chat History - accumulated across all interactions
    messages: Annotated[List[BaseMessage], operator.add] = Field(
        default_factory=list, description="Conversation history with the user"
    )

    # Phase 1: Requirements gathering
    requirements: Optional[RouteRequirements] = Field(
        default=None, description="Validated route requirements from the user"
    )

    # Phase 2: The overall route - from requirements.origin to requirements.destination
    route: Optional[Route] = Field(
        default=None,
        description="Calculated overall route from requirements.origin to requirements.destination",
    )

    # Phase 3:  List of segments that when connected form the overall route
    segments: Optional[List[Segment]] = Field(
        default=None, description="Daily routes in ascending order."
    )

    # Phase 4: User confirmation
    user_confirmed: bool = Field(
        default=False, description="Whether user has confirmed the route overview"
    )

    # True when reviewer asks question, False when user responds
    awaiting_user_response: bool = False
    
    # True after first optimization pass
    critical_optimization_done: bool = False
