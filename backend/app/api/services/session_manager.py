import logging
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Dict

from langchain_core.runnables import RunnableConfig

from app.agent.graph.workflow import app
from app.models.state import AgentState

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages conversation sessions in memory.

    This is a simple in-memory implementation. For production,
    replace with Redis or a database-backed implementation.
    """

    def __init__(self):
        self._sessions: Dict[str, Dict] = {}
        self._lock = Lock()
        logger.info("SessionManager initialized with in-memory storage")

    def create_session(self) -> str:
        """Create a new session and return its ID.

        Returns:
            str: The new session ID
        """
        session_id = str(uuid.uuid4())

        with self._lock:
            self._sessions[session_id] = {
                "created_at": datetime.now(timezone.utc),
                "last_updated": datetime.now(timezone.utc),
                "message_count": 0,
            }

        logger.info(f"Created new session: {session_id}")
        return session_id

    def get_session_state(self, session_id: str) -> AgentState:
        """Get the current state of a session.

        Args:
            session_id: The session ID

        Returns:
            Dictionary with current state

        Raises:
            ValueError: If session not found
        """
        if not self.session_exists(session_id):
            raise ValueError(f"Session {session_id} not found")

        config = RunnableConfig(configurable={"thread_id": session_id})

        try:
            # Get the current state from LangGraph
            state = app.get_state(config)

            return AgentState.model_validate(state.values)

        except Exception as e:
            logger.error(f"Error getting state for session {session_id}: {str(e)}")
            raise

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists.

        Args:
            session_id: The session ID to check

        Returns:
            True if session exists, False otherwise
        """
        with self._lock:
            return session_id in self._sessions
