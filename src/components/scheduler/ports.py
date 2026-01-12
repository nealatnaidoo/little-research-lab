"""
Scheduler component port definitions.

Spec refs: E5.2
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID


class PublishJobRepoPort(Protocol):
    """Repository interface for publish jobs."""

    def get_by_id(self, job_id: UUID) -> object | None:
        """Get job by ID."""
        ...

    def get_by_idempotency_key(
        self,
        content_id: UUID,
        publish_at_utc: datetime,
    ) -> object | None:
        """Get job by idempotency key."""
        ...

    def save(self, job: object) -> object:
        """Save or update job."""
        ...

    def delete(self, job_id: UUID) -> None:
        """Delete job."""
        ...

    def list_due_jobs(
        self,
        now_utc: datetime,
        limit: int = 10,
    ) -> list[object]:
        """List jobs due for execution."""
        ...

    def claim_job(
        self,
        job_id: UUID,
        worker_id: str,
        now_utc: datetime,
    ) -> object | None:
        """Atomically claim a job."""
        ...

    def list_in_range(
        self,
        start_utc: datetime,
        end_utc: datetime,
        statuses: list[str] | None = None,
    ) -> list[object]:
        """List jobs with publish_at in the given date range."""
        ...


class ContentPublisherPort(Protocol):
    """Content publisher interface for executing publishes."""

    def publish(self, content_id: UUID) -> tuple[bool, str | None]:
        """Publish content by ID. Returns (success, error_message)."""
        ...


class TimePort(Protocol):
    """Time port for DST-safe operations."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...

    def is_past_or_now(self, utc_dt: datetime) -> bool:
        """Check if datetime is at or before now."""
        ...

    def is_future(self, utc_dt: datetime, grace_seconds: int = 0) -> bool:
        """Check if datetime is in the future."""
        ...


class RulesPort(Protocol):
    """Port for scheduler rules configuration."""

    def get_max_attempts(self) -> int:
        """Get maximum retry attempts."""
        ...

    def get_backoff_seconds(self) -> tuple[int, ...]:
        """Get backoff schedule in seconds."""
        ...

    def get_publish_grace_seconds(self) -> int:
        """Get grace period for publish scheduling."""
        ...

    def get_never_publish_early(self) -> bool:
        """Get whether to enforce never publishing early."""
        ...
