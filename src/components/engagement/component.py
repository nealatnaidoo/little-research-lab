"""
Engagement component - Session tracking and aggregation.

Spec refs: E14.1, E14.2, E14.3, E14.4
Test assertions: TA-0058, TA-0059, TA-0060, TA-0065, TA-0066

Calculates, buckets, and stores engagement metrics with privacy enforcement.

Invariants:
- I9: No precise durations or scroll depths stored (bucketed only)
- R9: Engagement data bucketed before persistence
- HV2: Forbidden fields rejected (IP, email, visitor_id)
"""

from __future__ import annotations

from datetime import datetime, timezone

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


# --- Default Configuration ---

DEFAULT_TIME_BUCKETS: tuple[str, ...] = (
    "0-10s",
    "10-30s",
    "30-60s",
    "60-120s",
    "120-300s",
    "300+s",
)

DEFAULT_SCROLL_BUCKETS: tuple[str, ...] = (
    "0-25%",
    "25-50%",
    "50-75%",
    "75-100%",
)

DEFAULT_MIN_TIME_SECONDS = 30
DEFAULT_MIN_SCROLL_PERCENT = 25


# --- Pure Functions (Functional Core) ---


def bucket_time_on_page(seconds: float, buckets: tuple[str, ...] | None = None) -> TimeBucket:
    """
    Bucket time on page value (TA-0060).

    Converts precise time to privacy-safe bucket.

    Args:
        seconds: Time on page in seconds (0-3600 typical range)
        buckets: Optional custom bucket definitions

    Returns:
        Time bucket label
    """
    if buckets is None:
        buckets = DEFAULT_TIME_BUCKETS

    # Map seconds to bucket based on default ranges
    if seconds < 10:
        return "0-10s"
    elif seconds < 30:
        return "10-30s"
    elif seconds < 60:
        return "30-60s"
    elif seconds < 120:
        return "60-120s"
    elif seconds < 300:
        return "120-300s"
    else:
        return "300+s"


def bucket_scroll_depth(percent: float, buckets: tuple[str, ...] | None = None) -> ScrollBucket:
    """
    Bucket scroll depth value (TA-0060).

    Converts precise percentage to privacy-safe bucket.

    Args:
        percent: Scroll depth as percentage (0-100)
        buckets: Optional custom bucket definitions

    Returns:
        Scroll bucket label
    """
    if buckets is None:
        buckets = DEFAULT_SCROLL_BUCKETS

    # Clamp to valid range
    percent = max(0.0, min(100.0, percent))

    # Map percentage to bucket
    if percent < 25:
        return "0-25%"
    elif percent < 50:
        return "25-50%"
    elif percent < 75:
        return "50-75%"
    else:
        return "75-100%"


def is_engaged_session(
    time_on_page_seconds: float,
    scroll_depth_percent: float,
    min_time_seconds: int = DEFAULT_MIN_TIME_SECONDS,
    min_scroll_percent: int = DEFAULT_MIN_SCROLL_PERCENT,
) -> bool:
    """
    Determine if session meets engagement threshold (TA-0058).

    A session is "engaged" if it meets BOTH criteria:
    - Time on page >= threshold (default 30s)
    - Scroll depth >= threshold (default 25%)

    Args:
        time_on_page_seconds: Time spent on page
        scroll_depth_percent: Maximum scroll depth reached (0-100)
        min_time_seconds: Minimum time threshold
        min_scroll_percent: Minimum scroll threshold

    Returns:
        True if session is engaged
    """
    return (
        time_on_page_seconds >= min_time_seconds
        and scroll_depth_percent >= min_scroll_percent
    )


