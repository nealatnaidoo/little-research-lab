"""
Admin Analytics API (E6.4).

Provides endpoints for querying analytics data.

Spec refs: E6.4, TA-0041, TA-0042, E14
Test assertions:
- TA-0041: Dashboard queries return correct aggregated data
- TA-0042: Analytics data can be queried by time range and filters
- E14: Engagement data queries
"""

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.adapters.sqlite_db import SQLiteEngagementRepo
from src.components.analytics._aggregate import (
    AggregateService,
    BucketType,
    InMemoryAggregateRepo,
)
from src.components.engagement import EngagementRepoPort

router = APIRouter()


# --- Request/Response Models ---


class TotalsResponse(BaseModel):
    """Totals response model."""

    total: int
    total_with_bots: int
    real: int
    bot: int
    start: str
    end: str


class TimeSeriesPoint(BaseModel):
    """Time series data point."""

    timestamp: str
    count: int


class TimeSeriesResponse(BaseModel):
    """Time series response model."""

    bucket_type: str
    points: list[TimeSeriesPoint]


class TopContentItem(BaseModel):
    """Top content item."""

    content_id: str
    count: int


class TopContentResponse(BaseModel):
    """Top content response model."""

    items: list[TopContentItem]


class TopSourceItem(BaseModel):
    """Top source item."""

    source: str | None
    medium: str | None
    count: int


class TopSourcesResponse(BaseModel):
    """Top sources response model."""

    items: list[TopSourceItem]


class TopReferrerItem(BaseModel):
    """Top referrer item."""

    domain: str
    count: int


class TopReferrersResponse(BaseModel):
    """Top referrers response model."""

    items: list[TopReferrerItem]


class EngagementTotalsResponse(BaseModel):
    """Engagement totals response model."""

    total_sessions: int
    engaged_sessions: int
    engagement_rate: float  # 0.0 to 1.0


class EngagementDistributionItem(BaseModel):
    """Engagement distribution item."""

    time_bucket: str
    scroll_bucket: str
    count: int


class EngagementDistributionResponse(BaseModel):
    """Engagement distribution response model."""

    items: list[EngagementDistributionItem]


class TopEngagedContentItem(BaseModel):
    """Top engaged content item."""

    content_id: str
    engaged_count: int


class TopEngagedContentResponse(BaseModel):
    """Top engaged content response model."""

    items: list[TopEngagedContentItem]


class DashboardResponse(BaseModel):
    """Dashboard summary response."""

    period_start: str
    period_end: str
    totals: TotalsResponse
    time_series: TimeSeriesResponse
    top_content: TopContentResponse
    top_sources: TopSourcesResponse
    top_referrers: TopReferrersResponse
    engagement: EngagementTotalsResponse | None = None


# --- Dependencies ---


_aggregate_repo = InMemoryAggregateRepo()
_aggregate_service = AggregateService(repo=_aggregate_repo)

# Database path for engagement repo
_db_path = os.environ.get("DATABASE_URL", "lrl.db")
if _db_path.startswith("sqlite:///"):
    _db_path = _db_path.replace("sqlite:///", "")


def get_aggregate_service() -> AggregateService:
    """Get aggregate service dependency."""
    return _aggregate_service


def get_engagement_repo() -> EngagementRepoPort:
    """Get engagement repo dependency."""
    return SQLiteEngagementRepo(_db_path)


def reset_aggregate_service() -> None:
    """Reset aggregate service (for testing)."""
    global _aggregate_repo, _aggregate_service
    _aggregate_repo = InMemoryAggregateRepo()
    _aggregate_service = AggregateService(repo=_aggregate_repo)


