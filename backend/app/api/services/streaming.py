import json
import logging
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from app.agent.graph.workflow import app


logger = logging.getLogger(__name__)


async def stream_chat_response(
    message: str, session_id: str
) -> AsyncGenerator[str, None]:
    """Stream chat responses using Server-Sent Events.

    Args:
        message: The user's message
        session_id: The session ID for conversation continuity

    Yields:
        SSE-formatted strings with event data
    """
    try:

        # Create the config for LangGraph with the session ID
        config = RunnableConfig(configurable={"thread_id": session_id})

        logger.info(f"Starting stream for session {session_id}")

        # Track if we've sent any data
        sent_data = False

        # Stream events from the graph
        async for event in app.astream(
            {"messages": [HumanMessage(content=message)]}, config, stream_mode="values"
        ):
            sent_data = True

            # Extract relevant information from the event
            messages = event.get("messages", [])

            if messages:
                last_message = messages[-1]

                # Only stream AI messages
                if hasattr(last_message, "type"):
                    message_type = last_message.type

                    if message_type == "ai":
                        event_data = {
                            "event": "message",
                            "data": {
                                "content": last_message.content,
                                "type": "ai",
                                "session_id": session_id,
                            },
                        }

                        yield f"data: {json.dumps(event_data)}\n\n"
                        logger.debug(f"Streamed AI message for session {session_id}")

            # Stream state updates if available
            state_data = {}
            if event.get("requirements"):
                state_data["has_requirements"] = True
            if event.get("route"):
                state_data["has_route"] = True
                state_data["distance_km"] = event["route"].distance / 1000
            if event.get("waypoints"):
                state_data["has_waypoints"] = True
                state_data["num_days"] = len(event["waypoints"])

            if state_data:
                state_event = {
                    "event": "state_update",
                    "data": {
                        **state_data,
                        "session_id": session_id
                    }
                }
                yield f"data: {json.dumps(state_event)}\n\n"

        # Send completion event
        completion_event = {
            "event": "complete",
            "data": {
                "session_id": session_id,
                "message": "Stream completed successfully",
            },
        }
        yield f"data: {json.dumps(completion_event)}\n\n"

        logger.info(f"Stream completed for session {session_id}")

    except Exception as e:
        logger.error(
            f"Error in stream for session {session_id}: {str(e)}", exc_info=True
        )

        # Send error event
        error_event = {
            "event": "error",
            "data": {"error": str(e), "session_id": session_id},
        }
        yield f"data: {json.dumps(error_event)}\n\n"
