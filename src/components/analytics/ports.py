"""
Analytics component port definitions.

Spec refs: E6.1
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


class AnalyticsRepoPort(Protocol):
    """Repository interface for analytics events/aggregates."""

    def get_totals(
        self,
        event_type: str | None = None,
        content_id: UUID | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, int]:
        """Get aggregated totals. Returns dict with count_total, count_real, count_bot."""
        ...

    def get_timeseries(
        self,
        bucket_type: str,
        event_type: str | None = None,
        content_id: UUID | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get time-bucketed data. Returns list of dicts with bucket_start, counts."""
        ...

    def get_top_content(
        self,
        event_type: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get top content by views. Returns list with content_id, counts."""
        ...


class EventStorePort(Protocol):
    """Event store interface for storing analytics events."""

    def store(self, event: object) -> None:
        """Store an analytics event."""
        ...


class DedupePort(Protocol):
    """Deduplication logic interface."""

    def is_duplicate(self, event_hash: str, window_seconds: int) -> bool:
        """Check if event is a duplicate within time window."""
        ...

    def record_event(self, event_hash: str, window_seconds: int) -> None:
        """Record event for deduplication."""
        ...


class RateLimiterPort(Protocol):
    """Rate limiter interface."""

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if rate limit allows request. Returns True if allowed."""
        ...

    def record_request(self, key: str, window_seconds: int) -> None:
        """Record a request for rate limiting."""
        ...


class TimePort(Protocol):
    """Time provider interface."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...


class RulesPort(Protocol):
    """Port for analytics rules configuration."""

    def is_enabled(self) -> bool:
        """Check if analytics is enabled."""
        ...

    def get_allowed_event_types(self) -> frozenset[str]:
        """Get allowed event types."""
        ...

    def get_allowed_fields(self) -> frozenset[str]:
        """Get allowed fields."""
        ...

    def get_forbidden_fields(self) -> frozenset[str]:
        """Get forbidden (PII) fields."""
        ...

    def get_rate_limit_config(self) -> dict[str, int]:
        """Get rate limit config (window_seconds, max_requests)."""
        ...

    def get_timestamp_limits(self) -> dict[str, int]:
        """Get timestamp validation limits (max_age_seconds, max_future_seconds)."""
        ...

    def exclude_bots_from_counts(self) -> bool:
        """Check if bots should be excluded from counts."""
        ...
