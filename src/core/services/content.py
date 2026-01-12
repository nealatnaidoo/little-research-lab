"""
ContentService (C1) - Content validation and state machine.

Implements content validation, state transitions, and revisioning hooks.
State machine driven by rules.content.status_machine.

Spec refs: C1, SM1, E2, E4, R1
Test assertions: TA-0110 (state machine)

State Machine (SM1):
- draft → scheduled (set publish_at_utc)
- scheduled → draft (unschedule)
- draft|scheduled → published (publish now OR job-run)
- published → draft (unpublish)

Guards:
- G1: publish requires content validation + resolvable assets
- G2: scheduled publish requires publish_at_utc in future
- G3: scheduled content must never publish before target time
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from src.core.entities import ContentItem, ContentStatus

# --- State Machine Configuration ---


@dataclass
class StateTransition:
    """A valid state transition."""

    from_status: ContentStatus
    to_status: ContentStatus
    requires_publish_at: bool = False
    requires_validation: bool = False


DEFAULT_TRANSITIONS: dict[ContentStatus, list[ContentStatus]] = {
    "draft": ["scheduled", "published"],
    "scheduled": ["draft", "published"],
    "published": ["draft"],
}


# --- Validation Errors ---


@dataclass
class ContentValidationError:
    """Content validation error."""

    code: str
    message: str
    field: str | None = None


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""

    def __init__(
        self,
        from_status: ContentStatus,
        to_status: ContentStatus,
        reason: str = "",
    ) -> None:
        self.from_status = from_status
        self.to_status = to_status
        self.reason = reason
        msg = f"Cannot transition from '{from_status}' to '{to_status}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class PublishGuardError(Exception):
    """Raised when publish guards fail."""

    def __init__(self, errors: list[ContentValidationError]) -> None:
        self.errors = errors
        messages = [e.message for e in errors]
        super().__init__(f"Publish guards failed: {'; '.join(messages)}")


# --- Repository Protocol ---


class ContentRepoPort(Protocol):
    """Content repository interface."""

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


class AssetResolverPort(Protocol):
    """Asset resolver for checking asset references."""

    def resolve(self, asset_id: UUID) -> bool:
        """Check if an asset exists and is resolvable."""
        ...


# --- Validation Functions ---


def validate_content_fields(content: ContentItem) -> list[ContentValidationError]:
    """
    Validate content fields.

    Returns list of validation errors (empty if valid).
    """
    errors: list[ContentValidationError] = []

    # Title required
    if not content.title or not content.title.strip():
        errors.append(
            ContentValidationError(
                code="title_required",
                message="Title is required",
                field="title",
            )
        )

    # Slug required and valid format
    if not content.slug or not content.slug.strip():
        errors.append(
            ContentValidationError(
                code="slug_required",
                message="Slug is required",
                field="slug",
            )
        )
    elif not _is_valid_slug(content.slug):
        errors.append(
            ContentValidationError(
                code="slug_invalid",
                message="Slug must contain only lowercase letters, numbers, and hyphens",
                field="slug",
            )
        )

    return errors


def _is_valid_slug(slug: str) -> bool:
    """Check if slug is valid (lowercase alphanumeric + hyphens)."""
    import re

    return bool(re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug))


def validate_publish_at(
    publish_at: datetime | None,
    now: datetime,
    grace_seconds: int = 10,
) -> list[ContentValidationError]:
    """
    Validate publish_at for scheduling (G2).

    Args:
        publish_at: Target publish time
        now: Current time
        grace_seconds: Buffer for "now" scheduling

    Returns:
        List of validation errors
    """
    errors: list[ContentValidationError] = []

    if publish_at is None:
        errors.append(
            ContentValidationError(
                code="publish_at_required",
                message="publish_at is required for scheduling",
                field="publish_at",
            )
        )
    else:
        # Normalize to UTC for comparison
        if publish_at.tzinfo is None:
            publish_at = publish_at.replace(tzinfo=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        threshold = now + timedelta(seconds=grace_seconds)
        if publish_at < threshold:
            errors.append(
                ContentValidationError(
                    code="publish_at_past",
                    message=f"publish_at must be at least {grace_seconds} seconds in the future",
                    field="publish_at",
                )
            )

    return errors


def extract_asset_references(content: ContentItem) -> list[UUID]:
    """
    Extract asset UUIDs referenced in content blocks.

    Scans blocks for image/asset references.
    """
    asset_ids: list[UUID] = []

    for block in content.blocks:
        if block.block_type == "image":
            asset_id = block.data_json.get("asset_id")
            if asset_id:
                try:
                    asset_ids.append(UUID(asset_id))
                except (ValueError, TypeError):
                    pass

    return asset_ids


# --- State Machine ---


class ContentStateMachine:
    """
    Content state machine (SM1).

    Validates and executes state transitions based on rules.
    """

    def __init__(
        self,
        transitions: dict[ContentStatus, list[ContentStatus]] | None = None,
    ) -> None:
        """
        Initialize state machine.

        Args:
            transitions: Allowed transitions map (from rules.content.status_machine)
        """
        self._transitions = transitions or DEFAULT_TRANSITIONS

    def can_transition(
        self,
        from_status: ContentStatus,
        to_status: ContentStatus,
    ) -> bool:
        """Check if a transition is allowed."""
        allowed = self._transitions.get(from_status, [])
        return to_status in allowed

    def get_allowed_transitions(self, status: ContentStatus) -> list[ContentStatus]:
        """Get list of allowed target states from current status."""
        return list(self._transitions.get(status, []))

    def validate_transition(
        self,
        content: ContentItem,
        to_status: ContentStatus,
        publish_at: datetime | None = None,
        now: datetime | None = None,
    ) -> list[ContentValidationError]:
        """
        Validate a state transition.

        Args:
            content: Content item to transition
            to_status: Target status
            publish_at: Required for scheduling
            now: Current time (for validation)

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[ContentValidationError] = []
        now = now or datetime.now(UTC)

        # Check transition is allowed
        if not self.can_transition(content.status, to_status):
            errors.append(
                ContentValidationError(
                    code="invalid_transition",
                    message=(
                        f"Cannot transition from '{content.status}' to '{to_status}'. "
                        f"Allowed: {self.get_allowed_transitions(content.status)}"
                    ),
                    field="status",
                )
            )
            return errors  # Early return - no point checking other guards

        # Scheduling requires publish_at (G2)
        if to_status == "scheduled":
            errors.extend(validate_publish_at(publish_at, now))

        return errors


