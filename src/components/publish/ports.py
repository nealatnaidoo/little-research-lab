"""Publish component port definitions - protocols for dependencies."""

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.domain.entities import ContentItem, User


class ContentRepoPort(Protocol):
    """Protocol for content repository operations."""

    def get_by_id(self, item_id: UUID) -> ContentItem | None:
        """Retrieve a content item by ID."""
        ...

    def list_items(self, filters: dict[str, Any]) -> list[ContentItem]:
        """List content items matching filters."""
        ...

    def save(self, content: ContentItem) -> ContentItem:
        """Save a content item."""
        ...


class UserRepoPort(Protocol):
    """Protocol for user repository operations."""

    def get_by_id(self, user_id: UUID) -> User | None:
        """Retrieve a user by ID."""
        ...


class PolicyPort(Protocol):
    """Protocol for permission checks."""

    def check_permission(
        self,
        user: User | None,
        user_roles: list[str],
        action: str,
        resource: Any = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Check if user has permission to perform action on resource."""
        ...


class ClockPort(Protocol):
    """Protocol for time operations."""

    def now(self) -> datetime:
        """Return current UTC time."""
        ...
