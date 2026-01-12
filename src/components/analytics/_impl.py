"""
AnalyticsIngestionService (E6.1) - Event ingestion with validation.

Handles event ingestion, validation, and rate limiting.

Spec refs: E6.1, TA-0034, TA-0035, R4
Test assertions:
- TA-0034: Event validation (allowed types, fields)
- TA-0035: PII prevention (forbidden fields blocked)

Key behaviors:
- Only allowed event types accepted
- Only allowed fields accepted
- Forbidden fields (PII) rejected
- Rate limiting per window
- Timestamp validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Protocol
from uuid import UUID

# --- Enums ---


class EventType(str, Enum):
    """Allowed event types."""

    PAGE_VIEW = "page_view"
    OUTBOUND_CLICK = "outbound_click"
    ASSET_DOWNLOAD = "asset_download"


class UAClass(str, Enum):
    """User agent classification."""

    BOT = "bot"
    REAL = "real"
    UNKNOWN = "unknown"


# --- Configuration ---


@dataclass(frozen=True)
class IngestionConfig:
    """Analytics ingestion configuration."""

    enabled: bool = True

    # Rate limiting
    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 600

    # Allowed fields
    allowed_event_types: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "page_view",
                "outbound_click",
                "asset_download",
            }
        ),
    )
    allowed_fields: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "event_type",
                "ts",
                "path",
                "content_id",
                "link_id",
                "asset_id",
                "asset_version_id",
                "referrer",
                "utm_source",
                "utm_medium",
                "utm_campaign",
                "utm_content",
                "utm_term",
                "ua_class",
            }
        ),
    )
    forbidden_fields: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "ip",
                "ip_address",
                "user_agent",
                "ua_raw",
                "cookie",
                "cookie_id",
                "visitor_id",
                "email",
            }
        ),
    )

    # Bot handling
    treat_unknown_ua_as: str = "real"
    exclude_bots_from_counts: bool = True

    # Timestamp validation
    max_timestamp_age_seconds: int = 300  # 5 minutes
    max_timestamp_future_seconds: int = 60  # 1 minute


DEFAULT_CONFIG = IngestionConfig()


# --- Validation Errors ---


@dataclass
class IngestionError:
    """Analytics ingestion error."""

    code: str
    message: str
    field_name: str | None = None


# --- Event Model ---


@dataclass
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
    ua_class: UAClass = UAClass.UNKNOWN


# --- Rate Limiter Protocol ---


class RateLimiterPort(Protocol):
    """Rate limiter interface."""

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if rate limit allows request. Returns True if allowed."""
        ...

    def record_request(self, key: str, window_seconds: int) -> None:
        """Record a request for rate limiting."""
        ...


# --- Event Store Protocol ---


class EventStorePort(Protocol):
    """Event store interface."""

    def store(self, event: AnalyticsEvent) -> None:
        """Store an analytics event."""
        ...


# --- Time Port Protocol ---


class TimePort(Protocol):
    """Time provider interface."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...


# --- Default Implementations ---


class InMemoryRateLimiter:
    """In-memory rate limiter for testing/dev."""

    def __init__(self) -> None:
        self._requests: dict[str, list[datetime]] = {}

    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> bool:
        """Check if rate limit allows request."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=window_seconds)

        if key not in self._requests:
            return True

        # Clean old entries and count recent
        recent = [t for t in self._requests[key] if t > cutoff]
        self._requests[key] = recent

        return len(recent) < max_requests

    def record_request(self, key: str, window_seconds: int) -> None:
        """Record a request."""
        now = datetime.now(UTC)
        if key not in self._requests:
            self._requests[key] = []
        self._requests[key].append(now)


class InMemoryEventStore:
    """In-memory event store for testing/dev."""

    def __init__(self) -> None:
        self._events: list[AnalyticsEvent] = []

    def store(self, event: AnalyticsEvent) -> None:
        """Store an event."""
        self._events.append(event)

    def get_all(self) -> list[AnalyticsEvent]:
        """Get all stored events (for testing)."""
        return list(self._events)


