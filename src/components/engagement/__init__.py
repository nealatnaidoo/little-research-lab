"""
Engagement component - Session tracking and aggregation.

Spec refs: E14.1, E14.2, E14.3, E14.4
"""

from .component import (
    bucket_scroll_depth,
    bucket_time_on_page,
    is_engaged_session,
    run,
    run_calculate,
    run_query_distribution,
    run_query_top_engaged_content,
    run_query_totals,
    validate_engagement_input,
)
from .models import (
    BucketCount,
    CalculateEngagementInput,
    CalculateEngagementOutput,
    EngagementDistributionOutput,
    EngagementSession,
    EngagementTotalsOutput,
    EngagementValidationError,
    QueryEngagementDistributionInput,
    QueryEngagementTotalsInput,
    QueryTopEngagedContentInput,
    ScrollBucket,
    TimeBucket,
    TopEngagedContentItem,
    TopEngagedContentOutput,
)
from .ports import (
    EngagementRepoPort,
    EngagementRulesPort,
    TimePort,
)

__all__ = [
    # Component functions
    "run",
    "run_calculate",
    "run_query_totals",
    "run_query_distribution",
    "run_query_top_engaged_content",
    # Pure functions
    "bucket_time_on_page",
    "bucket_scroll_depth",
    "is_engaged_session",
    "validate_engagement_input",
    # Models
    "CalculateEngagementInput",
    "CalculateEngagementOutput",
    "QueryEngagementTotalsInput",
    "QueryEngagementDistributionInput",
    "QueryTopEngagedContentInput",
    "EngagementTotalsOutput",
    "EngagementDistributionOutput",
    "TopEngagedContentOutput",
    "EngagementSession",
    "EngagementValidationError",
    "BucketCount",
    "TopEngagedContentItem",
    "TimeBucket",
    "ScrollBucket",
    # Ports
    "EngagementRepoPort",
    "EngagementRulesPort",
    "TimePort",
]
