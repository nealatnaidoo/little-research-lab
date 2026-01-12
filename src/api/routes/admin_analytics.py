"""
Admin Analytics API (E6.4).

Provides endpoints for querying analytics data.

Spec refs: E6.4, TA-0041, TA-0042
Test assertions:
- TA-0041: Dashboard queries return correct aggregated data
- TA-0042: Analytics data can be queried by time range and filters
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.components.analytics._aggregate import (
    AggregateService,
    BucketType,
    InMemoryAggregateRepo,
)

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


class DashboardResponse(BaseModel):
    """Dashboard summary response."""

    period_start: str
    period_end: str
    totals: TotalsResponse
    time_series: TimeSeriesResponse
    top_content: TopContentResponse
    top_sources: TopSourcesResponse
    top_referrers: TopReferrersResponse


# --- Dependencies ---


_aggregate_repo = InMemoryAggregateRepo()
_aggregate_service = AggregateService(repo=_aggregate_repo)


def get_aggregate_service() -> AggregateService:
    """Get aggregate service dependency."""
    return _aggregate_service


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
) -> DashboardResponse:
    """
    Get complete dashboard data (TA-0041, TA-0042).

    Returns totals, time series, top content, sources, and referrers.
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
    )
