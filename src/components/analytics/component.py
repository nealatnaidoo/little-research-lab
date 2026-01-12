"""
Analytics component - Event ingestion and aggregation.

Spec refs: E6.1
Test assertions: TA-0034, TA-0035, TA-0040, TA-0041, TA-0042

Ingests, deduplicates, and aggregates analytics events with privacy enforcement.

Invariants:
- I1: No PII stored (IP, user agent, cookies, email) - HV2
- I2: Forbidden fields rejected on ingest
- I3: Bot traffic classified and tracked separately
- I4: Events deduplicated within time window
- I5: Aggregates rolled up by minute/hour/day
"""

from __future__ import annotations

from ._impl import (
    AnalyticsEvent as LegacyEvent,
)
from ._impl import (
    AnalyticsIngestionService,
    IngestionConfig,
)
from ._impl import (
    IngestionError as LegacyError,
)
from .models import (
    AnalyticsEvent,
    AnalyticsValidationError,
    IngestEventInput,
    IngestOutput,
    QueryTimeseriesInput,
    QueryTopContentInput,
    QueryTotalsInput,
    TimeseriesDataPoint,
    TimeseriesOutput,
    TopContentItem,
    TopContentOutput,
    TotalsOutput,
)
from .ports import (
    AnalyticsRepoPort,
    EventStorePort,
    RateLimiterPort,
    RulesPort,
    TimePort,
)


def _convert_event(legacy: LegacyEvent | None) -> AnalyticsEvent | None:
    """Convert legacy event to component model."""
    if legacy is None:
        return None
    return AnalyticsEvent(
        event_type=legacy.event_type.value,
        timestamp=legacy.timestamp,
        path=legacy.path,
        content_id=legacy.content_id,
        link_id=legacy.link_id,
        asset_id=legacy.asset_id,
        asset_version_id=legacy.asset_version_id,
        referrer=legacy.referrer,
        utm_source=legacy.utm_source,
        utm_medium=legacy.utm_medium,
        utm_campaign=legacy.utm_campaign,
        utm_content=legacy.utm_content,
        utm_term=legacy.utm_term,
        ua_class=legacy.ua_class.value,
    )


def _convert_errors(
    legacy_errors: list[LegacyError],
) -> list[AnalyticsValidationError]:
    """Convert legacy errors to component errors."""
    return [
        AnalyticsValidationError(
            code=e.code,
            message=e.message,
            field_name=e.field_name,
        )
        for e in legacy_errors
    ]


def _build_config(rules: RulesPort | None) -> IngestionConfig:
    """Build ingestion config from rules port."""
    if rules is None:
        return IngestionConfig()

    rate_limit = rules.get_rate_limit_config()
    timestamp_limits = rules.get_timestamp_limits()

    return IngestionConfig(
        enabled=rules.is_enabled(),
        allowed_event_types=rules.get_allowed_event_types(),
        allowed_fields=rules.get_allowed_fields(),
        forbidden_fields=rules.get_forbidden_fields(),
        rate_limit_window_seconds=rate_limit.get("window_seconds", 60),
        rate_limit_max_requests=rate_limit.get("max_requests", 600),
        max_timestamp_age_seconds=timestamp_limits.get("max_age_seconds", 300),
        max_timestamp_future_seconds=timestamp_limits.get("max_future_seconds", 60),
        exclude_bots_from_counts=rules.exclude_bots_from_counts(),
    )


# --- Component Entry Points ---


def run_ingest(
    inp: IngestEventInput,
    *,
    event_store: EventStorePort,
    rate_limiter: RateLimiterPort | None = None,
    time_port: TimePort | None = None,
    rules: RulesPort | None = None,
) -> IngestOutput:
    """
    Ingest an analytics event (TA-0034, TA-0035).

    Validates event, rejects PII, and stores if valid.

    Args:
        inp: Input containing event data and optional client key.
        event_store: Event store port.
        rate_limiter: Optional rate limiter port.
        time_port: Optional time port.
        rules: Optional rules port for configuration.

    Returns:
        IngestOutput with event or rejection errors.
    """
    config = _build_config(rules)

    service = AnalyticsIngestionService(
        event_store=event_store,
        rate_limiter=rate_limiter,
        time_port=time_port,
        config=config,
    )

    legacy_event, legacy_errors = service.ingest(
        data=inp.data,
        client_key=inp.client_key,
    )

    event = _convert_event(legacy_event)
    errors = _convert_errors(legacy_errors)

    return IngestOutput(
        event=event,
        accepted=event is not None,
        errors=errors,
        success=len(errors) == 0,
    )