# --- Content Service ---


class ContentService:
    """
    Content service (C1).

    Provides content CRUD, validation, and state transitions.
    """

    def __init__(
        self,
        repo: ContentRepoPort,
        state_machine: ContentStateMachine | None = None,
        asset_resolver: AssetResolverPort | None = None,
        require_validated_content: bool = True,
        block_publish_if_missing_assets: bool = True,
    ) -> None:
        """
        Initialize content service.

        Args:
            repo: Content repository
            state_machine: State machine (defaults to SM1)
            asset_resolver: Optional asset resolver for G1 validation
            require_validated_content: G1 guard flag
            block_publish_if_missing_assets: G1 guard flag
        """
        self._repo = repo
        self._state_machine = state_machine or ContentStateMachine()
        self._asset_resolver = asset_resolver
        self._require_validated = require_validated_content
        self._block_missing_assets = block_publish_if_missing_assets

    def get(self, content_id: UUID) -> ContentItem | None:
        """Get content by ID."""
        return self._repo.get_by_id(content_id)

    def get_by_slug(self, slug: str, content_type: str) -> ContentItem | None:
        """Get content by slug and type."""
        return self._repo.get_by_slug(slug, content_type)

    def create(
        self,
        content: ContentItem,
    ) -> tuple[ContentItem, list[ContentValidationError]]:
        """
        Create new content.

        Args:
            content: Content to create

        Returns:
            Tuple of (saved_content, errors)
        """
        # Validate fields
        errors = validate_content_fields(content)
        if errors:
            return content, errors

        # Check slug uniqueness
        existing = self._repo.get_by_slug(content.slug, content.type)
        if existing:
            errors.append(
                ContentValidationError(
                    code="slug_exists",
                    message=f"Slug '{content.slug}' already exists for type '{content.type}'",
                    field="slug",
                )
            )
            return content, errors

        # New content starts as draft
        content.status = "draft"
        content.created_at = datetime.now(UTC)
        content.updated_at = content.created_at

        saved = self._repo.save(content)
        return saved, []

    def update(
        self,
        content_id: UUID,
        updates: dict[str, Any],
    ) -> tuple[ContentItem | None, list[ContentValidationError]]:
        """
        Update content fields (not status).

        Args:
            content_id: Content ID
            updates: Fields to update

        Returns:
            Tuple of (updated_content, errors)
        """
        content = self._repo.get_by_id(content_id)
        if content is None:
            return None, [
                ContentValidationError(
                    code="not_found",
                    message=f"Content {content_id} not found",
                )
            ]

        # Apply updates (excluding status - use transition methods)
        updates.pop("status", None)
        updates.pop("id", None)

        for key, value in updates.items():
            if hasattr(content, key):
                setattr(content, key, value)

        content.updated_at = datetime.now(UTC)

        # Validate
        errors = validate_content_fields(content)
        if errors:
            return content, errors

        # Check slug uniqueness if changed
        if "slug" in updates:
            existing = self._repo.get_by_slug(content.slug, content.type)
            if existing and existing.id != content.id:
                errors.append(
                    ContentValidationError(
                        code="slug_exists",
                        message=f"Slug '{content.slug}' already exists",
                        field="slug",
                    )
                )
                return content, errors

        saved = self._repo.save(content)
        return saved, []

    def delete(self, content_id: UUID) -> bool:
        """
        Delete content.

        Returns True if deleted, False if not found.
        """
        content = self._repo.get_by_id(content_id)
        if content is None:
            return False

        self._repo.delete(content_id)
        return True

    def transition(
        self,
        content_id: UUID,
        to_status: ContentStatus,
        publish_at: datetime | None = None,
        now: datetime | None = None,
    ) -> tuple[ContentItem | None, list[ContentValidationError]]:
        """
        Transition content to a new status.

        Args:
            content_id: Content ID
            to_status: Target status
            publish_at: Required for 'scheduled' transition
            now: Current time (for validation)

        Returns:
            Tuple of (transitioned_content, errors)
        """
        now = now or datetime.now(UTC)

        content = self._repo.get_by_id(content_id)
        if content is None:
            return None, [
                ContentValidationError(
                    code="not_found",
                    message=f"Content {content_id} not found",
                )
            ]

        # Validate transition
        errors = self._state_machine.validate_transition(content, to_status, publish_at, now)
        if errors:
            return content, errors

        # Apply publish guards for publish transitions (G1)
        if to_status == "published":
            guard_errors = self._check_publish_guards(content)
            if guard_errors:
                return content, guard_errors

        # Execute transition
        old_status = content.status
        content.status = to_status
        content.updated_at = now

        # Set publish-related timestamps
        if to_status == "scheduled" and publish_at:
            content.publish_at = publish_at
        elif to_status == "published":
            content.published_at = now
            content.publish_at = None  # Clear scheduled time
        elif to_status == "draft":
            # Unpublish or unschedule
            if old_status == "scheduled":
                content.publish_at = None

        saved = self._repo.save(content)
        return saved, []

    def schedule(
        self,
        content_id: UUID,
        publish_at: datetime,
        now: datetime | None = None,
    ) -> tuple[ContentItem | None, list[ContentValidationError]]:
        """
        Schedule content for future publication.

        Convenience method for draft → scheduled transition.
        """
        return self.transition(content_id, "scheduled", publish_at, now)

    def publish(
        self,
        content_id: UUID,
        now: datetime | None = None,
    ) -> tuple[ContentItem | None, list[ContentValidationError]]:
        """
        Publish content immediately.

        Convenience method for → published transition.
        """
        return self.transition(content_id, "published", now=now)

    def unpublish(
        self,
        content_id: UUID,
    ) -> tuple[ContentItem | None, list[ContentValidationError]]:
        """
        Unpublish content (published → draft).

        Convenience method.
        """
        return self.transition(content_id, "draft")

    def unschedule(
        self,
        content_id: UUID,
    ) -> tuple[ContentItem | None, list[ContentValidationError]]:
        """
        Unschedule content (scheduled → draft).

        Convenience method.
        """
        return self.transition(content_id, "draft")

    def _check_publish_guards(
        self,
        content: ContentItem,
    ) -> list[ContentValidationError]:
        """
        Check publish guards (G1).

        Args:
            content: Content to publish

        Returns:
            List of guard violations
        """
        errors: list[ContentValidationError] = []

        # G1a: Content validation
        if self._require_validated:
            validation_errors = validate_content_fields(content)
            errors.extend(validation_errors)

        # G1b: Asset references resolvable
        if self._block_missing_assets and self._asset_resolver:
            asset_ids = extract_asset_references(content)
            for asset_id in asset_ids:
                if not self._asset_resolver.resolve(asset_id):
                    errors.append(
                        ContentValidationError(
                            code="missing_asset",
                            message=f"Referenced asset {asset_id} not found",
                            field="blocks",
                        )
                    )

        return errors

    def can_transition(
        self,
        content_id: UUID,
        to_status: ContentStatus,
    ) -> bool:
        """Check if a transition is possible."""
        content = self._repo.get_by_id(content_id)
        if content is None:
            return False
        return self._state_machine.can_transition(content.status, to_status)

    def get_allowed_transitions(self, content_id: UUID) -> list[ContentStatus]:
        """Get allowed transitions for content."""
        content = self._repo.get_by_id(content_id)
        if content is None:
            return []
        return self._state_machine.get_allowed_transitions(content.status)


# --- Factory ---


def create_content_service(
    repo: ContentRepoPort,
    rules_config: dict[str, Any] | None = None,
    asset_resolver: AssetResolverPort | None = None,
) -> ContentService:
    """
    Create a content service.

    Args:
        repo: Content repository
        rules_config: Optional rules.content configuration
        asset_resolver: Optional asset resolver

    Returns:
        Configured ContentService
    """
    # Parse state machine from rules
    transitions = DEFAULT_TRANSITIONS.copy()
    require_validated = True
    block_missing_assets = True

    if rules_config:
        # Parse status_machine
        if "status_machine" in rules_config:
            transitions = {}
            for status, config in rules_config["status_machine"].items():
                transitions[status] = config.get("can_transition_to", [])

        # Parse publish_guards
        if "publish_guards" in rules_config:
            guards = rules_config["publish_guards"]
            require_validated = guards.get("require_validated_content", True)
            block_missing_assets = guards.get("block_publish_if_missing_assets", True)

    state_machine = ContentStateMachine(transitions)

    return ContentService(
        repo=repo,
        state_machine=state_machine,
        asset_resolver=asset_resolver,
        require_validated_content=require_validated,
        block_publish_if_missing_assets=block_missing_assets,
    )
