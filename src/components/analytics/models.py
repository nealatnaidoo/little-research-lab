"""
Analytics component input/output models.

Spec refs: E6.1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

# --- Validation Error ---


@dataclass(frozen=True)
class AnalyticsValidationError:
    """Analytics validation error."""

    code: str
    message: str
    field_name: str | None = None


# --- Enums ---


EventType = Literal["page_view", "outbound_click", "asset_download"]
UAClass = Literal["bot", "real", "unknown"]


# --- Analytics Event Model ---


@dataclass(frozen=True)
class AnalyticsEvent:
    """Validated analytics event."""

    event_type: EventType
    timestamp: datetime
    path: str | None = None
    content_id: UUID | None = None
    link_id: str | None = None
    asset_id: UUID | None = None
    asset_version_id: UUID | None = None
    referrer: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None
    ua_class: UAClass = "unknown"


# --- Input Models ---


@dataclass(frozen=True)
class IngestEventInput:
    """Input for ingesting raw analytics event."""

    data: dict[str, Any]
    client_key: str | None = None


@dataclass(frozen=True)
class QueryTotalsInput:
    """Input for querying aggregated totals."""

    event_type: EventType | None = None
    content_id: UUID | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


@dataclass(frozen=True)
class QueryTimeseriesInput:
    """Input for querying time-bucketed data."""

    bucket_type: Literal["minute", "hour", "day"]
    event_type: EventType | None = None
    content_id: UUID | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = 100


@dataclass(frozen=True)
class QueryTopContentInput:
    """Input for querying top content by views."""

    event_type: EventType = "page_view"
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = 10


# --- Output Models ---


@dataclass(frozen=True)
class IngestOutput:
    """Output for ingestion result."""

    event: AnalyticsEvent | None
    accepted: bool
    errors: list[AnalyticsValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class TotalsOutput:
    """Output for aggregated totals."""

    count_total: int
    count_real: int
    count_bot: int
    errors: list[AnalyticsValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class TimeseriesDataPoint:
    """Single data point in timeseries."""

    bucket_start: datetime
    count_total: int
    count_real: int
    count_bot: int


@dataclass(frozen=True)
class TimeseriesOutput:
    """Output for time-bucketed data."""

    data_points: tuple[TimeseriesDataPoint, ...]
    errors: list[AnalyticsValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class TopContentItem:
    """Single item in top content list."""

    content_id: UUID
    count_total: int
    count_real: int


@dataclass(frozen=True)
class TopContentOutput:
    """Output for top content query."""

    items: tuple[TopContentItem, ...]
    errors: list[AnalyticsValidationError] = field(default_factory=list)
    success: bool = True
