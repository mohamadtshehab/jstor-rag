from __future__ import annotations

import time

from ..contracts.interfaces import ISessionAccess

_SESSION_TTL = 7200  # 2 hours


class SessionAccess(ISessionAccess):
    """In-memory session store.

    Tracks active user sessions keyed by session_id.
    Can be swapped for Redis without touching other components.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}

    async def create_session(
        self, session_id: str, document_id: str
    ) -> None:
        self._sessions[session_id] = {
            "document_id": document_id,
            "created_at": time.time(),
            "messages": [],
        }

    async def get_session(self, session_id: str) -> dict | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if time.time() - session["created_at"] > _SESSION_TTL:
            del self._sessions[session_id]
            return None
        return session

    async def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
