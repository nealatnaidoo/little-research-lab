from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.entities import Session, User


class UserRepoPort(Protocol):
    def get_by_email(self, email: str) -> User | None: ...
    def get_by_id(self, user_id: object) -> User | None: ...
    def save(self, user: User) -> User: ...
    def list_all(self) -> list[User]: ...


class AuthAdapterPort(Protocol):
    def verify_password(self, plain: str, hashed: str) -> bool: ...
    def hash_password(self, plain: str) -> str: ...
    def create_token(self, user_id: object, ttl_minutes: int) -> str: ...


class TimePort(Protocol):
    """Port for time operations - enables deterministic testing."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...


class SessionStorePort(Protocol):
    """Port for session storage - removes global state from component."""

    def get(self, token: str) -> Session | None:
        """Get session by token."""
        ...

    def save(self, token: str, session: Session) -> None:
        """Save session with token as key."""
        ...

    def delete(self, token: str) -> None:
        """Delete session by token."""
        ...

    def delete_by_user(self, user_id: UUID) -> int:
        """Delete all sessions for a user. Returns count deleted."""
        ...
