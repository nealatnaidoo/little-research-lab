"""
Analytics component - Event ingestion and aggregation.

Spec refs: E6.1
"""

# Re-exports from _impl for backwards compatibility
# Aggregate (E6.4, TA-0041)
from src.core.services.analytics_aggregate import (
    AggregateConfig,
    AggregateInput,
    AggregateService,
    BucketType,
    InMemoryAggregateRepo,
    calculate_bucket_end,
    calculate_bucket_start,
    create_aggregate_service,
)

# Re-exports from legacy services (pending full migration)
# Attribution (E6.2, TA-0036, TA-0037)
from src.core.services.analytics_attrib import (
    AttributionConfig,
    AttributionService,
    ReferrerInfo,
    SearchEngine,
    SocialNetwork,
    TrafficSource,
    UTMParams,
    classify_traffic_source,
    create_attribution_service,
    get_channel_name,
    parse_domain,
    parse_referrer,
    parse_utm_params,
)

# Dedupe (E6.3, TA-0039, TA-0040)
from src.core.services.analytics_dedupe import (
    DedupeConfig,
    DedupeResult,
    DedupeService,
    InMemoryDedupeStore,
    UAClass,
    classify_user_agent,
    create_dedupe_service,
    generate_dedupe_key,
    get_timestamp_bucket,
    is_bot,
    should_count,
)

from ._impl import (
    AnalyticsIngestionService,
    DefaultTimePort,
    EventType,
    IngestionConfig,
    IngestionError,
    InMemoryEventStore,
    InMemoryRateLimiter,
    create_analytics_ingestion_service,
    parse_uuid,
    validate_allowed_fields,
    validate_event_type,
    validate_forbidden_fields,
    validate_timestamp,
    validate_ua_class,
)

# Note: Ingest functions now re-exported from _impl (above) for consistency
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
    # Legacy attribution re-exports (pending migration)
    "AttributionConfig",
    "AttributionService",
    "ReferrerInfo",
    "SearchEngine",
    "SocialNetwork",
    "TrafficSource",
    "UTMParams",
    "classify_traffic_source",
    "create_attribution_service",
    "get_channel_name",
    "parse_domain",
    "parse_referrer",
    "parse_utm_params",
    # Legacy aggregate re-exports
    "AggregateConfig",
    "AggregateInput",
    "AggregateService",
    "BucketType",
    "InMemoryAggregateRepo",
    "calculate_bucket_end",
    "calculate_bucket_start",
    "create_aggregate_service",
    # Legacy dedupe re-exports
    "DedupeConfig",
    "DedupeResult",
    "DedupeService",
    "InMemoryDedupeStore",
    "classify_user_agent",
    "create_dedupe_service",
    "generate_dedupe_key",
    "get_timestamp_bucket",
    "is_bot",
    "should_count",
    # Ingest re-exports (from _impl)
    "DefaultTimePort",
    "IngestionError",
    "create_analytics_ingestion_service",
    "parse_uuid",
    "validate_allowed_fields",
    "validate_event_type",
    "validate_forbidden_fields",
    "validate_timestamp",
    "validate_ua_class",
]
