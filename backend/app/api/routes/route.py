"""API routes for the bikepacking route planner."""

import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.api.models.models import (
    ChatRequest,
    ChatResponse,
    SessionInfo,
    SessionState,
    HealthResponse,
    ErrorResponse,
)
from app.api.services.session_manager import session_manager
from app.api.services.streaming import stream_chat_response, get_session_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/routes")

@router.get("/{session_id}")
def get_route(session_id):
    """Get the current route of a session.
    
    Args:
        session_id: The session ID
        
    Returns:
        Route
        
    Raises:
        HTTPException: If session not found
    """
    try:
        state = get_session_state(session_id)

        return state.route
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)
