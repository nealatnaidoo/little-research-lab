"""
Content component input/output models.

Spec refs: E2, E3, E4, SM1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from src.core.entities import ContentItem, ContentStatus, ContentType

# --- Validation Error ---


@dataclass(frozen=True)
class ContentValidationError:
    """Content validation error."""

    code: str
    message: str
    field: str | None = None


# --- Input Models ---


@dataclass(frozen=True)
class CreateContentInput:
    """Input for creating new content."""

    type: ContentType
    title: str
    slug: str
    owner_user_id: UUID
    summary: str = ""
    blocks: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class UpdateContentInput:
    """Input for updating existing content."""

    content_id: UUID
    updates: dict[str, Any]


@dataclass(frozen=True)
class GetContentInput:
    """Input for retrieving content."""

    content_id: UUID | None = None
    slug: str | None = None
    content_type: ContentType | None = None


@dataclass(frozen=True)
class ListContentInput:
    """Input for listing content with filters."""

    content_type: ContentType | None = None
    status: ContentStatus | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class TransitionContentInput:
    """Input for content state transitions."""

    content_id: UUID
    to_status: ContentStatus
    publish_at: datetime | None = None


@dataclass(frozen=True)
class DeleteContentInput:
    """Input for deleting content."""

    content_id: UUID


# --- Output Models ---


@dataclass(frozen=True)
class ContentOutput:
    """Output containing a single content item."""

    content: ContentItem | None
    errors: list[ContentValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class ContentListOutput:
    """Output containing a list of content items."""

    items: list[ContentItem]
    total: int
    limit: int
    offset: int
    errors: list[ContentValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class ContentOperationOutput:
    """Output for content operations (create, update, delete, transition)."""

    content: ContentItem | None = None
    errors: list[ContentValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class GetRelatedInput:
    """Input for getting related articles."""

    content_id: UUID
    limit: int = 3


@dataclass(frozen=True)
class RelatedArticlesOutput:
    """Output containing related articles."""

    articles: list[ContentItem] = field(default_factory=list)
    errors: list[ContentValidationError] = field(default_factory=list)
    success: bool = True
