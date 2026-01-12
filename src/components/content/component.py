"""
Content component - Content lifecycle and state machine management.

Spec refs: E2, E3, E4, SM1
Test assertions: TA-0009 through TA-0013

Manages content lifecycle (posts, pages, resources) with state machine transitions.
Handles create, update, publish, archive operations with proper status transitions.

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

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.core.entities import ContentBlock, ContentItem, ContentStatus

from .models import (
    ContentListOutput,
    ContentOperationOutput,
    ContentOutput,
    ContentValidationError,
    CreateContentInput,
    DeleteContentInput,
    GetContentInput,
    ListContentInput,
    TransitionContentInput,
    UpdateContentInput,
)
from .ports import AssetResolverPort, ContentRepoPort, RulesPort, TimePort

# --- Default Configuration ---

DEFAULT_TRANSITIONS: dict[ContentStatus, list[ContentStatus]] = {
    "draft": ["scheduled", "published"],
    "scheduled": ["draft", "published"],
    "published": ["draft"],
}


# --- Validation Functions ---


def _is_valid_slug(slug: str) -> bool:
    """Check if slug is valid (lowercase alphanumeric + hyphens)."""
    return bool(re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug))


def _validate_content_fields(content: ContentItem) -> list[ContentValidationError]:
    """Validate content fields."""
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


def _validate_publish_at(
    publish_at: datetime | None,
    now: datetime,
    grace_seconds: int = 10,
) -> list[ContentValidationError]:
    """Validate publish_at for scheduling (G2)."""
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


def _extract_asset_references(content: ContentItem) -> list[UUID]:
    """Extract asset UUIDs referenced in content blocks."""
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


def _check_publish_guards(
    content: ContentItem,
    asset_resolver: AssetResolverPort | None,
    require_validated: bool = True,
    block_missing_assets: bool = True,
) -> list[ContentValidationError]:
    """Check publish guards (G1)."""
    errors: list[ContentValidationError] = []

    # G1a: Content validation
    if require_validated:
        validation_errors = _validate_content_fields(content)
        errors.extend(validation_errors)

    # G1b: Asset references resolvable
    if block_missing_assets and asset_resolver:
        asset_ids = _extract_asset_references(content)
        for asset_id in asset_ids:
            if not asset_resolver.resolve(asset_id):
                errors.append(
                    ContentValidationError(
                        code="missing_asset",
                        message=f"Referenced asset {asset_id} not found",
                        field="blocks",
                    )
                )

    return errors


# --- State Machine ---


@dataclass
class StateMachineConfig:
    """Configuration for content state machine."""

    transitions: dict[ContentStatus, list[ContentStatus]] = field(
        default_factory=lambda: DEFAULT_TRANSITIONS.copy()
    )
    require_validated_content: bool = True
    block_publish_if_missing_assets: bool = True


def _can_transition(
    from_status: ContentStatus,
    to_status: ContentStatus,
    config: StateMachineConfig,
) -> bool:
    """Check if a transition is allowed."""
    allowed = config.transitions.get(from_status, [])
    return to_status in allowed


def _get_allowed_transitions(
    status: ContentStatus,
    config: StateMachineConfig,
) -> list[ContentStatus]:
    """Get list of allowed target states from current status."""
    return list(config.transitions.get(status, []))


# --- Component Entry Points ---


def run_get(
    inp: GetContentInput,
    *,
    repo: ContentRepoPort,
) -> ContentOutput:
    """
    Get content by ID or slug.

    Args:
        inp: Input containing content_id or (slug + content_type).
        repo: Content repository port.

    Returns:
        ContentOutput with content item or error.
    """
    content: ContentItem | None = None

    if inp.content_id is not None:
        content = repo.get_by_id(inp.content_id)
    elif inp.slug is not None and inp.content_type is not None:
        content = repo.get_by_slug(inp.slug, inp.content_type)
    else:
        return ContentOutput(
            content=None,
            errors=[
                ContentValidationError(
                    code="invalid_input",
                    message="Either content_id or (slug + content_type) must be provided",
                )
            ],
            success=False,
        )

    if content is None:
        return ContentOutput(
            content=None,
            errors=[
                ContentValidationError(
                    code="not_found",
                    message="Content not found",
                )
            ],
            success=False,
        )

    return ContentOutput(content=content, errors=[], success=True)


def run_list(
    inp: ListContentInput,
    *,
    repo: ContentRepoPort,
) -> ContentListOutput:
    """
    List content with filters.

    Args:
        inp: Input containing filters.
        repo: Content repository port.

    Returns:
        ContentListOutput with items and pagination.
    """
    items, total = repo.list(
        content_type=inp.content_type,
        status=inp.status,
        limit=inp.limit,
        offset=inp.offset,
    )

    return ContentListOutput(
        items=items,
        total=total,
        limit=inp.limit,
        offset=inp.offset,
        errors=[],
        success=True,
    )


def run_create(
    inp: CreateContentInput,
    *,
    repo: ContentRepoPort,
    time: TimePort,
) -> ContentOperationOutput:
    """
    Create new content.

    Args:
        inp: Input containing content fields.
        repo: Content repository port.
        time: Time port for timestamps.

    Returns:
        ContentOperationOutput with created content or errors.
    """
    now = time.now_utc()

    # Build content blocks from input (position is implicit in list order)
    blocks = [
        ContentBlock(
            block_type=b.get("type", "markdown"),
            data_json=b.get("data", {}),
        )
        for b in inp.blocks
    ]

    # Create content item
    content = ContentItem(
        id=uuid4(),
        type=inp.type,
        title=inp.title,
        slug=inp.slug,
        summary=inp.summary,
        status="draft",
        owner_user_id=inp.owner_user_id,
        blocks=blocks,
        created_at=now,
        updated_at=now,
    )

    # Validate fields
    errors = _validate_content_fields(content)
    if errors:
        return ContentOperationOutput(content=None, errors=errors, success=False)

    # Check slug uniqueness
    existing = repo.get_by_slug(content.slug, content.type)
    if existing:
        return ContentOperationOutput(
            content=None,
            errors=[
                ContentValidationError(
                    code="slug_exists",
                    message=f"Slug '{content.slug}' already exists for type '{content.type}'",
                    field="slug",
                )
            ],
            success=False,
        )

    saved = repo.save(content)
    return ContentOperationOutput(content=saved, errors=[], success=True)


def run_update(
    inp: UpdateContentInput,
    *,
    repo: ContentRepoPort,
    time: TimePort,
) -> ContentOperationOutput:
    """
    Update existing content fields.

    Args:
        inp: Input containing content_id and updates.
        repo: Content repository port.
        time: Time port for timestamps.

    Returns:
        ContentOperationOutput with updated content or errors.
    """
    content = repo.get_by_id(inp.content_id)
    if content is None:
        return ContentOperationOutput(
            content=None,
            errors=[
                ContentValidationError(
                    code="not_found",
                    message=f"Content {inp.content_id} not found",
                )
            ],
            success=False,
        )

    # Apply updates (excluding status - use transition for that)
    updates = dict(inp.updates)
    updates.pop("status", None)
    updates.pop("id", None)

    for key, value in updates.items():
        if hasattr(content, key):
            setattr(content, key, value)

    content.updated_at = time.now_utc()

    # Validate
    errors = _validate_content_fields(content)
    if errors:
        return ContentOperationOutput(content=content, errors=errors, success=False)

    # Check slug uniqueness if changed
    if "slug" in inp.updates:
        existing = repo.get_by_slug(content.slug, content.type)
        if existing and existing.id != content.id:
            return ContentOperationOutput(
                content=content,
                errors=[
                    ContentValidationError(
                        code="slug_exists",
                        message=f"Slug '{content.slug}' already exists",
                        field="slug",
                    )
                ],
                success=False,
            )

    saved = repo.save(content)
    return ContentOperationOutput(content=saved, errors=[], success=True)


def run_transition(
    inp: TransitionContentInput,
    *,
    repo: ContentRepoPort,
    time: TimePort,
    rules: RulesPort | None = None,
    asset_resolver: AssetResolverPort | None = None,
) -> ContentOperationOutput:
    """
    Transition content to a new status.

    Args:
        inp: Input containing content_id, to_status, and optional publish_at.
        repo: Content repository port.
        time: Time port for timestamps.
        rules: Optional rules port for state machine config.
        asset_resolver: Optional asset resolver for publish guards.

    Returns:
        ContentOperationOutput with transitioned content or errors.
    """
    now = time.now_utc()

    content = repo.get_by_id(inp.content_id)
    if content is None:
        return ContentOperationOutput(
            content=None,
            errors=[
                ContentValidationError(
                    code="not_found",
                    message=f"Content {inp.content_id} not found",
                )
            ],
            success=False,
        )

    # Build state machine config from rules
    config = StateMachineConfig()
    if rules:
        config.transitions = rules.get_status_machine()
        guards = rules.get_publish_guards()
        config.require_validated_content = guards.get("require_validated_content", True)
        config.block_publish_if_missing_assets = guards.get("block_publish_if_missing_assets", True)

    # Check transition is allowed
    if not _can_transition(content.status, inp.to_status, config):
        allowed = _get_allowed_transitions(content.status, config)
        return ContentOperationOutput(
            content=content,
            errors=[
                ContentValidationError(
                    code="invalid_transition",
                    message=(
                        f"Cannot transition from '{content.status}' to '{inp.to_status}'. "
                        f"Allowed: {allowed}"
                    ),
                    field="status",
                )
            ],
            success=False,
        )

    # Scheduling requires publish_at (G2)
    if inp.to_status == "scheduled":
        errors = _validate_publish_at(inp.publish_at, now)
        if errors:
            return ContentOperationOutput(content=content, errors=errors, success=False)

    # Apply publish guards for publish transitions (G1)
    if inp.to_status == "published":
        guard_errors = _check_publish_guards(
            content,
            asset_resolver,
            config.require_validated_content,
            config.block_publish_if_missing_assets,
        )
        if guard_errors:
            return ContentOperationOutput(content=content, errors=guard_errors, success=False)

    # Execute transition
    old_status = content.status
    content.status = inp.to_status
    content.updated_at = now

    # Set publish-related timestamps
    if inp.to_status == "scheduled" and inp.publish_at:
        content.publish_at = inp.publish_at
    elif inp.to_status == "published":
        content.published_at = now
        content.publish_at = None  # Clear scheduled time
    elif inp.to_status == "draft":
        # Unpublish or unschedule
        if old_status == "scheduled":
            content.publish_at = None

    saved = repo.save(content)
    return ContentOperationOutput(content=saved, errors=[], success=True)


def run_delete(
    inp: DeleteContentInput,
    *,
    repo: ContentRepoPort,
) -> ContentOperationOutput:
    """
    Delete content.

    Args:
        inp: Input containing content_id.
        repo: Content repository port.

    Returns:
        ContentOperationOutput indicating success or failure.
    """
    content = repo.get_by_id(inp.content_id)
    if content is None:
        return ContentOperationOutput(
            content=None,
            errors=[
                ContentValidationError(
                    code="not_found",
                    message=f"Content {inp.content_id} not found",
                )
            ],
            success=False,
        )

    # I3: Published content cannot be deleted (must archive first)
    if content.status == "published":
        return ContentOperationOutput(
            content=content,
            errors=[
                ContentValidationError(
                    code="cannot_delete_published",
                    message="Published content cannot be deleted. Unpublish first.",
                    field="status",
                )
            ],
            success=False,
        )

    repo.delete(inp.content_id)
    return ContentOperationOutput(content=None, errors=[], success=True)


def run(
    inp: (
        GetContentInput
        | ListContentInput
        | CreateContentInput
        | UpdateContentInput
        | TransitionContentInput
        | DeleteContentInput
    ),
    *,
    repo: ContentRepoPort,
    time: TimePort | None = None,
    rules: RulesPort | None = None,
    asset_resolver: AssetResolverPort | None = None,
) -> ContentOutput | ContentListOutput | ContentOperationOutput:
    """
    Main entry point for the content component.

    Dispatches to appropriate handler based on input type.

    Args:
        inp: Input object determining the operation.
        repo: Content repository port.
        time: Time port for timestamps (required for create/update/transition).
        rules: Optional rules port for state machine config.
        asset_resolver: Optional asset resolver for publish guards.

    Returns:
        Appropriate output object based on input type.
    """
    if isinstance(inp, GetContentInput):
        return run_get(inp, repo=repo)

    elif isinstance(inp, ListContentInput):
        return run_list(inp, repo=repo)

    elif isinstance(inp, CreateContentInput):
        if time is None:
            raise ValueError("TimePort is required for create operations")
        return run_create(inp, repo=repo, time=time)

    elif isinstance(inp, UpdateContentInput):
        if time is None:
            raise ValueError("TimePort is required for update operations")
        return run_update(inp, repo=repo, time=time)

    elif isinstance(inp, TransitionContentInput):
        if time is None:
            raise ValueError("TimePort is required for transition operations")
        return run_transition(inp, repo=repo, time=time, rules=rules, asset_resolver=asset_resolver)

    elif isinstance(inp, DeleteContentInput):
        return run_delete(inp, repo=repo)

    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
