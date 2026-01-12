from datetime import datetime
from typing import Protocol

from src.domain.entities import Invite, User


class InviteRepoPort(Protocol):
    def save(self, invite: Invite) -> Invite: ...
    def get_by_token_hash(self, token_hash: str) -> Invite | None: ...


class AuthAdapterPort(Protocol):
    def hash_password(self, plain: str) -> str: ...


class UserRepoPort(Protocol):
    def get_by_email(self, email: str) -> User | None: ...
    def save(self, user: User) -> User: ...


class TimePort(Protocol):
    """Port for time operations - enables deterministic testing."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...
