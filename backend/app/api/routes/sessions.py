import logging
from typing import Dict

from fastapi import APIRouter, HTTPException

from app.api.deps import SessionManagerDep
from app.models import AgentState, Route, Segment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions")


@router.post("/", response_model=Dict[str, str])
async def create_session(session_manager: SessionManagerDep):
    """Create a new conversation session.

    Returns:
        Dictionary with the new session_id
    """
    session_id = session_manager.create_session()
    logger.info(f"Created session via API: {session_id}")

    return {"session_id": session_id, "message": "Session created successfully"}


@router.get("/{session_id}/state", response_model=AgentState)
async def get_state(session_manager: SessionManagerDep, session_id: str) -> AgentState:
    """Get the current state of a session.

    Args:
        session_id: The session ID

    Returns:
        AgentState with current state details

    Raises:
        HTTPException: If session not found
    """
    try:
        state = session_manager.get_session_state(session_id)
        return state
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get("/{session_id}/route", response_model=Route)
def get_route(session_manager: SessionManagerDep, session_id: str):
    """Get the current route of a session.

    Args:
        session_id: The session ID

    Returns:
        Route

    Raises:
        HTTPException: If session not found
    """
    try:
        state = session_manager.get_session_state(session_id)

        return state.route
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get("/{session_id}/segments", response_model=list[Segment])
def get_segments(session_manager: SessionManagerDep, session_id: str):
    """Get the current segments of a session.

    Args:
        session_id: The session ID

    Returns:
        Segments

    Raises:
        HTTPException: If session not found
    """
    try:
        state = session_manager.get_session_state(session_id)

        return state.segments
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)
