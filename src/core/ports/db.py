"""
v3 Database Adapter Interfaces (P1).

Protocol-based interfaces for repository operations.
Implementations: SQLite (now), Postgres (future).

Spec refs: P1, E1-E8
Test assertions: TA-0103 (repo contract tests)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.core.entities import (
    AnalyticsEventAggregate,
    Asset,
    AssetVersion,
    AuditEvent,
    ContentItem,
    PublishJob,
    RedirectRule,
    SiteSettings,
    User,
)

# -----------------------------------------------------------------------------
# E1: SiteSettings Repository
# -----------------------------------------------------------------------------


class SiteSettingsRepoPort(Protocol):
    """
    Repository for site-wide settings (singleton row).

    Invariants:
    - I1: Exactly one active row; reads always succeed (fallback defaults allowed)
    """

    def get(self) -> SiteSettings | None:
        """Get current settings, or None if not configured."""
        ...

    def save(self, settings: SiteSettings) -> SiteSettings:
        """Save or update settings (upsert)."""
        ...


# -----------------------------------------------------------------------------
# E2: ContentItem Repository
# -----------------------------------------------------------------------------


class ContentRepoPort(Protocol):
    """
    Repository for content items (posts, resources).

    State machine (SM1): draft -> scheduled -> published
    """

    def get_by_id(self, item_id: UUID) -> ContentItem | None:
        """Get content by ID."""
        ...

    def get_by_slug(self, slug: str, item_type: str) -> ContentItem | None:
        """Get content by slug and type."""
        ...

    def save(self, content: ContentItem) -> ContentItem:
        """Save or update content (upsert)."""
        ...

    def delete(self, item_id: UUID) -> None:
        """Delete content by ID."""
        ...

    def list_items(self, filters: dict[str, Any]) -> list[ContentItem]:
        """List content with optional filters."""
        ...

    def list_published(self) -> list[ContentItem]:
        """List all published content (for public routes)."""
        ...

    def list_scheduled_before(self, before_utc: datetime) -> list[ContentItem]:
        """List scheduled content with publish_at before given time."""
        ...


# -----------------------------------------------------------------------------
# E3: Asset Repository (Logical Asset)
# -----------------------------------------------------------------------------


class AssetRepoPort(Protocol):
    """Repository for logical assets (parent of versions)."""

    def get_by_id(self, asset_id: UUID) -> Asset | None:
        """Get asset by ID."""
        ...

    def save(self, asset: Asset) -> Asset:
        """Save or update asset (upsert)."""
        ...

    def delete(self, asset_id: UUID) -> None:
        """Delete asset by ID."""
        ...

    def list_assets(self) -> list[Asset]:
        """List all assets."""
        ...


# -----------------------------------------------------------------------------
# E4: AssetVersion Repository
# -----------------------------------------------------------------------------


class AssetVersionRepoPort(Protocol):
    """
    Repository for immutable asset versions.

    Invariants:
    - I3: bytes are immutable; sha256 stored equals sha256 served
    - I4: /latest alias resolves to exactly one version per asset
    """

    def get_by_id(self, version_id: UUID) -> AssetVersion | None:
        """Get version by ID."""
        ...

    def get_by_storage_key(self, storage_key: str) -> AssetVersion | None:
        """Get version by storage key."""
        ...

    def save(self, version: AssetVersion) -> AssetVersion:
        """Save new version (insert only - versions are immutable)."""
        ...

    def list_by_asset(self, asset_id: UUID) -> list[AssetVersion]:
        """List all versions for an asset, ordered by version_number."""
        ...

    def get_latest(self, asset_id: UUID) -> AssetVersion | None:
        """Get the latest version for an asset."""
        ...

    def set_latest(self, asset_id: UUID, version_id: UUID) -> None:
        """Set a version as the latest (atomically clears previous latest)."""
        ...


# -----------------------------------------------------------------------------
# E5: PublishJob Repository
# -----------------------------------------------------------------------------


class PublishJobRepoPort(Protocol):
    """
    Repository for publish jobs (scheduler).

    Invariants:
    - I5: at-most-once per idempotency key (content_id, publish_at_utc)
    - Unique constraint required on (content_id, publish_at_utc)
    """

    def get_by_id(self, job_id: UUID) -> PublishJob | None:
        """Get job by ID."""
        ...

    def get_by_idempotency_key(
        self, content_id: UUID, publish_at_utc: datetime
    ) -> PublishJob | None:
        """Get job by idempotency key."""
        ...

    def save(self, job: PublishJob) -> PublishJob:
        """Save or update job (upsert)."""
        ...

    def create_if_not_exists(self, job: PublishJob) -> tuple[PublishJob, bool]:
        """
        Create job only if idempotency key doesn't exist.
        Returns (job, created) tuple.
        """
        ...

    def claim_next_runnable(self, worker_id: str, now_utc: datetime) -> PublishJob | None:
        """
        Atomically claim the next runnable job.
        Runnable = queued or retry_wait with next_retry_at <= now.
        Sets status to 'running' and claimed_by to worker_id.
        """
        ...

    def list_pending(self) -> list[PublishJob]:
        """List all pending jobs (queued, running, retry_wait)."""
        ...

    def list_by_content(self, content_id: UUID) -> list[PublishJob]:
        """List all jobs for a content item."""
        ...


# -----------------------------------------------------------------------------
# E6: AnalyticsEventAggregate Repository
# -----------------------------------------------------------------------------


class AnalyticsAggregateRepoPort(Protocol):
    """
    Repository for analytics aggregates.

    Invariants:
    - I6: no PII fields stored
    """

    def get_or_create_bucket(
        self,
        bucket_type: str,
        bucket_start: datetime,
        event_type: str,
        dimensions: dict[str, Any],
    ) -> AnalyticsEventAggregate:
        """Get or create an aggregate bucket."""
        ...

    def increment(
        self,
        bucket_id: UUID,
        count_total: int = 1,
        count_real: int = 0,
        count_bot: int = 0,
    ) -> None:
        """Increment counts for a bucket."""
        ...

    def query(
        self,
        bucket_type: str,
        start: datetime,
        end: datetime,
        event_type: str | None = None,
        content_id: UUID | None = None,
        dimensions: dict[str, Any] | None = None,
    ) -> list[AnalyticsEventAggregate]:
        """Query aggregates within a time range."""
        ...


# -----------------------------------------------------------------------------
# E7: RedirectRule Repository
# -----------------------------------------------------------------------------


class RedirectRepoPort(Protocol):
    """
    Repository for redirect rules.

    Invariants:
    - I7: no loops, no open redirects
    """

    def get_by_id(self, redirect_id: UUID) -> RedirectRule | None:
        """Get redirect by ID."""
        ...

    def get_by_source_path(self, source_path: str) -> RedirectRule | None:
        """Get active redirect by source path."""
        ...

    def save(self, rule: RedirectRule) -> RedirectRule:
        """Save or update redirect (upsert)."""
        ...

    def delete(self, redirect_id: UUID) -> None:
        """Delete redirect by ID."""
        ...

    def list_all(self) -> list[RedirectRule]:
        """List all redirects."""
        ...

    def list_active(self) -> list[RedirectRule]:
        """List active redirects."""
        ...


# -----------------------------------------------------------------------------
# E8: AuditLogEvent Repository
# -----------------------------------------------------------------------------


class AuditLogRepoPort(Protocol):
    """
    Repository for audit log events.

    Invariants:
    - Append-only (no updates or deletes)
    """

    def append(self, event: AuditEvent) -> AuditEvent:
        """Append a new audit event (insert only)."""
        ...

    def list_recent(self, limit: int = 100) -> list[AuditEvent]:
        """List recent audit events."""
        ...

    def list_by_target(
        self, target_type: str, target_id: str, limit: int = 100
    ) -> list[AuditEvent]:
        """List audit events for a specific target."""
        ...

    def list_by_actor(self, actor_user_id: UUID, limit: int = 100) -> list[AuditEvent]:
        """List audit events by actor."""
        ...


# -----------------------------------------------------------------------------
# User Repository (existing, re-exported for convenience)
# -----------------------------------------------------------------------------


class UserRepoPort(Protocol):
    """Repository for users."""

    def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        ...

    def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        ...

    def save(self, user: User) -> None:
        """Save or update user."""
        ...

    def list_all(self) -> list[User]:
        """List all users."""
        ...


# -----------------------------------------------------------------------------
# Unit of Work (Transaction Management)
# -----------------------------------------------------------------------------


class UnitOfWorkPort(Protocol):
    """
    Unit of Work pattern for transaction management.

    Usage:
        with uow:
            uow.content.save(content)
            uow.commit()
    """

    # Repository access
    settings: SiteSettingsRepoPort
    content: ContentRepoPort
    assets: AssetRepoPort
    asset_versions: AssetVersionRepoPort
    publish_jobs: PublishJobRepoPort
    analytics: AnalyticsAggregateRepoPort
    redirects: RedirectRepoPort
    audit_log: AuditLogRepoPort
    users: UserRepoPort

    def __enter__(self) -> UnitOfWorkPort:
        """Enter transaction context."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit transaction context (rollback on exception)."""
        ...

    def commit(self) -> None:
        """Commit the transaction."""
        ...

    def rollback(self) -> None:
        """Rollback the transaction."""
        ...
