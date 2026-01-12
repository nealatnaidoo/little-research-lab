from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.entities import CollaborationGrant, ContentItem, User


class CollabRepoPort(Protocol):
    def get_by_content_and_user(
        self, content_id: UUID, user_id: UUID
    ) -> CollaborationGrant | None: ...
    def list_by_content(self, content_id: UUID) -> list[CollaborationGrant]: ...
    def save(self, grant: CollaborationGrant) -> CollaborationGrant: ...
    def delete(self, grant_id: UUID) -> None: ...


class ContentRepoPort(Protocol):
    def get_by_id(self, content_id: UUID) -> ContentItem | None: ...


class UserRepoPort(Protocol):
    def get_by_email(self, email: str) -> User | None: ...
    def get_by_id(self, user_id: UUID) -> User | None: ...


class TimePort(Protocol):
    """Port for time operations - enables deterministic testing."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...
