"""In-memory session management for conversations."""

import uuid
import logging
from typing import Dict, Optional, List
from datetime import datetime
from collections import defaultdict
from threading import Lock

from app.agent.schemas.state import AgentState

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
                "created_at": datetime.utcnow(),
                "last_updated": datetime.utcnow(),
                "message_count": 0,
            }
        
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get information about a session.
        
        Args:
            session_id: The session ID to look up
            
        Returns:
            Dictionary with session info, or None if not found
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
            if not session:
                return None
            
            return {
                "session_id": session_id,
                "created_at": session["created_at"],
                "last_updated": session["last_updated"],
                "message_count": session["message_count"],
            }
    
    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists.
        
        Args:
            session_id: The session ID to check
            
        Returns:
            True if session exists, False otherwise
        """
        with self._lock:
            return session_id in self._sessions
    
    def update_session(self, session_id: str):
        """Update session metadata after interaction.
        
        Args:
            session_id: The session to update
        """
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["last_updated"] = datetime.utcnow()
                self._sessions[session_id]["message_count"] += 1
                logger.debug(f"Updated session {session_id}")
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session.
        
        Args:
            session_id: The session to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Deleted session: {session_id}")
                return True
            return False
    
    def get_all_sessions(self) -> List[Dict]:
        """Get info for all sessions.
        
        Returns:
            List of session info dictionaries
        """
        with self._lock:
            return [
                {
                    "session_id": sid,
                    **session_data
                }
                for sid, session_data in self._sessions.items()
            ]
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours.
        
        Args:
            max_age_hours: Maximum age of sessions to keep
        """
        now = datetime.utcnow()
        to_delete = []
        
        with self._lock:
            for session_id, data in self._sessions.items():
                age = (now - data["last_updated"]).total_seconds() / 3600
                if age > max_age_hours:
                    to_delete.append(session_id)
            
            for session_id in to_delete:
                del self._sessions[session_id]
        
        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} old sessions")
    
    def get_stats(self) -> Dict:
        """Get statistics about current sessions.
        
        Returns:
            Dictionary with session statistics
        """
        with self._lock:
            if not self._sessions:
                return {
                    "total_sessions": 0,
                    "total_messages": 0,
                    "avg_messages_per_session": 0
                }
            
            total_messages = sum(
                s["message_count"] for s in self._sessions.values()
            )
            
            return {
                "total_sessions": len(self._sessions),
                "total_messages": total_messages,
                "avg_messages_per_session": total_messages / len(self._sessions)
            }


# Global session manager instance
session_manager = SessionManager()