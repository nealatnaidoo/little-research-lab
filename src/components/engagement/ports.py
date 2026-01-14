"""
Engagement component port definitions.

Spec refs: E14.1
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


class EngagementRepoPort(Protocol):
    """Repository interface for engagement sessions."""

    def store_session(
        self,
        content_id: UUID,
        date: datetime,
        time_bucket: str,
        scroll_bucket: str,
        is_engaged: bool,
    ) -> None:
        """
        Store or increment an engagement session aggregate.

        Sessions are aggregated by (content_id, date, time_bucket, scroll_bucket).
        If a matching aggregate exists, increment its count.
        """
        ...

    def get_totals(
        self,
        content_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        engaged_only: bool = False,
    ) -> dict[str, int]:
        """
        Get engagement totals.

        Returns dict with:
        - total_sessions: Total session count
        - engaged_sessions: Sessions meeting threshold
        """
        ...

    def get_distribution(
        self,
        distribution_type: str,  # "time" or "scroll"
        content_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get engagement distribution by bucket.

        Returns list of dicts with:
        - bucket: The bucket label
        - count: Number of sessions in bucket
        """
        ...

    def get_top_engaged_content(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get top content by engagement.

        Returns list of dicts with:
        - content_id: UUID
        - total_sessions: int
        - engaged_sessions: int
        """
        ...


class EngagementRulesPort(Protocol):
    """Port for engagement rules configuration."""

    def is_enabled(self) -> bool:
        """Check if engagement tracking is enabled."""
        ...

    def get_min_time_on_page_seconds(self) -> int:
        """Get minimum time on page for engaged session (default 30)."""
        ...

    def get_min_scroll_depth_percent(self) -> int:
        """Get minimum scroll depth for engaged session (default 25)."""
        ...

    def get_time_buckets(self) -> tuple[str, ...]:
        """Get time bucket definitions."""
        ...

    def get_scroll_buckets(self) -> tuple[str, ...]:
        """Get scroll bucket definitions."""
        ...


class TimePort(Protocol):
    """Time provider interface."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...

    def truncate_to_day(self, dt: datetime) -> datetime:
        """Truncate datetime to day (zero out time component)."""
        ...
