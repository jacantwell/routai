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

router = APIRouter(prefix="/chat")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.
    
    Returns:
        HealthResponse with current status
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )


@router.post("/sessions", response_model=Dict[str, str])
async def create_session():
    """Create a new conversation session.
    
    Returns:
        Dictionary with the new session_id
    """
    session_id = session_manager.create_session()
    logger.info(f"Created session via API: {session_id}")
    
    return {
        "session_id": session_id,
        "message": "Session created successfully"
    }


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """Get information about a session.
    
    Args:
        session_id: The session ID to look up
        
    Returns:
        SessionInfo with session details
        
    Raises:
        HTTPException: If session not found
    """
    info = session_manager.get_session_info(session_id)
    
    if not info:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    # Get state to check progress
    try:
        state = get_session_state(session_id)
        info["has_requirements"] = state["requirements"] is not None
        info["has_route"] = state["route"] is not None
        info["has_waypoints"] = state["waypoints"] is not None
    except Exception as e:
        logger.warning(f"Could not get state for session {session_id}: {str(e)}")
        info["has_requirements"] = False
        info["has_route"] = False
        info["has_waypoints"] = False
    
    return SessionInfo(**info)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session.
    
    Args:
        session_id: The session ID to delete
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If session not found
    """
    success = session_manager.delete_session(session_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return {
        "message": f"Session {session_id} deleted successfully"
    }


@router.get("/sessions/{session_id}/state", response_model=SessionState)
async def get_state(session_id: str):
    """Get the current state of a session.
    
    Args:
        session_id: The session ID
        
    Returns:
        SessionState with current state details
        
    Raises:
        HTTPException: If session not found
    """
    try:
        state = get_session_state(session_id)
        
        # Get session info for metadata
        info = session_manager.get_session_info(session_id)
        if not info:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        return SessionState(
            session_id=session_id,
            message_count=state["message_count"],
            requirements=state["requirements"],
            route=state["route"],
            waypoints=state["waypoints"],
            last_updated=info["last_updated"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting state: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving session state: {str(e)}"
        )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat responses using Server-Sent Events.
    
    This endpoint streams the conversation in real-time using SSE.
    The client will receive events as the AI processes the request.
    
    Args:
        request: ChatRequest with message and optional session_id
        
    Returns:
        StreamingResponse with SSE events
        
    Example client code:
        ```javascript
        const eventSource = new EventSource('/chat/stream', {
            method: 'POST',
            body: JSON.stringify({message: "Plan a route", session_id: "..."})
        });
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data);
        };
        ```
    """
    # Create or get session
    session_id = request.session_id
    if not session_id:
        session_id = session_manager.create_session()
        logger.info(f"Created new session for streaming: {session_id}")
    else:
        if not session_manager.session_exists(session_id):
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
    
    logger.info(f"Starting chat stream for session {session_id}")
    
    # Return SSE stream
    return EventSourceResponse(
        stream_chat_response(request.message, session_id)
    )


@router.get("/sessions")
async def list_sessions():
    """List all active sessions.
    
    Returns:
        List of session information
    """
    sessions = session_manager.get_all_sessions()
    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@router.get("/stats")
async def get_stats():
    """Get statistics about the service.
    
    Returns:
        Dictionary with service statistics
    """
    stats = session_manager.get_stats()
    return {
        "timestamp": datetime.utcnow(),
        **stats
    }