def validate_engagement_input(
    time_on_page_seconds: float,
    scroll_depth_percent: float,
) -> list[EngagementValidationError]:
    """
    Validate engagement input values (TA-0059).

    Args:
        time_on_page_seconds: Time on page
        scroll_depth_percent: Scroll depth

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[EngagementValidationError] = []

    # Validate time on page
    if time_on_page_seconds < 0:
        errors.append(
            EngagementValidationError(
                code="INVALID_TIME",
                message="Time on page cannot be negative",
                field_name="time_on_page_seconds",
            )
        )
    elif time_on_page_seconds > 3600:
        errors.append(
            EngagementValidationError(
                code="INVALID_TIME",
                message="Time on page exceeds maximum (3600s)",
                field_name="time_on_page_seconds",
            )
        )

    # Validate scroll depth
    if scroll_depth_percent < 0:
        errors.append(
            EngagementValidationError(
                code="INVALID_SCROLL",
                message="Scroll depth cannot be negative",
                field_name="scroll_depth_percent",
            )
        )
    elif scroll_depth_percent > 100:
        errors.append(
            EngagementValidationError(
                code="INVALID_SCROLL",
                message="Scroll depth cannot exceed 100%",
                field_name="scroll_depth_percent",
            )
        )

    return errors


# --- Component Entry Points ---


def run_calculate(
    inp: CalculateEngagementInput,
    *,
    repo: EngagementRepoPort | None = None,
    rules: EngagementRulesPort | None = None,
    time_port: TimePort | None = None,
) -> CalculateEngagementOutput:
    """
    Calculate engagement metrics and optionally store session (TA-0058, TA-0059, TA-0060).

    Buckets raw values before storage to ensure privacy compliance.

    Args:
        inp: Input containing content_id and raw metrics
        repo: Optional repo port (if provided, session is stored)
        rules: Optional rules port for thresholds
        time_port: Optional time port

    Returns:
        CalculateEngagementOutput with bucketed values and engagement status
    """
    # Validate input
    errors = validate_engagement_input(
        inp.time_on_page_seconds,
        inp.scroll_depth_percent,
    )

    if errors:
        return CalculateEngagementOutput(
            session=None,
            is_engaged=False,
            time_bucket="0-10s",
            scroll_bucket="0-25%",
            errors=errors,
            success=False,
        )

    # Get thresholds from rules or use defaults
    min_time = DEFAULT_MIN_TIME_SECONDS
    min_scroll = DEFAULT_MIN_SCROLL_PERCENT
    time_buckets = DEFAULT_TIME_BUCKETS
    scroll_buckets = DEFAULT_SCROLL_BUCKETS

    if rules is not None:
        min_time = rules.get_min_time_on_page_seconds()
        min_scroll = rules.get_min_scroll_depth_percent()
        time_buckets = rules.get_time_buckets()
        scroll_buckets = rules.get_scroll_buckets()

    # Bucket the values (privacy enforcement - TA-0060)
    time_bucket = bucket_time_on_page(inp.time_on_page_seconds, time_buckets)
    scroll_bucket = bucket_scroll_depth(inp.scroll_depth_percent, scroll_buckets)

    # Check if engaged
    engaged = is_engaged_session(
        inp.time_on_page_seconds,
        inp.scroll_depth_percent,
        min_time,
        min_scroll,
    )

    # Get timestamp and truncate to day
    timestamp = inp.timestamp
    if timestamp is None:
        if time_port is not None:
            timestamp = time_port.now_utc()
        else:
            timestamp = datetime.now(timezone.utc)

    # Truncate to day for privacy
    if time_port is not None:
        date = time_port.truncate_to_day(timestamp)
    else:
        date = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)

    # Create session
    session = EngagementSession(
        content_id=inp.content_id,
        date=date,
        time_bucket=time_bucket,
        scroll_bucket=scroll_bucket,
        is_engaged=engaged,
    )

    # Store if repo provided
    if repo is not None:
        repo.store_session(
            content_id=session.content_id,
            date=session.date,
            time_bucket=session.time_bucket,
            scroll_bucket=session.scroll_bucket,
            is_engaged=session.is_engaged,
        )

    return CalculateEngagementOutput(
        session=session,
        is_engaged=engaged,
        time_bucket=time_bucket,
        scroll_bucket=scroll_bucket,
        errors=[],
        success=True,
    )


def run_query_totals(
    inp: QueryEngagementTotalsInput,
    *,
    repo: EngagementRepoPort,
    rules: EngagementRulesPort | None = None,
) -> EngagementTotalsOutput:
    """
    Query engagement totals (TA-0065).

    Args:
        inp: Input containing query filters
        repo: Engagement repository port

    Returns:
        EngagementTotalsOutput with totals and engagement rate
    """
    result = repo.get_totals(
        content_id=inp.content_id,
        start_date=inp.start_date,
        end_date=inp.end_date,
        engaged_only=inp.engaged_only,
    )

    total = result.get("total_sessions", 0)
    engaged = result.get("engaged_sessions", 0)

    # Calculate engagement rate (avoid division by zero)
    rate = engaged / total if total > 0 else 0.0

    return EngagementTotalsOutput(
        total_sessions=total,
        engaged_sessions=engaged,
        engagement_rate=rate,
        errors=[],
        success=True,
    )


def run_query_distribution(
    inp: QueryEngagementDistributionInput,
    *,
    repo: EngagementRepoPort,
    rules: EngagementRulesPort | None = None,
) -> EngagementDistributionOutput:
    """
    Query engagement distribution by bucket (TA-0066).

    Args:
        inp: Input containing query filters and distribution type
        repo: Engagement repository port

    Returns:
        EngagementDistributionOutput with bucket counts
    """
    results = repo.get_distribution(
        distribution_type=inp.distribution_type,
        content_id=inp.content_id,
        start_date=inp.start_date,
        end_date=inp.end_date,
    )

    # Calculate total for percentages
    total = sum(r.get("count", 0) for r in results)

    # Build bucket counts
    buckets = tuple(
        BucketCount(
            bucket=r["bucket"],
            count=r.get("count", 0),
            percentage=r.get("count", 0) / total if total > 0 else 0.0,
        )
        for r in results
    )

    return EngagementDistributionOutput(
        distribution_type=inp.distribution_type,
        buckets=buckets,
        total_sessions=total,
        errors=[],
        success=True,
    )


def run_query_top_engaged_content(
    inp: QueryTopEngagedContentInput,
    *,
    repo: EngagementRepoPort,
    rules: EngagementRulesPort | None = None,
) -> TopEngagedContentOutput:
    """
    Query top content by engagement (TA-0065, TA-0066).

    Args:
        inp: Input containing query filters
        repo: Engagement repository port

    Returns:
        TopEngagedContentOutput with ranked content list
    """
    results = repo.get_top_engaged_content(
        start_date=inp.start_date,
        end_date=inp.end_date,
        limit=inp.limit,
    )

    items = tuple(
        TopEngagedContentItem(
            content_id=r["content_id"],
            total_sessions=r.get("total_sessions", 0),
            engaged_sessions=r.get("engaged_sessions", 0),
            engagement_rate=(
                r.get("engaged_sessions", 0) / r.get("total_sessions", 1)
                if r.get("total_sessions", 0) > 0
                else 0.0
            ),
        )
        for r in results
    )

    return TopEngagedContentOutput(
        items=items,
        errors=[],
        success=True,
    )


def run(
    inp: (
        CalculateEngagementInput
        | QueryEngagementTotalsInput
        | QueryEngagementDistributionInput
        | QueryTopEngagedContentInput
    ),
    *,
    repo: EngagementRepoPort | None = None,
    rules: EngagementRulesPort | None = None,
    time_port: TimePort | None = None,
) -> (
    CalculateEngagementOutput
    | EngagementTotalsOutput
    | EngagementDistributionOutput
    | TopEngagedContentOutput
):
    """
    Main entry point for the engagement component.

    Dispatches to appropriate handler based on input type.

    Args:
        inp: Input object determining the operation
        repo: Optional engagement repository port
        rules: Optional rules port
        time_port: Optional time port

    Returns:
        Appropriate output object based on input type
    """
    if isinstance(inp, CalculateEngagementInput):
        return run_calculate(inp, repo=repo, rules=rules, time_port=time_port)
    elif isinstance(inp, QueryEngagementTotalsInput):
        if repo is None:
            raise ValueError("EngagementRepoPort is required for query operations")
        return run_query_totals(inp, repo=repo, rules=rules)
    elif isinstance(inp, QueryEngagementDistributionInput):
        if repo is None:
            raise ValueError("EngagementRepoPort is required for query operations")
        return run_query_distribution(inp, repo=repo, rules=rules)
    elif isinstance(inp, QueryTopEngagedContentInput):
        if repo is None:
            raise ValueError("EngagementRepoPort is required for query operations")
        return run_query_top_engaged_content(inp, repo=repo, rules=rules)
    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
