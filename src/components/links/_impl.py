"""
LinkService - Link management for navigation and social links.

Handles link creation, updates, and validation.

Functional Core - pure business logic.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from src.domain.entities import ContentVisibility, LinkItem, LinkStatus

from .models import LinkValidationError
from .ports import LinkRepoPort

# --- Validation Functions ---


def validate_link_data(
    title: str | None = None,
    slug: str | None = None,
    url: str | None = None,
) -> list[LinkValidationError]:
    """Validate link data."""
    errors: list[LinkValidationError] = []

    if title is not None:
        if not title or not title.strip():
            errors.append(
                LinkValidationError(
                    code="title_required",
                    message="Title is required",
                    field="title",
                )
            )
        elif len(title) > 200:
            errors.append(
                LinkValidationError(
                    code="title_too_long",
                    message="Title must be 200 characters or less",
                    field="title",
                )
            )

    if slug is not None:
        if not slug or not slug.strip():
            errors.append(
                LinkValidationError(
                    code="slug_required",
                    message="Slug is required",
                    field="slug",
                )
            )
        elif len(slug) > 100:
            errors.append(
                LinkValidationError(
                    code="slug_too_long",
                    message="Slug must be 100 characters or less",
                    field="slug",
                )
            )

    if url is not None:
        if not url or not url.strip():
            errors.append(
                LinkValidationError(
                    code="url_required",
                    message="URL is required",
                    field="url",
                )
            )
        elif not url.strip().startswith(("http://", "https://")):
            errors.append(
                LinkValidationError(
                    code="url_invalid_scheme",
                    message="URL must start with http:// or https://",
                    field="url",
                )
            )

    return errors


# --- Link Service ---


class LinkService:
    """
    Link service.

    Manages navigation and social links.
    """

    def __init__(self, repo: LinkRepoPort) -> None:
        """Initialize service."""
        self._repo = repo

    def get_all(self) -> list[LinkItem]:
        """Get all links."""
        return self._repo.get_all()

    def get_by_id(self, link_id: UUID) -> LinkItem | None:
        """Get link by ID."""
        links = self._repo.get_all()
        return next((link for link in links if link.id == link_id), None)

    def create(
        self,
        title: str,
        slug: str,
        url: str,
        icon: str | None = None,
        status: LinkStatus = "active",
        position: int = 0,
        visibility: ContentVisibility = "public",
        group_id: UUID | None = None,
    ) -> tuple[LinkItem | None, list[LinkValidationError]]:
        """
        Create a new link.

        Returns:
            Tuple of (link, errors). Link is None if validation fails.
        """
        # Validate input
        errors = validate_link_data(title=title, slug=slug, url=url)
        if errors:
            return None, errors

        # Check for duplicate slug
        existing_links = self._repo.get_all()
        if any(link.slug == slug for link in existing_links):
            return None, [
                LinkValidationError(
                    code="slug_duplicate",
                    message=f"Link with slug '{slug}' already exists",
                    field="slug",
                )
            ]

        # Create link
        link = LinkItem(
            id=uuid4(),
            title=title.strip(),
            slug=slug.strip(),
            url=url.strip(),
            icon=icon.strip() if icon else None,
            status=status,
            position=position,
            visibility=visibility,
            group_id=group_id,
        )

        # Save
        saved = self._repo.save(link)
        return saved, []

    def update(
        self,
        link_id: UUID,
        updates: dict[str, Any],
    ) -> tuple[LinkItem | None, list[LinkValidationError]]:
        """
        Update an existing link.

        Returns:
            Tuple of (link, errors). Link is None if not found or validation fails.
        """
        # Get existing link
        link = self.get_by_id(link_id)
        if not link:
            return None, [
                LinkValidationError(
                    code="link_not_found",
                    message=f"Link with ID {link_id} not found",
                )
            ]

        # Validate updates
        errors = validate_link_data(
            title=updates.get("title"),
            slug=updates.get("slug"),
            url=updates.get("url"),
        )
        if errors:
            return None, errors

        # Check for duplicate slug (if changing slug)
        new_slug = updates.get("slug")
        if new_slug and new_slug != link.slug:
            existing_links = self._repo.get_all()
            if any(
                link_item.slug == new_slug and link_item.id != link_id
                for link_item in existing_links
            ):
                return None, [
                    LinkValidationError(
                        code="slug_duplicate",
                        message=f"Link with slug '{new_slug}' already exists",
                        field="slug",
                    )
                ]

        # Apply updates
        if "title" in updates:
            link.title = str(updates["title"]).strip()
        if "slug" in updates:
            link.slug = str(updates["slug"]).strip()
        if "url" in updates:
            link.url = str(updates["url"]).strip()
        if "icon" in updates:
            link.icon = str(updates["icon"]).strip() if updates["icon"] else None
        if "status" in updates:
            link.status = updates["status"]
        if "position" in updates:
            link.position = updates["position"]
        if "visibility" in updates:
            link.visibility = updates["visibility"]
        if "group_id" in updates:
            link.group_id = updates["group_id"]

        # Save
        saved = self._repo.save(link)
        return saved, []

    def delete(self, link_id: UUID) -> tuple[bool, list[LinkValidationError]]:
        """
        Delete a link.

        Returns:
            Tuple of (success, errors).
        """
        # Check if link exists
        link = self.get_by_id(link_id)
        if not link:
            return False, [
                LinkValidationError(
                    code="link_not_found",
                    message=f"Link with ID {link_id} not found",
                )
            ]

        # Delete
        self._repo.delete(link_id)
        return True, []