class DefaultTimePort:
    """Default time provider."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        return datetime.now(UTC)


# --- Validation Functions ---


def validate_event_type(
    event_type: str | None,
    config: IngestionConfig = DEFAULT_CONFIG,
) -> list[IngestionError]:
    """Validate event type (TA-0034)."""
    errors: list[IngestionError] = []

    if not event_type:
        errors.append(
            IngestionError(
                code="event_type_required",
                message="Event type is required",
                field_name="event_type",
            )
        )
        return errors

    if event_type not in config.allowed_event_types:
        errors.append(
            IngestionError(
                code="invalid_event_type",
                message=f"Event type '{event_type}' is not allowed",
                field_name="event_type",
            )
        )

    return errors


def validate_forbidden_fields(
    data: dict[str, Any],
    config: IngestionConfig = DEFAULT_CONFIG,
) -> list[IngestionError]:
    """Validate no forbidden fields present (TA-0035)."""
    errors: list[IngestionError] = []

    for field_name in config.forbidden_fields:
        if field_name in data:
            errors.append(
                IngestionError(
                    code="forbidden_field",
                    message=f"Field '{field_name}' is not allowed (PII)",
                    field_name=field_name,
                )
            )

    return errors


def validate_allowed_fields(
    data: dict[str, Any],
    config: IngestionConfig = DEFAULT_CONFIG,
) -> list[IngestionError]:
    """Validate only allowed fields are present."""
    errors: list[IngestionError] = []

    for field_name in data:
        if field_name not in config.allowed_fields:
            # Skip if it's a forbidden field (handled separately)
            if field_name not in config.forbidden_fields:
                errors.append(
                    IngestionError(
                        code="unknown_field",
                        message=f"Field '{field_name}' is not recognized",
                        field_name=field_name,
                    )
                )

    return errors


def validate_timestamp(
    ts: Any,
    now: datetime,
    config: IngestionConfig = DEFAULT_CONFIG,
) -> tuple[datetime | None, list[IngestionError]]:
    """Validate and parse timestamp."""
    errors: list[IngestionError] = []

    if ts is None:
        # Use current time if not provided
        return now, []

    # Parse timestamp
    parsed: datetime | None = None

    if isinstance(ts, datetime):
        parsed = ts
    elif isinstance(ts, str):
        try:
            # Try ISO format
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            errors.append(
                IngestionError(
                    code="invalid_timestamp",
                    message="Timestamp must be ISO 8601 format",
                    field_name="ts",
                )
            )
            return None, errors
    elif isinstance(ts, (int, float)):
        try:
            # Unix timestamp (seconds or milliseconds)
            if ts > 1e12:  # Likely milliseconds
                parsed = datetime.fromtimestamp(ts / 1000, tz=UTC)
            else:
                parsed = datetime.fromtimestamp(ts, tz=UTC)
        except (ValueError, OSError):
            errors.append(
                IngestionError(
                    code="invalid_timestamp",
                    message="Invalid Unix timestamp",
                    field_name="ts",
                )
            )
            return None, errors
    else:
        errors.append(
            IngestionError(
                code="invalid_timestamp",
                message="Timestamp must be ISO string or Unix timestamp",
                field_name="ts",
            )
        )
        return None, errors

    # Ensure timezone aware
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    # Validate age
    age = (now - parsed).total_seconds()
    if age > config.max_timestamp_age_seconds:
        errors.append(
            IngestionError(
                code="timestamp_too_old",
                message=f"Timestamp is too old (max {config.max_timestamp_age_seconds}s)",
                field_name="ts",
            )
        )
    elif age < -config.max_timestamp_future_seconds:
        max_future = config.max_timestamp_future_seconds
        errors.append(
            IngestionError(
                code="timestamp_in_future",
                message=f"Timestamp is too far in future (max {max_future}s)",
                field_name="ts",
            )
        )

    return parsed, errors


def validate_ua_class(
    ua_class: str | None,
    config: IngestionConfig = DEFAULT_CONFIG,
) -> tuple[UAClass, list[IngestionError]]:
    """Validate user agent class."""
    errors: list[IngestionError] = []

    if ua_class is None:
        return UAClass.UNKNOWN, []

    try:
        return UAClass(ua_class), []
    except ValueError:
        errors.append(
            IngestionError(
                code="invalid_ua_class",
                message=f"UA class must be one of: {', '.join(c.value for c in UAClass)}",
                field_name="ua_class",
            )
        )
        return UAClass.UNKNOWN, errors


def parse_uuid(value: Any, field_name: str) -> tuple[UUID | None, list[IngestionError]]:
    """Parse and validate UUID field."""
    errors: list[IngestionError] = []

    if value is None:
        return None, []

    if isinstance(value, UUID):
        return value, []

    if isinstance(value, str):
        try:
            return UUID(value), []
        except ValueError:
            errors.append(
                IngestionError(
                    code="invalid_uuid",
                    message=f"Field '{field_name}' must be a valid UUID",
                    field_name=field_name,
                )
            )

    return None, errors


# --- Analytics Ingestion Service ---


class AnalyticsIngestionService:
    """
    Analytics ingestion service (E6.1).

    Handles event validation and ingestion with rate limiting.
    """

    def __init__(
        self,
        event_store: EventStorePort,
        rate_limiter: RateLimiterPort | None = None,
        time_port: TimePort | None = None,
        config: IngestionConfig | None = None,
    ) -> None:
        """Initialize service."""
        self._event_store = event_store
        self._rate_limiter = rate_limiter or InMemoryRateLimiter()
        self._time = time_port or DefaultTimePort()
        self._config = config or DEFAULT_CONFIG

    def check_rate_limit(self, client_key: str) -> bool:
        """Check if client is within rate limit."""
        return self._rate_limiter.check_rate_limit(
            key=client_key,
            max_requests=self._config.rate_limit_max_requests,
            window_seconds=self._config.rate_limit_window_seconds,
        )

    def ingest(
        self,
        data: dict[str, Any],
        client_key: str | None = None,
    ) -> tuple[AnalyticsEvent | None, list[IngestionError]]:
        """
        Ingest an analytics event.

        Validates:
        - Event type (TA-0034)
        - No forbidden fields (TA-0035)
        - Only allowed fields
        - Timestamp validity
        - Rate limits

        Returns:
            Tuple of (event, errors). Event is None if validation fails.
        """
        errors: list[IngestionError] = []
        now = self._time.now_utc()

        # Check rate limit
        if client_key:
            if not self.check_rate_limit(client_key):
                errors.append(
                    IngestionError(
                        code="rate_limit_exceeded",
                        message="Too many requests",
                    )
                )
                return None, errors
            self._rate_limiter.record_request(
                client_key,
                self._config.rate_limit_window_seconds,
            )

        # Validate forbidden fields first (TA-0035)
        errors.extend(validate_forbidden_fields(data, self._config))

        # If PII present, reject immediately
        if errors:
            return None, errors

        # Validate event type (TA-0034)
        errors.extend(validate_event_type(data.get("event_type"), self._config))

        # Validate allowed fields
        errors.extend(validate_allowed_fields(data, self._config))

        # Validate timestamp
        ts, ts_errors = validate_timestamp(data.get("ts"), now, self._config)
        errors.extend(ts_errors)

        # Validate UA class
        ua_class, ua_errors = validate_ua_class(data.get("ua_class"), self._config)
        errors.extend(ua_errors)

        # Validate UUIDs
        content_id, uuid_errors = parse_uuid(data.get("content_id"), "content_id")
        errors.extend(uuid_errors)

        asset_id, uuid_errors = parse_uuid(data.get("asset_id"), "asset_id")
        errors.extend(uuid_errors)

        asset_version_id, uuid_errors = parse_uuid(
            data.get("asset_version_id"),
            "asset_version_id",
        )
        errors.extend(uuid_errors)

        if errors:
            return None, errors

        # Build event
        event = AnalyticsEvent(
            event_type=EventType(data["event_type"]),
            timestamp=ts or now,
            path=data.get("path"),
            content_id=content_id,
            link_id=data.get("link_id"),
            asset_id=asset_id,
            asset_version_id=asset_version_id,
            referrer=data.get("referrer"),
            utm_source=data.get("utm_source"),
            utm_medium=data.get("utm_medium"),
            utm_campaign=data.get("utm_campaign"),
            utm_content=data.get("utm_content"),
            utm_term=data.get("utm_term"),
            ua_class=ua_class,
        )

        # Store event
        self._event_store.store(event)

        return event, []

    def should_count_event(self, event: AnalyticsEvent) -> bool:
        """Check if event should be counted (exclude bots if configured)."""
        if not self._config.exclude_bots_from_counts:
            return True

        if event.ua_class == UAClass.BOT:
            return False

        if event.ua_class == UAClass.UNKNOWN:
            treat_as = self._config.treat_unknown_ua_as
            return treat_as != "bot"

        return True


# --- Factory ---


def create_analytics_ingestion_service(
    event_store: EventStorePort,
    rate_limiter: RateLimiterPort | None = None,
    time_port: TimePort | None = None,
    config: IngestionConfig | None = None,
) -> AnalyticsIngestionService:
    """Create an AnalyticsIngestionService."""
    return AnalyticsIngestionService(
        event_store=event_store,
        rate_limiter=rate_limiter,
        time_port=time_port,
        config=config,
    )
