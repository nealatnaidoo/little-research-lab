"""
Analytics component - Event ingestion and aggregation.

Spec refs: E6.1
"""

# Re-exports from _impl for backwards compatibility
from ._impl import (
    AnalyticsIngestionService,
    IngestionConfig,
    InMemoryEventStore,
    InMemoryRateLimiter,
)
from .component import (
    run,
    run_ingest,
    run_query_timeseries,
    run_query_top_content,
    run_query_totals,
)
from .models import (
    AnalyticsEvent,
    AnalyticsValidationError,
    EventType,
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
    UAClass,
)
from .ports import (
    AnalyticsRepoPort,
    DedupePort,
    EventStorePort,
    RateLimiterPort,
    RulesPort,
    TimePort,
)

__all__ = [
    # Entry points
    "run",
    "run_ingest",
    "run_query_timeseries",
    "run_query_top_content",
    "run_query_totals",
    # Input models
    "IngestEventInput",
    "QueryTimeseriesInput",
    "QueryTopContentInput",
    "QueryTotalsInput",
    # Output models
    "AnalyticsEvent",
    "AnalyticsValidationError",
    "EventType",
    "IngestOutput",
    "TimeseriesDataPoint",
    "TimeseriesOutput",
    "TopContentItem",
    "TopContentOutput",
    "TotalsOutput",
    "UAClass",
    # Ports
    "AnalyticsRepoPort",
    "DedupePort",
    "EventStorePort",
    "RateLimiterPort",
    "RulesPort",
    "TimePort",
    # Legacy _impl re-exports
    "AnalyticsIngestionService",
    "IngestionConfig",
    "InMemoryEventStore",
    "InMemoryRateLimiter",
]