def run_query_totals(
    inp: QueryTotalsInput,
    *,
    repo: AnalyticsRepoPort,
    rules: RulesPort | None = None,
) -> TotalsOutput:
    """
    Query aggregated totals.

    Args:
        inp: Input containing query filters.
        repo: Analytics repository port.
        rules: Optional rules port for configuration.

    Returns:
        TotalsOutput with aggregated counts.
    """
    result = repo.get_totals(
        event_type=inp.event_type,
        content_id=inp.content_id,
        start_time=inp.start_time,
        end_time=inp.end_time,
    )

    return TotalsOutput(
        count_total=result.get("count_total", 0),
        count_real=result.get("count_real", 0),
        count_bot=result.get("count_bot", 0),
        errors=[],
        success=True,
    )


def run_query_timeseries(
    inp: QueryTimeseriesInput,
    *,
    repo: AnalyticsRepoPort,
    rules: RulesPort | None = None,
) -> TimeseriesOutput:
    """
    Query time-bucketed data.

    Args:
        inp: Input containing query filters and bucket type.
        repo: Analytics repository port.
        rules: Optional rules port for configuration.

    Returns:
        TimeseriesOutput with data points.
    """
    results = repo.get_timeseries(
        bucket_type=inp.bucket_type,
        event_type=inp.event_type,
        content_id=inp.content_id,
        start_time=inp.start_time,
        end_time=inp.end_time,
        limit=inp.limit,
    )

    data_points = tuple(
        TimeseriesDataPoint(
            bucket_start=r["bucket_start"],
            count_total=r.get("count_total", 0),
            count_real=r.get("count_real", 0),
            count_bot=r.get("count_bot", 0),
        )
        for r in results
    )

    return TimeseriesOutput(
        data_points=data_points,
        errors=[],
        success=True,
    )


def run_query_top_content(
    inp: QueryTopContentInput,
    *,
    repo: AnalyticsRepoPort,
    rules: RulesPort | None = None,
) -> TopContentOutput:
    """
    Query top content by views.

    Args:
        inp: Input containing query filters.
        repo: Analytics repository port.
        rules: Optional rules port for configuration.

    Returns:
        TopContentOutput with ranked content list.
    """
    results = repo.get_top_content(
        event_type=inp.event_type,
        start_time=inp.start_time,
        end_time=inp.end_time,
        limit=inp.limit,
    )

    items = tuple(
        TopContentItem(
            content_id=r["content_id"],
            count_total=r.get("count_total", 0),
            count_real=r.get("count_real", 0),
        )
        for r in results
    )

    return TopContentOutput(
        items=items,
        errors=[],
        success=True,
    )


def run(
    inp: (IngestEventInput | QueryTotalsInput | QueryTimeseriesInput | QueryTopContentInput),
    *,
    event_store: EventStorePort | None = None,
    repo: AnalyticsRepoPort | None = None,
    rate_limiter: RateLimiterPort | None = None,
    time_port: TimePort | None = None,
    rules: RulesPort | None = None,
) -> IngestOutput | TotalsOutput | TimeseriesOutput | TopContentOutput:
    """
    Main entry point for the analytics component.

    Dispatches to appropriate handler based on input type.

    Args:
        inp: Input object determining the operation.
        event_store: Optional event store port (required for ingest).
        repo: Optional analytics repository port (required for queries).
        rate_limiter: Optional rate limiter port.
        time_port: Optional time port.
        rules: Optional rules port for configuration.

    Returns:
        Appropriate output object based on input type.
    """
    if isinstance(inp, IngestEventInput):
        if event_store is None:
            raise ValueError("EventStorePort is required for ingest operations")
        return run_ingest(
            inp,
            event_store=event_store,
            rate_limiter=rate_limiter,
            time_port=time_port,
            rules=rules,
        )
    elif isinstance(inp, QueryTotalsInput):
        if repo is None:
            raise ValueError("AnalyticsRepoPort is required for query operations")
        return run_query_totals(inp, repo=repo, rules=rules)
    elif isinstance(inp, QueryTimeseriesInput):
        if repo is None:
            raise ValueError("AnalyticsRepoPort is required for query operations")
        return run_query_timeseries(inp, repo=repo, rules=rules)
    elif isinstance(inp, QueryTopContentInput):
        if repo is None:
            raise ValueError("AnalyticsRepoPort is required for query operations")
        return run_query_top_content(inp, repo=repo, rules=rules)
    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