# --- Helper Functions ---


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string to datetime object."""
    try:
        # Try ISO format with Z
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {dt_str}",
        ) from e


def get_default_time_range() -> tuple[datetime, datetime]:
    """Get default time range (last 7 days)."""
    end = datetime.now(UTC)
    start = end - timedelta(days=7)
    return start, end


def parse_bucket_type(bucket_type: str) -> BucketType:
    """Parse bucket type string to enum."""
    try:
        return BucketType(bucket_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bucket type: {bucket_type}. Must be one of: minute, hour, day",
        ) from None


# --- Routes ---


@router.get("/totals", response_model=TotalsResponse)
def get_totals(
    start: str | None = Query(None, description="Start datetime (ISO format)"),
    end: str | None = Query(None, description="End datetime (ISO format)"),
    bucket_type: str = Query("day", description="Bucket type: minute, hour, day"),
    event_type: str | None = Query(None, description="Filter by event type"),
    content_id: str | None = Query(None, description="Filter by content ID"),
    exclude_bots: bool = Query(True, description="Exclude bot traffic"),
    service: AggregateService = Depends(get_aggregate_service),
) -> TotalsResponse:
    """
    Get aggregated totals for a time range (TA-0041).

    Returns total counts split by real/bot traffic.
    """
    if start and end:
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
    else:
        start_dt, end_dt = get_default_time_range()

    bt = parse_bucket_type(bucket_type)

    content_uuid = UUID(content_id) if content_id else None

    totals = service.get_totals(
        bucket_type=bt,
        start=start_dt,
        end=end_dt,
        event_type=event_type,
        content_id=content_uuid,
        exclude_bots=exclude_bots,
    )

    return TotalsResponse(
        total=totals["total"],
        total_with_bots=totals["total_with_bots"],
        real=totals["real"],
        bot=totals["bot"],
        start=start_dt.isoformat(),
        end=end_dt.isoformat(),
    )


@router.get("/time-series", response_model=TimeSeriesResponse)
def get_time_series(
    start: str | None = Query(None, description="Start datetime (ISO format)"),
    end: str | None = Query(None, description="End datetime (ISO format)"),
    bucket_type: str = Query("hour", description="Bucket type: minute, hour, day"),
    event_type: str | None = Query(None, description="Filter by event type"),
    content_id: str | None = Query(None, description="Filter by content ID"),
    exclude_bots: bool = Query(True, description="Exclude bot traffic"),
    service: AggregateService = Depends(get_aggregate_service),
) -> TimeSeriesResponse:
    """
    Get time series data for charting (TA-0041).

    Returns data points with timestamps and counts.
    """
    if start and end:
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
    else:
        start_dt, end_dt = get_default_time_range()

    bt = parse_bucket_type(bucket_type)

    content_uuid = UUID(content_id) if content_id else None

    series = service.get_time_series(
        bucket_type=bt,
        start=start_dt,
        end=end_dt,
        event_type=event_type,
        content_id=content_uuid,
        exclude_bots=exclude_bots,
    )

    return TimeSeriesResponse(
        bucket_type=bt.value,
        points=[
            TimeSeriesPoint(
                timestamp=point["timestamp"].isoformat(),
                count=point["count"],
            )
            for point in series
        ],
    )


@router.get("/top-content", response_model=TopContentResponse)
def get_top_content(
    start: str | None = Query(None, description="Start datetime (ISO format)"),
    end: str | None = Query(None, description="End datetime (ISO format)"),
    bucket_type: str = Query("day", description="Bucket type: minute, hour, day"),
    event_type: str = Query("page_view", description="Event type"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
    exclude_bots: bool = Query(True, description="Exclude bot traffic"),
    service: AggregateService = Depends(get_aggregate_service),
) -> TopContentResponse:
    """
    Get top content by views (TA-0042).

    Returns content IDs sorted by view count.
    """
    if start and end:
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
    else:
        start_dt, end_dt = get_default_time_range()

    bt = parse_bucket_type(bucket_type)

    top = service.get_top_content(
        bucket_type=bt,
        start=start_dt,
        end=end_dt,
        event_type=event_type,
        limit=limit,
        exclude_bots=exclude_bots,
    )

    return TopContentResponse(
        items=[
            TopContentItem(
                content_id=str(item["content_id"]),
                count=item["count"],
            )
            for item in top
        ],
    )


@router.get("/top-sources", response_model=TopSourcesResponse)
def get_top_sources(
    start: str | None = Query(None, description="Start datetime (ISO format)"),
    end: str | None = Query(None, description="End datetime (ISO format)"),
    bucket_type: str = Query("day", description="Bucket type: minute, hour, day"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
    exclude_bots: bool = Query(True, description="Exclude bot traffic"),
    service: AggregateService = Depends(get_aggregate_service),
) -> TopSourcesResponse:
    """
    Get top traffic sources (TA-0042).

    Returns UTM sources sorted by view count.
    """
    if start and end:
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
    else:
        start_dt, end_dt = get_default_time_range()

    bt = parse_bucket_type(bucket_type)

    top = service.get_top_sources(
        bucket_type=bt,
        start=start_dt,
        end=end_dt,
        limit=limit,
        exclude_bots=exclude_bots,
    )

    return TopSourcesResponse(
        items=[
            TopSourceItem(
                source=item["source"],
                medium=item["medium"],
                count=item["count"],
            )
            for item in top
        ],
    )


@router.get("/top-referrers", response_model=TopReferrersResponse)
def get_top_referrers(
    start: str | None = Query(None, description="Start datetime (ISO format)"),
    end: str | None = Query(None, description="End datetime (ISO format)"),
    bucket_type: str = Query("day", description="Bucket type: minute, hour, day"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
    exclude_bots: bool = Query(True, description="Exclude bot traffic"),
    service: AggregateService = Depends(get_aggregate_service),
) -> TopReferrersResponse:
    """
    Get top referrer domains (TA-0042).

    Returns referrer domains sorted by view count.
    """
    if start and end:
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
    else:
        start_dt, end_dt = get_default_time_range()

    bt = parse_bucket_type(bucket_type)

    top = service.get_top_referrers(
        bucket_type=bt,
        start=start_dt,
        end=end_dt,
        limit=limit,
        exclude_bots=exclude_bots,
    )

    return TopReferrersResponse(
        items=[
            TopReferrerItem(
                domain=item["domain"],
                count=item["count"],
            )
            for item in top
        ],
    )


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    start: str | None = Query(None, description="Start datetime (ISO format)"),
    end: str | None = Query(None, description="End datetime (ISO format)"),
    bucket_type: str = Query("day", description="Bucket type for time series"),
    service: AggregateService = Depends(get_aggregate_service),
    engagement_repo: EngagementRepoPort = Depends(get_engagement_repo),
) -> DashboardResponse:
    """
    Get complete dashboard data (TA-0041, TA-0042, E14).

    Returns totals, time series, top content, sources, referrers, and engagement.
    """
    if start and end:
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
    else:
        start_dt, end_dt = get_default_time_range()

    bt = parse_bucket_type(bucket_type)

    # Get all dashboard data
    totals = service.get_totals(
        bucket_type=bt,
        start=start_dt,
        end=end_dt,
    )

    series = service.get_time_series(
        bucket_type=bt,
        start=start_dt,
        end=end_dt,
    )

    top_content = service.get_top_content(
        bucket_type=bt,
        start=start_dt,
        end=end_dt,
        limit=5,
    )

    top_sources = service.get_top_sources(
        bucket_type=bt,
        start=start_dt,
        end=end_dt,
        limit=5,
    )

    top_referrers = service.get_top_referrers(
        bucket_type=bt,
        start=start_dt,
        end=end_dt,
        limit=5,
    )

    # Get engagement data (E14)
    engagement_data = None
    try:
        engagement_totals = engagement_repo.get_totals(
            start_date=start_dt,
            end_date=end_dt,
        )
        total_sessions = engagement_totals.get("total_sessions", 0) or 0
        engaged_sessions = engagement_totals.get("engaged_sessions", 0) or 0
        engagement_rate = engaged_sessions / total_sessions if total_sessions > 0 else 0.0
        engagement_data = EngagementTotalsResponse(
            total_sessions=total_sessions,
            engaged_sessions=engaged_sessions,
            engagement_rate=engagement_rate,
        )
    except Exception:
        # Don't fail dashboard if engagement data fails
        pass

    return DashboardResponse(
        period_start=start_dt.isoformat(),
        period_end=end_dt.isoformat(),
        totals=TotalsResponse(
            total=totals["total"],
            total_with_bots=totals["total_with_bots"],
            real=totals["real"],
            bot=totals["bot"],
            start=start_dt.isoformat(),
            end=end_dt.isoformat(),
        ),
        time_series=TimeSeriesResponse(
            bucket_type=bt.value,
            points=[
                TimeSeriesPoint(
                    timestamp=point["timestamp"].isoformat(),
                    count=point["count"],
                )
                for point in series
            ],
        ),
        top_content=TopContentResponse(
            items=[
                TopContentItem(
                    content_id=str(item["content_id"]),
                    count=item["count"],
                )
                for item in top_content
            ],
        ),
        top_sources=TopSourcesResponse(
            items=[
                TopSourceItem(
                    source=item["source"],
                    medium=item["medium"],
                    count=item["count"],
                )
                for item in top_sources
            ],
        ),
        top_referrers=TopReferrersResponse(
            items=[
                TopReferrerItem(
                    domain=item["domain"],
                    count=item["count"],
                )
                for item in top_referrers
            ],
        ),
        engagement=engagement_data,
    )


@router.get("/engagement", response_model=EngagementTotalsResponse)
def get_engagement_totals(
    start: str | None = Query(None, description="Start datetime (ISO format)"),
    end: str | None = Query(None, description="End datetime (ISO format)"),
    content_id: str | None = Query(None, description="Filter by content ID"),
    engagement_repo: EngagementRepoPort = Depends(get_engagement_repo),
) -> EngagementTotalsResponse:
    """
    Get engagement totals for a time range (E14).

    Returns total and engaged session counts.
    """
    if start and end:
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
    else:
        start_dt, end_dt = get_default_time_range()

    content_uuid = UUID(content_id) if content_id else None

    totals = engagement_repo.get_totals(
        start_date=start_dt,
        end_date=end_dt,
        content_id=content_uuid,
    )

    total_sessions = totals.get("total_sessions", 0) or 0
    engaged_sessions = totals.get("engaged_sessions", 0) or 0
    engagement_rate = engaged_sessions / total_sessions if total_sessions > 0 else 0.0

    return EngagementTotalsResponse(
        total_sessions=total_sessions,
        engaged_sessions=engaged_sessions,
        engagement_rate=engagement_rate,
    )


@router.get("/engagement/distribution", response_model=EngagementDistributionResponse)
def get_engagement_distribution(
    start: str | None = Query(None, description="Start datetime (ISO format)"),
    end: str | None = Query(None, description="End datetime (ISO format)"),
    content_id: str | None = Query(None, description="Filter by content ID"),
    engagement_repo: EngagementRepoPort = Depends(get_engagement_repo),
) -> EngagementDistributionResponse:
    """
    Get engagement distribution by time and scroll buckets (E14).

    Returns counts per bucket combination.
    """
    if start and end:
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
    else:
        start_dt, end_dt = get_default_time_range()

    content_uuid = UUID(content_id) if content_id else None

    distribution = engagement_repo.get_distribution(
        distribution_type="combined",
        start_date=start_dt,
        end_date=end_dt,
        content_id=content_uuid,
    )

    return EngagementDistributionResponse(
        items=[
            EngagementDistributionItem(
                time_bucket=item["time_bucket"],
                scroll_bucket=item["scroll_bucket"],
                count=item["count"],
            )
            for item in distribution
        ],
    )


@router.get("/engagement/top-content", response_model=TopEngagedContentResponse)
def get_top_engaged_content(
    start: str | None = Query(None, description="Start datetime (ISO format)"),
    end: str | None = Query(None, description="End datetime (ISO format)"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
    engagement_repo: EngagementRepoPort = Depends(get_engagement_repo),
) -> TopEngagedContentResponse:
    """
    Get top content by engaged sessions (E14).

    Returns content IDs sorted by engaged session count.
    """
    if start and end:
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
    else:
        start_dt, end_dt = get_default_time_range()

    top = engagement_repo.get_top_engaged_content(
        start_date=start_dt,
        end_date=end_dt,
        limit=limit,
    )

    return TopEngagedContentResponse(
        items=[
            TopEngagedContentItem(
                content_id=str(item["content_id"]),
                engaged_count=item["engaged_count"],
            )
            for item in top
        ],
    )
