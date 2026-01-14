"""
AnalyticsAggregateService (E6.1, E6.4) - Aggregate bucketing writer.

Handles aggregation of analytics events into time buckets.

Spec refs: E6.1, E6.4, TA-0041
Test assertions:
- TA-0041: Aggregate buckets are created and updated correctly

Key behaviors:
- Bucket events into minute/hour/day time periods
- Track dimensions (content, UTM, referrer, etc.)
- Separate counts by bot/real classification
- Support rollup queries by time range
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Protocol
from uuid import UUID, uuid4

from src.core.entities import AnalyticsEventAggregate

# --- Enums ---


class BucketType(str, Enum):
    """Time bucket types."""

    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


class UAClass(str, Enum):
    """User agent classification."""

    BOT = "bot"
    REAL = "real"
    UNKNOWN = "unknown"


# --- Configuration ---


@dataclass(frozen=True)
class AggregateConfig:
    """Aggregate configuration."""

    enabled: bool = True

    # Bucket types to write
    bucket_types: tuple[BucketType, ...] = (
        BucketType.MINUTE,
        BucketType.HOUR,
        BucketType.DAY,
    )

    # Treat unknown UA as real for counts
    treat_unknown_as_real: bool = True

    # Dimensions to aggregate by
    include_utm_dimensions: bool = True
    include_referrer_domain: bool = True

    # Retention periods (for cleanup)
    retention_minutes: int = 60 * 24 * 7  # 7 days
    retention_hours: int = 24 * 90  # 90 days
    retention_days: int = 365 * 2  # 2 years


DEFAULT_CONFIG = AggregateConfig()


# --- Repository Protocol ---


class AggregateRepoPort(Protocol):
    """Aggregate repository interface."""

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


# --- Time Port Protocol ---


class TimePort(Protocol):
    """Time provider interface."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...


# --- Input Event Model ---


@dataclass
class AggregateInput:
    """Input for aggregation (from validated analytics event)."""

    event_type: str
    timestamp: datetime
    content_id: UUID | None = None
    asset_id: UUID | None = None
    link_id: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    referrer_domain: str | None = None
    ua_class: UAClass = UAClass.UNKNOWN


# --- Bucket Calculation ---


def calculate_bucket_start(timestamp: datetime, bucket_type: BucketType) -> datetime:
    """
    Calculate the start of a time bucket for a given timestamp.

    All timestamps are normalized to UTC.
    """
    # Ensure UTC
    if timestamp.tzinfo is None:
        ts = timestamp.replace(tzinfo=UTC)
    else:
        ts = timestamp.astimezone(UTC)

    if bucket_type == BucketType.MINUTE:
        return ts.replace(second=0, microsecond=0)
    elif bucket_type == BucketType.HOUR:
        return ts.replace(minute=0, second=0, microsecond=0)
    elif bucket_type == BucketType.DAY:
        return ts.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        msg = f"Unknown bucket type: {bucket_type}"
        raise ValueError(msg)


def calculate_bucket_end(bucket_start: datetime, bucket_type: BucketType) -> datetime:
    """Calculate the end of a time bucket (exclusive)."""
    if bucket_type == BucketType.MINUTE:
        return bucket_start + timedelta(minutes=1)
    elif bucket_type == BucketType.HOUR:
        return bucket_start + timedelta(hours=1)
    elif bucket_type == BucketType.DAY:
        return bucket_start + timedelta(days=1)
    else:
        msg = f"Unknown bucket type: {bucket_type}"
        raise ValueError(msg)


# --- In-Memory Repository ---


