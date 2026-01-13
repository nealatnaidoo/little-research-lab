"""
Links component - Navigation and social link management.

Handles link CRUD operations.

Shell Layer - handles I/O and error conversion.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.entities import ContentVisibility, LinkItem, LinkStatus

from ._impl import LinkService, LinkValidationError

# --- Component Models (Shell Layer) ---


@dataclass
class LinkOperationOutput:
    """Output from link operation."""

    link: LinkItem | None
    errors: list[LinkValidationError]
    success: bool


@dataclass
class LinkListOutput:
    """Output from list operation."""

    links: list[LinkItem]
    total: int


@dataclass
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


@dataclass
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


@dataclass
class DeleteLinkInput:
    """Input for deleting a link."""

    link_id: UUID


@dataclass
class GetLinkInput:
    """Input for getting a link."""

    link_id: UUID


# --- Shell Layer Functions ---


def run_create(
    input_data: CreateLinkInput,
    service: LinkService,
) -> LinkOperationOutput:
    """Create a new link."""
    link, errors = service.create(
        title=input_data.title,
        slug=input_data.slug,
        url=input_data.url,
        icon=input_data.icon,
        status=input_data.status,
        position=input_data.position,
        visibility=input_data.visibility,
        group_id=input_data.group_id,
    )

    return LinkOperationOutput(
        link=link,
        errors=errors,
        success=link is not None,
    )


def run_update(
    input_data: UpdateLinkInput,
    service: LinkService,
) -> LinkOperationOutput:
    """Update an existing link."""
    # Build updates dict from non-None fields
    updates = {}
    if input_data.title is not None:
        updates["title"] = input_data.title
    if input_data.slug is not None:
        updates["slug"] = input_data.slug
    if input_data.url is not None:
        updates["url"] = input_data.url
    if input_data.icon is not None:
        updates["icon"] = input_data.icon
    if input_data.status is not None:
        updates["status"] = input_data.status
    if input_data.position is not None:
        updates["position"] = input_data.position
    if input_data.visibility is not None:
        updates["visibility"] = input_data.visibility
    if input_data.group_id is not None:
        updates["group_id"] = input_data.group_id

    link, errors = service.update(input_data.link_id, updates)

    return LinkOperationOutput(
        link=link,
        errors=errors,
        success=link is not None,
    )


def run_delete(
    input_data: DeleteLinkInput,
    service: LinkService,
) -> LinkOperationOutput:
    """Delete a link."""
    success, errors = service.delete(input_data.link_id)

    return LinkOperationOutput(
        link=None,
        errors=errors,
        success=success,
    )


def run_get(
    input_data: GetLinkInput,
    service: LinkService,
) -> LinkOperationOutput:
    """Get a link by ID."""
    link = service.get_by_id(input_data.link_id)

    if link is None:
        return LinkOperationOutput(
            link=None,
            errors=[
                LinkValidationError(
                    code="link_not_found",
                    message=f"Link with ID {input_data.link_id} not found",
                )
            ],
            success=False,
        )

    return LinkOperationOutput(
        link=link,
        errors=[],
        success=True,
    )


def run_list(service: LinkService) -> LinkListOutput:
    """List all links."""
    links = service.get_all()
    return LinkListOutput(
        links=links,
        total=len(links),
    )
