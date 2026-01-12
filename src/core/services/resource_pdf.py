"""
Resource(PDF) Service (E3.1) - PDF resource content management.

Handles PDF resource creation, asset linkage, and pinned policy.

Spec refs: E3.1, TA-0014, TA-0015
Test assertions:
- TA-0014: Resource draft persistence (create, update, save)
- TA-0015: Pinned policy validation (pinned_version vs latest)

Key behaviors:
- Resource links to a PDF asset with version pinning policy
- Pinned policy: "pinned" (specific version) or "latest" (follow /latest)
- Validates PDF asset exists and is correct MIME type
- Inherits status transitions from ContentService
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from src.core.entities import ContentItem
from src.domain.entities import ContentStatus

# --- Types ---

PinnedPolicy = Literal["pinned", "latest"]


# --- Validation Errors ---


@dataclass
class ResourceValidationError:
    """Resource validation error."""

    code: str
    message: str
    field: str | None = None


# --- Resource PDF Model ---


@dataclass
class ResourcePDF:
    """
    PDF Resource content.

    Extends ContentItem with PDF-specific fields.
    """

    id: UUID
    title: str
    slug: str
    summary: str
    status: ContentStatus  # draft, scheduled, published
    owner_user_id: UUID

    # PDF-specific fields
    pdf_asset_id: UUID | None  # Link to PDF asset
    pdf_version_id: UUID | None  # Specific version (when pinned)
    pinned_policy: PinnedPolicy  # "pinned" or "latest"
    display_title: str | None  # Override title for display
    download_filename: str | None  # Custom download filename

    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None

    def to_content_item(self) -> ContentItem:
        """Convert to ContentItem for content service operations."""
        return ContentItem(
            id=self.id,
            type="resource_pdf",
            slug=self.slug,
            title=self.title,
            summary=self.summary,
            status=self.status,
            owner_user_id=self.owner_user_id,
            blocks=[],  # PDF resources don't use blocks
            created_at=self.created_at,
            updated_at=self.updated_at,
            published_at=self.published_at,
        )


# --- Repository Protocol ---


class ResourcePDFRepoPort(Protocol):
    """Repository interface for PDF resources."""

    def get_by_id(self, resource_id: UUID) -> ResourcePDF | None:
        """Get resource by ID."""
        ...

    def get_by_slug(self, slug: str) -> ResourcePDF | None:
        """Get resource by slug."""
        ...

    def save(self, resource: ResourcePDF) -> ResourcePDF:
        """Save or update resource."""
        ...

    def delete(self, resource_id: UUID) -> None:
        """Delete resource."""
        ...

    def list_all(self) -> list[ResourcePDF]:
        """List all resources."""
        ...


class AssetResolverPort(Protocol):
    """Asset resolver for checking PDF assets."""

    def get_asset(self, asset_id: UUID) -> Any | None:
        """Get asset by ID."""
        ...

    def get_version(self, version_id: UUID) -> Any | None:
        """Get version by ID."""
        ...

    def is_pdf(self, asset_id: UUID) -> bool:
        """Check if asset is a PDF."""
        ...


# --- Validation Functions ---


def validate_resource_fields(resource: ResourcePDF) -> list[ResourceValidationError]:
    """
    Validate resource fields (TA-0014).

    Returns list of validation errors.
    """
    errors: list[ResourceValidationError] = []

    # Title required
    if not resource.title or not resource.title.strip():
        errors.append(
            ResourceValidationError(
                code="title_required",
                message="Title is required",
                field="title",
            )
        )

    # Slug required and valid
    if not resource.slug or not resource.slug.strip():
        errors.append(
            ResourceValidationError(
                code="slug_required",
                message="Slug is required",
                field="slug",
            )
        )
    elif not _is_valid_slug(resource.slug):
        errors.append(
            ResourceValidationError(
                code="slug_invalid",
                message="Slug must contain only lowercase letters, numbers, and hyphens",
                field="slug",
            )
        )

    return errors


def validate_pinned_policy(
    resource: ResourcePDF,
    asset_resolver: AssetResolverPort | None = None,
) -> list[ResourceValidationError]:
    """
    Validate pinned policy (TA-0015).

    Rules:
    - If pinned_policy is "pinned", pdf_version_id must be set
    - If pinned_policy is "latest", pdf_version_id should be None
    - pdf_asset_id must reference a valid PDF asset

    Returns list of validation errors.
    """
    errors: list[ResourceValidationError] = []

    # Check pinned policy consistency
    if resource.pinned_policy == "pinned":
        if resource.pdf_version_id is None:
            errors.append(
                ResourceValidationError(
                    code="version_required_for_pinned",
                    message="pdf_version_id is required when pinned_policy is 'pinned'",
                    field="pdf_version_id",
                )
            )
    elif resource.pinned_policy == "latest":
        if resource.pdf_version_id is not None:
            errors.append(
                ResourceValidationError(
                    code="version_not_allowed_for_latest",
                    message="pdf_version_id should not be set when pinned_policy is 'latest'",
                    field="pdf_version_id",
                )
            )

    # Check asset exists and is PDF (if resolver provided)
    if asset_resolver and resource.pdf_asset_id:
        asset = asset_resolver.get_asset(resource.pdf_asset_id)
        if asset is None:
            errors.append(
                ResourceValidationError(
                    code="asset_not_found",
                    message=f"PDF asset {resource.pdf_asset_id} not found",
                    field="pdf_asset_id",
                )
            )
        elif not asset_resolver.is_pdf(resource.pdf_asset_id):
            errors.append(
                ResourceValidationError(
                    code="asset_not_pdf",
                    message="Asset must be a PDF (application/pdf)",
                    field="pdf_asset_id",
                )
            )

    # Check version exists and belongs to asset (if resolver provided)
    if asset_resolver and resource.pdf_version_id:
        version = asset_resolver.get_version(resource.pdf_version_id)
        if version is None:
            errors.append(
                ResourceValidationError(
                    code="version_not_found",
                    message=f"Version {resource.pdf_version_id} not found",
                    field="pdf_version_id",
                )
            )
        elif resource.pdf_asset_id and version.asset_id != resource.pdf_asset_id:
            errors.append(
                ResourceValidationError(
                    code="version_asset_mismatch",
                    message="Version does not belong to the specified asset",
                    field="pdf_version_id",
                )
            )

    return errors


def _is_valid_slug(slug: str) -> bool:
    """Check if slug is valid."""
    import re

    return bool(re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug))


# --- Resource PDF Service ---


class ResourcePDFService:
    """
    PDF Resource service (E3.1).

    Provides CRUD operations for PDF resources with validation.
    """

    def __init__(
        self,
        repo: ResourcePDFRepoPort,
        asset_resolver: AssetResolverPort | None = None,
    ) -> None:
        """
        Initialize service.

        Args:
            repo: Resource repository
            asset_resolver: Optional asset resolver for validation
        """
        self._repo = repo
        self._asset_resolver = asset_resolver

    def get(self, resource_id: UUID) -> ResourcePDF | None:
        """Get resource by ID."""
        return self._repo.get_by_id(resource_id)

    def get_by_slug(self, slug: str) -> ResourcePDF | None:
        """Get resource by slug."""
        return self._repo.get_by_slug(slug)

    def create(
        self,
        title: str,
        slug: str,
        owner_user_id: UUID,
        summary: str = "",
        pdf_asset_id: UUID | None = None,
        pdf_version_id: UUID | None = None,
        pinned_policy: PinnedPolicy = "latest",
        display_title: str | None = None,
        download_filename: str | None = None,
    ) -> tuple[ResourcePDF | None, list[ResourceValidationError]]:
        """
        Create a new PDF resource draft (TA-0014).

        Returns:
            Tuple of (resource, errors). Resource is None if validation fails.
        """
        now = datetime.now(UTC)

        resource = ResourcePDF(
            id=uuid4(),
            title=title,
            slug=slug,
            summary=summary,
            status="draft",
            owner_user_id=owner_user_id,
            pdf_asset_id=pdf_asset_id,
            pdf_version_id=pdf_version_id,
            pinned_policy=pinned_policy,
            display_title=display_title,
            download_filename=download_filename,
            created_at=now,
            updated_at=now,
        )

        # Validate fields
        errors = validate_resource_fields(resource)
        if errors:
            return None, errors

        # Validate pinned policy
        errors.extend(validate_pinned_policy(resource, self._asset_resolver))
        if errors:
            return None, errors

        # Check slug uniqueness
        existing = self._repo.get_by_slug(slug)
        if existing:
            return None, [
                ResourceValidationError(
                    code="slug_exists",
                    message=f"Slug '{slug}' already exists",
                    field="slug",
                )
            ]

        saved = self._repo.save(resource)
        return saved, []

    def update(
        self,
        resource_id: UUID,
        updates: dict[str, Any],
    ) -> tuple[ResourcePDF | None, list[ResourceValidationError]]:
        """
        Update resource fields.

        Returns:
            Tuple of (updated_resource, errors).
        """
        resource = self._repo.get_by_id(resource_id)
        if resource is None:
            return None, [
                ResourceValidationError(
                    code="not_found",
                    message=f"Resource {resource_id} not found",
                )
            ]

        # Apply updates
        for key, value in updates.items():
            if hasattr(resource, key) and key not in ("id", "status", "created_at"):
                setattr(resource, key, value)

        resource.updated_at = datetime.now(UTC)

        # Validate
        errors = validate_resource_fields(resource)
        if errors:
            return resource, errors

        errors.extend(validate_pinned_policy(resource, self._asset_resolver))
        if errors:
            return resource, errors

        # Check slug uniqueness if changed
        if "slug" in updates:
            existing = self._repo.get_by_slug(resource.slug)
            if existing and existing.id != resource.id:
                return resource, [
                    ResourceValidationError(
                        code="slug_exists",
                        message=f"Slug '{resource.slug}' already exists",
                        field="slug",
                    )
                ]

        saved = self._repo.save(resource)
        return saved, []

    def set_pinned_policy(
        self,
        resource_id: UUID,
        policy: PinnedPolicy,
        version_id: UUID | None = None,
    ) -> tuple[ResourcePDF | None, list[ResourceValidationError]]:
        """
        Set pinned policy for resource (TA-0015).

        Args:
            resource_id: Resource to update
            policy: "pinned" or "latest"
            version_id: Required when policy is "pinned"

        Returns:
            Tuple of (updated_resource, errors).
        """
        resource = self._repo.get_by_id(resource_id)
        if resource is None:
            return None, [
                ResourceValidationError(
                    code="not_found",
                    message=f"Resource {resource_id} not found",
                )
            ]

        # Update policy
        resource.pinned_policy = policy
        resource.pdf_version_id = version_id if policy == "pinned" else None
        resource.updated_at = datetime.now(UTC)

        # Validate
        errors = validate_pinned_policy(resource, self._asset_resolver)
        if errors:
            return resource, errors

        saved = self._repo.save(resource)
        return saved, []

    def link_asset(
        self,
        resource_id: UUID,
        asset_id: UUID,
        version_id: UUID | None = None,
        policy: PinnedPolicy = "latest",
    ) -> tuple[ResourcePDF | None, list[ResourceValidationError]]:
        """
        Link PDF asset to resource.

        Args:
            resource_id: Resource to update
            asset_id: PDF asset to link
            version_id: Specific version (for pinned policy)
            policy: Pinned policy

        Returns:
            Tuple of (updated_resource, errors).
        """
        resource = self._repo.get_by_id(resource_id)
        if resource is None:
            return None, [
                ResourceValidationError(
                    code="not_found",
                    message=f"Resource {resource_id} not found",
                )
            ]

        resource.pdf_asset_id = asset_id
        resource.pdf_version_id = version_id if policy == "pinned" else None
        resource.pinned_policy = policy
        resource.updated_at = datetime.now(UTC)

        # Validate
        errors = validate_pinned_policy(resource, self._asset_resolver)
        if errors:
            return resource, errors

        saved = self._repo.save(resource)
        return saved, []

    def delete(self, resource_id: UUID) -> bool:
        """
        Delete resource.

        Returns True if deleted, False if not found.
        """
        resource = self._repo.get_by_id(resource_id)
        if resource is None:
            return False

        self._repo.delete(resource_id)
        return True

    def list_all(self) -> list[ResourcePDF]:
        """List all resources."""
        return self._repo.list_all()


# --- Factory ---


def create_resource_pdf_service(
    repo: ResourcePDFRepoPort,
    asset_resolver: AssetResolverPort | None = None,
) -> ResourcePDFService:
    """Create a ResourcePDFService."""
    return ResourcePDFService(repo=repo, asset_resolver=asset_resolver)