class InMemoryAggregateRepo:
    """In-memory aggregate repository for testing/dev."""

    def __init__(self, time_port: TimePort | None = None) -> None:
        self._buckets: dict[UUID, AnalyticsEventAggregate] = {}
        self._index: dict[str, UUID] = {}  # dimension_key -> bucket_id
        self._time_port = time_port

    def _now(self) -> datetime:
        """Get current time via injected port (deterministic core)."""
        if self._time_port:
            return self._time_port.now_utc()
        # Fallback for backward compatibility - should inject TimePort in production
        from src.adapters.time_london import LondonTimeAdapter

        return LondonTimeAdapter().now_utc()

    def _build_key(
        self,
        bucket_type: str,
        bucket_start: datetime,
        event_type: str,
        dimensions: dict[str, Any],
    ) -> str:
        """Build a unique key for a bucket."""
        dim_parts = sorted(f"{k}={v}" for k, v in dimensions.items() if v is not None)
        return f"{bucket_type}:{bucket_start.isoformat()}:{event_type}:{':'.join(dim_parts)}"

    def get_or_create_bucket(
        self,
        bucket_type: str,
        bucket_start: datetime,
        event_type: str,
        dimensions: dict[str, Any],
    ) -> AnalyticsEventAggregate:
        """Get or create an aggregate bucket."""
        key = self._build_key(bucket_type, bucket_start, event_type, dimensions)

        if key in self._index:
            return self._buckets[self._index[key]]

        # Create new bucket
        bucket = AnalyticsEventAggregate(
            id=uuid4(),
            bucket_type=bucket_type,  # type: ignore[arg-type]
            bucket_start=bucket_start,
            event_type=event_type,  # type: ignore[arg-type]
            content_id=dimensions.get("content_id"),
            asset_id=dimensions.get("asset_id"),
            link_id=dimensions.get("link_id"),
            utm_source=dimensions.get("utm_source"),
            utm_medium=dimensions.get("utm_medium"),
            utm_campaign=dimensions.get("utm_campaign"),
            referrer_domain=dimensions.get("referrer_domain"),
            ua_class=dimensions.get("ua_class", "unknown"),
            count_total=0,
            count_real=0,
            count_bot=0,
        )

        self._buckets[bucket.id] = bucket
        self._index[key] = bucket.id

        return bucket

    def increment(
        self,
        bucket_id: UUID,
        count_total: int = 1,
        count_real: int = 0,
        count_bot: int = 0,
    ) -> None:
        """Increment counts for a bucket."""
        if bucket_id not in self._buckets:
            msg = f"Bucket not found: {bucket_id}"
            raise ValueError(msg)

        bucket = self._buckets[bucket_id]
        # Create new bucket with updated counts (immutable-ish)
        updated = AnalyticsEventAggregate(
            id=bucket.id,
            bucket_type=bucket.bucket_type,
            bucket_start=bucket.bucket_start,
            event_type=bucket.event_type,
            content_id=bucket.content_id,
            asset_id=bucket.asset_id,
            link_id=bucket.link_id,
            utm_source=bucket.utm_source,
            utm_medium=bucket.utm_medium,
            utm_campaign=bucket.utm_campaign,
            referrer_domain=bucket.referrer_domain,
            ua_class=bucket.ua_class,
            count_total=bucket.count_total + count_total,
            count_real=bucket.count_real + count_real,
            count_bot=bucket.count_bot + count_bot,
            created_at=bucket.created_at,
            updated_at=self._now(),
        )
        self._buckets[bucket_id] = updated

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
        results = []

        for bucket in self._buckets.values():
            # Filter by bucket type
            if bucket.bucket_type != bucket_type:
                continue

            # Filter by time range
            if bucket.bucket_start < start or bucket.bucket_start >= end:
                continue

            # Filter by event type
            if event_type is not None and bucket.event_type != event_type:
                continue

            # Filter by content_id
            if content_id is not None and bucket.content_id != content_id:
                continue

            # Filter by dimensions
            if dimensions:
                match = True
                for k, v in dimensions.items():
                    if v is not None:
                        bucket_val = getattr(bucket, k, None)
                        if bucket_val != v:
                            match = False
                            break
                if not match:
                    continue

            results.append(bucket)

        # Sort by bucket_start
        return sorted(results, key=lambda b: b.bucket_start)

    def clear(self) -> None:
        """Clear all buckets."""
        self._buckets.clear()
        self._index.clear()


# --- Aggregate Service ---


