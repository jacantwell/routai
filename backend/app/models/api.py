from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MessageInput(BaseModel):
    """User message input."""

    content: str = Field(
        ...,
        description="The message content from the user",
        min_length=1,
        max_length=5000,
    )


class ChatRequest(BaseModel):
    """Request to send a message in a conversation."""

    message: str = Field(
        ..., description="The message to send", min_length=1, max_length=5000
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for conversation continuity. If not provided, a new session is created.",
    )


class ChatResponse(BaseModel):
    """Response from a chat message."""

    session_id: str = Field(..., description="Session ID for this conversation")
    message: str = Field(..., description="The assistant's response")
    message_type: str = Field(
        default="ai", description="Type of message (ai, human, tool)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata about the response"
    )


class SessionInfo(BaseModel):
    """Information about a conversation session."""

    session_id: str
    created_at: datetime
    last_updated: datetime
    message_count: int
    has_requirements: bool
    has_route: bool
    has_waypoints: bool


class SessionState(BaseModel):
    """Current state of a session."""

    session_id: str
    message_count: int
    requirements: Optional[Dict[str, Any]] = None
    route: Optional[Dict[str, Any]] = None
    waypoints: Optional[List[Dict[str, Any]]] = None
    last_updated: datetime


class StreamEvent(BaseModel):
    """A single event in the stream."""

    event: str = Field(
        ..., description="Event type (message, state_update, complete, error)"
    )
    data: Dict[str, Any] = Field(..., description="Event data")
    session_id: str


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: Optional[str] = None
    session_id: Optional[str] = None
