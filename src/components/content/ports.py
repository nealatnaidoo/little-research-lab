"""
Content component port definitions.

Spec refs: E2, E3, E4, SM1
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.core.entities import ContentItem, ContentStatus, ContentType


class ContentRepoPort(Protocol):
    """Repository interface for content persistence."""

    def get_by_id(self, item_id: UUID) -> ContentItem | None:
        """Get content by ID."""
        ...

    def get_by_slug(self, slug: str, item_type: str) -> ContentItem | None:
        """Get content by slug and type."""
        ...

    def save(self, content: ContentItem) -> ContentItem:
        """Save or update content."""
        ...

    def delete(self, item_id: UUID) -> None:
        """Delete content by ID."""
        ...

    def list(
        self,
        *,
        content_type: ContentType | None = None,
        status: ContentStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ContentItem], int]:
        """List content with filters. Returns (items, total_count)."""
        ...


class RulesPort(Protocol):
    """Port for accessing content rules configuration."""

    def get_status_machine(self) -> dict[ContentStatus, list[ContentStatus]]:
        """Get status machine transitions."""
        ...

    def get_publish_guards(self) -> dict[str, Any]:
        """Get publish guard configuration."""
        ...

    def get_allowed_types(self) -> list[ContentType]:
        """Get allowed content types."""
        ...


class TimePort(Protocol):
    """Port for time operations."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...


class AssetResolverPort(Protocol):
    """Port for resolving asset references."""

    def resolve(self, asset_id: UUID) -> bool:
        """Check if an asset exists and is resolvable."""
        ...
