"""
Links component - Data models.

Spec refs: Link management
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.entities import ContentVisibility, LinkItem, LinkStatus

# --- Validation Errors ---


@dataclass(frozen=True)
class LinkValidationError:
    """Link validation error."""

    code: str
    message: str
    field: str | None = None


# --- Input Models ---


@dataclass(frozen=True)
class CreateLinkInput:
    """Input for creating a link."""

    title: str
    slug: str
    url: str
    icon: str | None = None
    status: LinkStatus = "active"
    position: int = 0
    visibility: ContentVisibility = "public"
    group_id: UUID | None = None


@dataclass(frozen=True)
class UpdateLinkInput:
    """Input for updating a link."""

    link_id: UUID
    title: str | None = None
    slug: str | None = None
    url: str | None = None
    icon: str | None = None
    status: LinkStatus | None = None
    position: int | None = None
    visibility: ContentVisibility | None = None
    group_id: UUID | None = None


@dataclass(frozen=True)
class DeleteLinkInput:
    """Input for deleting a link."""

    link_id: UUID


@dataclass(frozen=True)
class GetLinkInput:
    """Input for getting a link."""

    link_id: UUID


# --- Output Models ---


@dataclass(frozen=True)
class LinkOperationOutput:
    """Output from link operation."""

    link: LinkItem | None
    errors: tuple[LinkValidationError, ...]
    success: bool


@dataclass(frozen=True)
class LinkListOutput:
    """Output from list operation."""

    links: tuple[LinkItem, ...]
    total: int
