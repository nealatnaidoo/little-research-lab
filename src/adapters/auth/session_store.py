"""In-memory session store adapter.

This adapter implements SessionStorePort for the auth component.
For production, consider SQLite or Redis backed implementations.
"""

from uuid import UUID

from src.domain.entities import Session


class InMemorySessionStore:
    """In-memory session storage - suitable for single-process deployments."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get(self, token: str) -> Session | None:
        """Get session by token."""
        return self._sessions.get(token)

    def save(self, token: str, session: Session) -> None:
        """Save session with token as key."""
        self._sessions[token] = session

    def delete(self, token: str) -> None:
        """Delete session by token."""
        self._sessions.pop(token, None)

    def delete_by_user(self, user_id: UUID) -> int:
        """Delete all sessions for a user. Returns count deleted."""
        tokens_to_remove = [k for k, v in self._sessions.items() if str(v.user_id) == str(user_id)]
        for token in tokens_to_remove:
            del self._sessions[token]
        return len(tokens_to_remove)

    def clear(self) -> None:
        """Clear all sessions - useful for testing."""
        self._sessions.clear()
