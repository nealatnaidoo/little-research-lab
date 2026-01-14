"""
Links component - Navigation and social link management.

Handles link CRUD operations.

Shell Layer - handles I/O and error conversion.
"""

from __future__ import annotations

from typing import Any

from ._impl import LinkService
from .models import (
    CreateLinkInput,
    DeleteLinkInput,
    GetLinkInput,
    LinkListOutput,
    LinkOperationOutput,
    LinkValidationError,
    UpdateLinkInput,
)

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
        errors=tuple(errors),
        success=link is not None,
    )


def run_update(
    input_data: UpdateLinkInput,
    service: LinkService,
) -> LinkOperationOutput:
    """Update an existing link."""
    # Build updates dict from non-None fields
    updates: dict[str, Any] = {}
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
        errors=tuple(errors),
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
        errors=tuple(errors),
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
            errors=(
                LinkValidationError(
                    code="link_not_found",
                    message=f"Link with ID {input_data.link_id} not found",
                ),
            ),
            success=False,
        )

    return LinkOperationOutput(
        link=link,
        errors=(),
        success=True,
    )


def run_list(service: LinkService) -> LinkListOutput:
    """List all links."""
    links = service.get_all()
    return LinkListOutput(
        links=tuple(links),
        total=len(links),
    )
