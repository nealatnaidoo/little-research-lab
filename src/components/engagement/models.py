"""
Engagement component input/output models.

Spec refs: E14.1, E14.2, E14.3
Test assertions: TA-0058, TA-0059, TA-0060
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID


# --- Bucket Types ---

TimeBucket = Literal["0-10s", "10-30s", "30-60s", "60-120s", "120-300s", "300+s"]
ScrollBucket = Literal["0-25%", "25-50%", "50-75%", "75-100%"]


# --- Validation Error ---


@dataclass(frozen=True)
class EngagementValidationError:
    """Engagement validation error."""

    code: str
    message: str
    field_name: str | None = None


# --- Engagement Session Model ---


@dataclass(frozen=True)
class EngagementSession:
    """
    Bucketed engagement session (TA-0060).

    Privacy invariant: No precise timestamps, durations, or scroll depths stored.
    Only bucketed values that prevent fingerprinting.
    """

    content_id: UUID
    date: datetime  # Truncated to day (no time component)
    time_bucket: TimeBucket
    scroll_bucket: ScrollBucket
    is_engaged: bool  # Met threshold criteria


# --- Input Models ---


@dataclass(frozen=True)
class CalculateEngagementInput:
    """
    Input for calculating engagement metrics from raw values.

    The raw values are bucketed before storage (TA-0060).
    """

    content_id: UUID
    time_on_page_seconds: float
    scroll_depth_percent: float
    timestamp: datetime | None = None  # Optional, defaults to now


@dataclass(frozen=True)
class QueryEngagementTotalsInput:
    """Input for querying engagement totals."""

    content_id: UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    engaged_only: bool = False  # Only count sessions that met threshold


@dataclass(frozen=True)
class QueryEngagementDistributionInput:
    """Input for querying engagement distribution by bucket."""

    content_id: UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    distribution_type: Literal["time", "scroll"] = "time"


@dataclass(frozen=True)
class QueryTopEngagedContentInput:
    """Input for querying top content by engagement."""

    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int = 10


# --- Output Models ---


@dataclass(frozen=True)
class CalculateEngagementOutput:
    """Output from engagement calculation."""

    session: EngagementSession | None
    is_engaged: bool
    time_bucket: TimeBucket
    scroll_bucket: ScrollBucket
    errors: list[EngagementValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class EngagementTotalsOutput:
    """Output for engagement totals query."""

    total_sessions: int
    engaged_sessions: int
    engagement_rate: float  # engaged / total (0.0 - 1.0)
    errors: list[EngagementValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class BucketCount:
    """Count for a specific bucket."""

    bucket: str
    count: int
    percentage: float  # of total


@dataclass(frozen=True)
class EngagementDistributionOutput:
    """Output for engagement distribution query."""

    distribution_type: Literal["time", "scroll"]
    buckets: tuple[BucketCount, ...]
    total_sessions: int
    errors: list[EngagementValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class TopEngagedContentItem:
    """Single item in top engaged content list."""

    content_id: UUID
    total_sessions: int
    engaged_sessions: int
    engagement_rate: float


@dataclass(frozen=True)
class TopEngagedContentOutput:
    """Output for top engaged content query."""

    items: tuple[TopEngagedContentItem, ...]
    errors: list[EngagementValidationError] = field(default_factory=list)
    success: bool = True
