import logging

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.api.deps import SessionManagerDep
from app.api.services.streaming import stream_chat_response
from app.models import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats")

@router.post("/stream")
async def chat_stream(session_manager: SessionManagerDep, request: ChatRequest) -> EventSourceResponse:
    """Stream chat responses using Server-Sent Events.
    
    This endpoint streams the conversation in real-time using SSE.
    The client will receive events as the AI processes the request.
    
    Args:
        request: ChatRequest with message and optional session_id
        
    Returns:
        StreamingResponse with SSE events
    """

    print("herer")
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