class AggregateService:
    """
    Analytics aggregate service (E6.1, E6.4).

    Aggregates events into time buckets for efficient querying.
    """

    def __init__(
        self,
        repo: AggregateRepoPort | None = None,
        time_port: TimePort | None = None,
        config: AggregateConfig | None = None,
    ) -> None:
        """Initialize service."""
        self._repo = repo or InMemoryAggregateRepo()
        self._time_port = time_port
        self._config = config or DEFAULT_CONFIG

    def _now(self) -> datetime:
        """Get current time via injected port (deterministic core)."""
        if self._time_port:
            return self._time_port.now_utc()
        # Fallback for backward compatibility - should inject TimePort in production
        from src.adapters.time_london import LondonTimeAdapter

        return LondonTimeAdapter().now_utc()

    def record(self, event: AggregateInput) -> list[AnalyticsEventAggregate]:
        """
        Record an event to all configured bucket types (TA-0041).

        Returns the updated/created buckets.
        """
        if not self._config.enabled:
            return []

        buckets = []

        # Build base dimensions
        dimensions = self._build_dimensions(event)

        # Determine count increments based on ua_class
        count_total = 1
        count_real = 0
        count_bot = 0

        if event.ua_class == UAClass.BOT:
            count_bot = 1
        elif event.ua_class == UAClass.REAL:
            count_real = 1
        elif event.ua_class == UAClass.UNKNOWN:
            if self._config.treat_unknown_as_real:
                count_real = 1
            # else: neither real nor bot

        # Record to each bucket type
        for bucket_type in self._config.bucket_types:
            bucket_start = calculate_bucket_start(event.timestamp, bucket_type)

            bucket = self._repo.get_or_create_bucket(
                bucket_type=bucket_type.value,
                bucket_start=bucket_start,
                event_type=event.event_type,
                dimensions=dimensions,
            )

            self._repo.increment(
                bucket_id=bucket.id,
                count_total=count_total,
                count_real=count_real,
                count_bot=count_bot,
            )

            # Re-fetch to get updated counts
            updated = self._repo.get_or_create_bucket(
                bucket_type=bucket_type.value,
                bucket_start=bucket_start,
                event_type=event.event_type,
                dimensions=dimensions,
            )
            buckets.append(updated)

        return buckets

    def _build_dimensions(self, event: AggregateInput) -> dict[str, Any]:
        """Build dimension dict from event."""
        dimensions: dict[str, Any] = {
            "content_id": event.content_id,
            "asset_id": event.asset_id,
            "link_id": event.link_id,
            "ua_class": event.ua_class.value,
        }

        if self._config.include_utm_dimensions:
            dimensions["utm_source"] = event.utm_source
            dimensions["utm_medium"] = event.utm_medium
            dimensions["utm_campaign"] = event.utm_campaign

        if self._config.include_referrer_domain:
            dimensions["referrer_domain"] = event.referrer_domain

        return dimensions

    def query_buckets(
        self,
        bucket_type: BucketType,
        start: datetime,
        end: datetime,
        event_type: str | None = None,
        content_id: UUID | None = None,
        **dimension_filters: Any,
    ) -> list[AnalyticsEventAggregate]:
        """
        Query aggregate buckets (TA-0041).

        Returns buckets matching the criteria, sorted by time.
        """
        return self._repo.query(
            bucket_type=bucket_type.value,
            start=start,
            end=end,
            event_type=event_type,
            content_id=content_id,
            dimensions=dimension_filters if dimension_filters else None,
        )

    def get_totals(
        self,
        bucket_type: BucketType,
        start: datetime,
        end: datetime,
        event_type: str | None = None,
        content_id: UUID | None = None,
        exclude_bots: bool = True,
    ) -> dict[str, int]:
        """
        Get aggregated totals for a time range.

        Returns dict with total, real, and bot counts.
        """
        buckets = self.query_buckets(
            bucket_type=bucket_type,
            start=start,
            end=end,
            event_type=event_type,
            content_id=content_id,
        )

        total = sum(b.count_total for b in buckets)
        real = sum(b.count_real for b in buckets)
        bot = sum(b.count_bot for b in buckets)

        return {
            "total": real if exclude_bots else total,
            "total_with_bots": total,
            "real": real,
            "bot": bot,
        }

    def get_time_series(
        self,
        bucket_type: BucketType,
        start: datetime,
        end: datetime,
        event_type: str | None = None,
        content_id: UUID | None = None,
        exclude_bots: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Get time series data for charting.

        Returns list of {timestamp, count} dicts.
        """
        buckets = self.query_buckets(
            bucket_type=bucket_type,
            start=start,
            end=end,
            event_type=event_type,
            content_id=content_id,
        )

        # Group by timestamp (in case multiple dimension combos)
        by_time: dict[datetime, int] = {}
        for bucket in buckets:
            count = bucket.count_real if exclude_bots else bucket.count_total
            if bucket.bucket_start in by_time:
                by_time[bucket.bucket_start] += count
            else:
                by_time[bucket.bucket_start] = count

        return [{"timestamp": ts, "count": count} for ts, count in sorted(by_time.items())]

    def get_top_content(
        self,
        bucket_type: BucketType,
        start: datetime,
        end: datetime,
        event_type: str = "page_view",
        limit: int = 10,
        exclude_bots: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Get top content by views.

        Returns list of {content_id, count} dicts.
        """
        buckets = self.query_buckets(
            bucket_type=bucket_type,
            start=start,
            end=end,
            event_type=event_type,
        )

        # Group by content_id
        by_content: dict[UUID | None, int] = {}
        for bucket in buckets:
            if bucket.content_id is None:
                continue
            count = bucket.count_real if exclude_bots else bucket.count_total
            if bucket.content_id in by_content:
                by_content[bucket.content_id] += count
            else:
                by_content[bucket.content_id] = count

        # Sort by count desc and limit
        sorted_content = sorted(by_content.items(), key=lambda x: x[1], reverse=True)

        return [{"content_id": cid, "count": count} for cid, count in sorted_content[:limit]]

    def get_top_sources(
        self,
        bucket_type: BucketType,
        start: datetime,
        end: datetime,
        limit: int = 10,
        exclude_bots: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Get top traffic sources by views.

        Returns list of {source, medium, count} dicts.
        """
        buckets = self.query_buckets(
            bucket_type=bucket_type,
            start=start,
            end=end,
            event_type="page_view",
        )

        # Group by source/medium
        by_source: dict[tuple[str | None, str | None], int] = {}
        for bucket in buckets:
            key = (bucket.utm_source, bucket.utm_medium)
            count = bucket.count_real if exclude_bots else bucket.count_total
            if key in by_source:
                by_source[key] += count
            else:
                by_source[key] = count

        # Sort by count desc and limit
        sorted_sources = sorted(by_source.items(), key=lambda x: x[1], reverse=True)

        return [
            {"source": src, "medium": med, "count": count}
            for (src, med), count in sorted_sources[:limit]
        ]

    def get_top_referrers(
        self,
        bucket_type: BucketType,
        start: datetime,
        end: datetime,
        limit: int = 10,
        exclude_bots: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Get top referrer domains.

        Returns list of {domain, count} dicts.
        """
        buckets = self.query_buckets(
            bucket_type=bucket_type,
            start=start,
            end=end,
            event_type="page_view",
        )

        # Group by referrer_domain
        by_domain: dict[str | None, int] = {}
        for bucket in buckets:
            domain = bucket.referrer_domain
            if domain is None:
                continue
            count = bucket.count_real if exclude_bots else bucket.count_total
            if domain in by_domain:
                by_domain[domain] += count
            else:
                by_domain[domain] = count

        # Sort by count desc and limit
        sorted_domains = sorted(by_domain.items(), key=lambda x: x[1], reverse=True)

        return [{"domain": domain, "count": count} for domain, count in sorted_domains[:limit]]


# --- Factory ---


def create_aggregate_service(
    repo: AggregateRepoPort | None = None,
    time_port: TimePort | None = None,
    config: AggregateConfig | None = None,
) -> AggregateService:
    """Create an AggregateService."""
    return AggregateService(
        repo=repo,
        time_port=time_port,
        config=config,
    )
