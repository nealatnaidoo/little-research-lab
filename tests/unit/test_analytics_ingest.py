"""
Tests for AnalyticsIngestionService (E6.1).

Test assertions:
- TA-0034: Event validation (allowed types, fields)
- TA-0035: PII prevention (forbidden fields blocked)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.core.services.analytics_ingest import (
    AnalyticsEvent,
    AnalyticsIngestionService,
    EventType,
    IngestionConfig,
    InMemoryEventStore,
    InMemoryRateLimiter,
    UAClass,
    create_analytics_ingestion_service,
    parse_uuid,
    validate_allowed_fields,
    validate_event_type,
    validate_forbidden_fields,
    validate_timestamp,
    validate_ua_class,
)

# --- Mock Time Port ---


class MockTimePort:
    """Mock time provider."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime.now(UTC)

    def now_utc(self) -> datetime:
        return self._now

    def set_now(self, now: datetime) -> None:
        self._now = now


# --- Fixtures ---


@pytest.fixture
def event_store() -> InMemoryEventStore:
    """Fresh event store."""
    return InMemoryEventStore()


@pytest.fixture
def rate_limiter() -> InMemoryRateLimiter:
    """Fresh rate limiter."""
    return InMemoryRateLimiter()


@pytest.fixture
def time_port() -> MockTimePort:
    """Mock time provider."""
    return MockTimePort()


@pytest.fixture
def service(
    event_store: InMemoryEventStore,
    rate_limiter: InMemoryRateLimiter,
    time_port: MockTimePort,
) -> AnalyticsIngestionService:
    """Analytics ingestion service with mock dependencies."""
    return AnalyticsIngestionService(
        event_store=event_store,
        rate_limiter=rate_limiter,
        time_port=time_port,
    )


# --- Event Type Validation Tests (TA-0034) ---


class TestValidateEventType:
    """Test TA-0034: Event type validation."""

    def test_page_view_allowed(self) -> None:
        """page_view is allowed."""
        errors = validate_event_type("page_view")
        assert len(errors) == 0

    def test_outbound_click_allowed(self) -> None:
        """outbound_click is allowed."""
        errors = validate_event_type("outbound_click")
        assert len(errors) == 0

    def test_asset_download_allowed(self) -> None:
        """asset_download is allowed."""
        errors = validate_event_type("asset_download")
        assert len(errors) == 0

    def test_empty_type_rejected(self) -> None:
        """Empty event type is rejected."""
        errors = validate_event_type("")
        assert len(errors) == 1
        assert errors[0].code == "event_type_required"

    def test_none_type_rejected(self) -> None:
        """None event type is rejected."""
        errors = validate_event_type(None)
        assert len(errors) == 1
        assert errors[0].code == "event_type_required"

    def test_unknown_type_rejected(self) -> None:
        """Unknown event type is rejected."""
        errors = validate_event_type("custom_event")
        assert len(errors) == 1
        assert errors[0].code == "invalid_event_type"

    def test_custom_allowed_types(self) -> None:
        """Custom allowed types config is respected."""
        config = IngestionConfig(allowed_event_types=frozenset({"custom"}))
        errors = validate_event_type("custom", config)
        assert len(errors) == 0


# --- Forbidden Fields Validation Tests (TA-0035) ---


class TestValidateForbiddenFields:
    """Test TA-0035: PII prevention."""

    def test_clean_data_passes(self) -> None:
        """Data without PII passes."""
        data = {"event_type": "page_view", "path": "/test"}
        errors = validate_forbidden_fields(data)
        assert len(errors) == 0

    def test_ip_rejected(self) -> None:
        """TA-0035: IP address is rejected."""
        data = {"event_type": "page_view", "ip": "192.168.1.1"}
        errors = validate_forbidden_fields(data)
        assert len(errors) == 1
        assert errors[0].code == "forbidden_field"
        assert "ip" in errors[0].message.lower()

    def test_ip_address_rejected(self) -> None:
        """TA-0035: ip_address field is rejected."""
        data = {"event_type": "page_view", "ip_address": "10.0.0.1"}
        errors = validate_forbidden_fields(data)
        assert len(errors) == 1
        assert errors[0].code == "forbidden_field"

    def test_user_agent_rejected(self) -> None:
        """TA-0035: Full user agent is rejected."""
        data = {"event_type": "page_view", "user_agent": "Mozilla/5.0..."}
        errors = validate_forbidden_fields(data)
        assert len(errors) == 1
        assert errors[0].code == "forbidden_field"

    def test_cookie_rejected(self) -> None:
        """TA-0035: Cookie data is rejected."""
        data = {"event_type": "page_view", "cookie": "session=abc123"}
        errors = validate_forbidden_fields(data)
        assert len(errors) == 1
        assert errors[0].code == "forbidden_field"

    def test_cookie_id_rejected(self) -> None:
        """TA-0035: Cookie ID is rejected."""
        data = {"event_type": "page_view", "cookie_id": "abc123"}
        errors = validate_forbidden_fields(data)
        assert len(errors) == 1
        assert errors[0].code == "forbidden_field"

    def test_visitor_id_rejected(self) -> None:
        """TA-0035: Visitor ID is rejected."""
        data = {"event_type": "page_view", "visitor_id": "v123"}
        errors = validate_forbidden_fields(data)
        assert len(errors) == 1
        assert errors[0].code == "forbidden_field"

    def test_email_rejected(self) -> None:
        """TA-0035: Email is rejected."""
        data = {"event_type": "page_view", "email": "user@example.com"}
        errors = validate_forbidden_fields(data)
        assert len(errors) == 1
        assert errors[0].code == "forbidden_field"

    def test_multiple_pii_fields_all_reported(self) -> None:
        """All PII fields are reported."""
        data = {"event_type": "page_view", "ip": "1.2.3.4", "email": "a@b.com"}
        errors = validate_forbidden_fields(data)
        assert len(errors) == 2


# --- Allowed Fields Validation Tests ---


class TestValidateAllowedFields:
    """Test allowed fields validation."""

    def test_all_allowed_fields_pass(self) -> None:
        """All allowed fields are accepted."""
        data = {
            "event_type": "page_view",
            "ts": "2026-01-12T10:00:00Z",
            "path": "/test",
            "content_id": str(uuid4()),
            "referrer": "https://example.com",
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "test",
            "utm_content": "ad1",
            "utm_term": "keyword",
            "ua_class": "real",
        }
        errors = validate_allowed_fields(data)
        assert len(errors) == 0

    def test_unknown_field_reported(self) -> None:
        """Unknown fields are reported."""
        data = {"event_type": "page_view", "custom_field": "value"}
        errors = validate_allowed_fields(data)
        assert len(errors) == 1
        assert errors[0].code == "unknown_field"


# --- Timestamp Validation Tests ---


class TestValidateTimestamp:
    """Test timestamp validation."""

    def test_none_uses_current_time(self) -> None:
        """None timestamp uses current time."""
        now = datetime.now(UTC)
        ts, errors = validate_timestamp(None, now)
        assert len(errors) == 0
        assert ts == now

    def test_iso_format_parsed(self) -> None:
        """ISO 8601 format is parsed."""
        now = datetime.now(UTC)
        # Use a timestamp 30 seconds ago (within acceptable range)
        past_ts = (now - timedelta(seconds=30)).isoformat()
        ts, errors = validate_timestamp(past_ts, now)
        assert len(errors) == 0
        assert ts is not None

    def test_iso_format_with_z_parsed(self) -> None:
        """ISO format with Z suffix is parsed."""
        now = datetime.now(UTC)
        # Use a timestamp 30 seconds ago with Z suffix
        past_ts = (now - timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        ts, errors = validate_timestamp(past_ts, now)
        assert len(errors) == 0
        assert ts is not None

    def test_unix_timestamp_seconds_parsed(self) -> None:
        """Unix timestamp in seconds is parsed."""
        now = datetime(2026, 1, 12, 10, 0, 0, tzinfo=UTC)
        ts, errors = validate_timestamp(now.timestamp(), now)
        assert len(errors) == 0

    def test_unix_timestamp_milliseconds_parsed(self) -> None:
        """Unix timestamp in milliseconds is parsed."""
        now = datetime(2026, 1, 12, 10, 0, 0, tzinfo=UTC)
        ts, errors = validate_timestamp(now.timestamp() * 1000, now)
        assert len(errors) == 0

    def test_invalid_format_rejected(self) -> None:
        """Invalid format is rejected."""
        now = datetime.now(UTC)
        ts, errors = validate_timestamp("not-a-date", now)
        assert len(errors) == 1
        assert errors[0].code == "invalid_timestamp"

    def test_too_old_timestamp_rejected(self) -> None:
        """Timestamp too old is rejected."""
        now = datetime.now(UTC)
        old_ts = (now - timedelta(seconds=600)).isoformat()
        ts, errors = validate_timestamp(old_ts, now)
        assert len(errors) == 1
        assert errors[0].code == "timestamp_too_old"

    def test_future_timestamp_rejected(self) -> None:
        """Timestamp in future is rejected."""
        now = datetime.now(UTC)
        future_ts = (now + timedelta(seconds=120)).isoformat()
        ts, errors = validate_timestamp(future_ts, now)
        assert len(errors) == 1
        assert errors[0].code == "timestamp_in_future"


# --- UA Class Validation Tests ---


class TestValidateUAClass:
    """Test UA class validation."""

    def test_real_accepted(self) -> None:
        """'real' is accepted."""
        ua, errors = validate_ua_class("real")
        assert len(errors) == 0
        assert ua == UAClass.REAL

    def test_bot_accepted(self) -> None:
        """'bot' is accepted."""
        ua, errors = validate_ua_class("bot")
        assert len(errors) == 0
        assert ua == UAClass.BOT

    def test_unknown_accepted(self) -> None:
        """'unknown' is accepted."""
        ua, errors = validate_ua_class("unknown")
        assert len(errors) == 0
        assert ua == UAClass.UNKNOWN

    def test_none_defaults_to_unknown(self) -> None:
        """None defaults to unknown."""
        ua, errors = validate_ua_class(None)
        assert len(errors) == 0
        assert ua == UAClass.UNKNOWN

    def test_invalid_rejected(self) -> None:
        """Invalid UA class is rejected."""
        ua, errors = validate_ua_class("crawler")
        assert len(errors) == 1
        assert errors[0].code == "invalid_ua_class"


# --- UUID Parsing Tests ---


class TestParseUUID:
    """Test UUID parsing."""

    def test_valid_uuid_string(self) -> None:
        """Valid UUID string is parsed."""
        uuid_str = str(uuid4())
        result, errors = parse_uuid(uuid_str, "test_field")
        assert len(errors) == 0
        assert str(result) == uuid_str

    def test_uuid_object(self) -> None:
        """UUID object passes through."""
        uuid_obj = uuid4()
        result, errors = parse_uuid(uuid_obj, "test_field")
        assert len(errors) == 0
        assert result == uuid_obj

    def test_none_returns_none(self) -> None:
        """None returns None."""
        result, errors = parse_uuid(None, "test_field")
        assert len(errors) == 0
        assert result is None

    def test_invalid_uuid_rejected(self) -> None:
        """Invalid UUID string is rejected."""
        result, errors = parse_uuid("not-a-uuid", "test_field")
        assert len(errors) == 1
        assert errors[0].code == "invalid_uuid"


# --- Service Integration Tests ---


class TestAnalyticsIngestionService:
    """Test the full ingestion service."""

    def test_ingest_page_view(
        self,
        service: AnalyticsIngestionService,
        event_store: InMemoryEventStore,
    ) -> None:
        """Ingest a page view event."""
        data = {
            "event_type": "page_view",
            "path": "/blog/post-1",
            "referrer": "https://google.com",
        }

        event, errors = service.ingest(data)

        assert len(errors) == 0
        assert event is not None
        assert event.event_type == EventType.PAGE_VIEW
        assert event.path == "/blog/post-1"
        assert len(event_store.get_all()) == 1

    def test_ingest_with_utm_params(
        self,
        service: AnalyticsIngestionService,
    ) -> None:
        """Ingest event with UTM parameters."""
        data = {
            "event_type": "page_view",
            "path": "/landing",
            "utm_source": "newsletter",
            "utm_medium": "email",
            "utm_campaign": "launch",
        }

        event, errors = service.ingest(data)

        assert len(errors) == 0
        assert event is not None
        assert event.utm_source == "newsletter"
        assert event.utm_medium == "email"
        assert event.utm_campaign == "launch"

    def test_ingest_asset_download(
        self,
        service: AnalyticsIngestionService,
    ) -> None:
        """Ingest asset download event."""
        asset_id = uuid4()
        data = {
            "event_type": "asset_download",
            "asset_id": str(asset_id),
        }

        event, errors = service.ingest(data)

        assert len(errors) == 0
        assert event is not None
        assert event.event_type == EventType.ASSET_DOWNLOAD
        assert event.asset_id == asset_id

    def test_ingest_rejects_pii(
        self,
        service: AnalyticsIngestionService,
    ) -> None:
        """TA-0035: PII is rejected."""
        data = {
            "event_type": "page_view",
            "ip": "192.168.1.1",
        }

        event, errors = service.ingest(data)

        assert event is None
        assert len(errors) == 1
        assert errors[0].code == "forbidden_field"

    def test_ingest_rejects_invalid_event_type(
        self,
        service: AnalyticsIngestionService,
    ) -> None:
        """TA-0034: Invalid event type is rejected."""
        data = {"event_type": "invalid_type"}

        event, errors = service.ingest(data)

        assert event is None
        assert any(e.code == "invalid_event_type" for e in errors)

    def test_rate_limiting(
        self,
        event_store: InMemoryEventStore,
        time_port: MockTimePort,
    ) -> None:
        """Rate limiting is enforced."""
        config = IngestionConfig(rate_limit_max_requests=2)
        service = AnalyticsIngestionService(
            event_store=event_store,
            time_port=time_port,
            config=config,
        )

        # First two requests succeed
        for _ in range(2):
            event, errors = service.ingest(
                {"event_type": "page_view"},
                client_key="test-client",
            )
            assert event is not None

        # Third request is rate limited
        event, errors = service.ingest(
            {"event_type": "page_view"},
            client_key="test-client",
        )
        assert event is None
        assert errors[0].code == "rate_limit_exceeded"

    def test_no_rate_limit_without_client_key(
        self,
        event_store: InMemoryEventStore,
        time_port: MockTimePort,
    ) -> None:
        """No rate limiting without client key."""
        config = IngestionConfig(rate_limit_max_requests=1)
        service = AnalyticsIngestionService(
            event_store=event_store,
            time_port=time_port,
            config=config,
        )

        # Many requests without client key all succeed
        for _ in range(5):
            event, errors = service.ingest({"event_type": "page_view"})
            assert event is not None


class TestShouldCountEvent:
    """Test bot exclusion logic."""

    def test_real_ua_counted(
        self,
        service: AnalyticsIngestionService,
    ) -> None:
        """Real UA class is counted."""
        event = AnalyticsEvent(
            event_type=EventType.PAGE_VIEW,
            timestamp=datetime.now(UTC),
            ua_class=UAClass.REAL,
        )
        assert service.should_count_event(event) is True

    def test_bot_excluded(
        self,
        service: AnalyticsIngestionService,
    ) -> None:
        """Bot UA class is excluded."""
        event = AnalyticsEvent(
            event_type=EventType.PAGE_VIEW,
            timestamp=datetime.now(UTC),
            ua_class=UAClass.BOT,
        )
        assert service.should_count_event(event) is False

    def test_unknown_treated_as_real_by_default(
        self,
        service: AnalyticsIngestionService,
    ) -> None:
        """Unknown UA treated as real by default."""
        event = AnalyticsEvent(
            event_type=EventType.PAGE_VIEW,
            timestamp=datetime.now(UTC),
            ua_class=UAClass.UNKNOWN,
        )
        assert service.should_count_event(event) is True

    def test_unknown_can_be_excluded(
        self,
        event_store: InMemoryEventStore,
        time_port: MockTimePort,
    ) -> None:
        """Unknown UA can be excluded via config."""
        config = IngestionConfig(treat_unknown_ua_as="bot")
        service = AnalyticsIngestionService(
            event_store=event_store,
            time_port=time_port,
            config=config,
        )

        event = AnalyticsEvent(
            event_type=EventType.PAGE_VIEW,
            timestamp=datetime.now(UTC),
            ua_class=UAClass.UNKNOWN,
        )
        assert service.should_count_event(event) is False

    def test_bots_counted_when_exclusion_disabled(
        self,
        event_store: InMemoryEventStore,
        time_port: MockTimePort,
    ) -> None:
        """Bots counted when exclusion is disabled."""
        config = IngestionConfig(exclude_bots_from_counts=False)
        service = AnalyticsIngestionService(
            event_store=event_store,
            time_port=time_port,
            config=config,
        )

        event = AnalyticsEvent(
            event_type=EventType.PAGE_VIEW,
            timestamp=datetime.now(UTC),
            ua_class=UAClass.BOT,
        )
        assert service.should_count_event(event) is True


# --- Factory Tests ---


class TestFactory:
    """Test factory function."""

    def test_create_service(self, event_store: InMemoryEventStore) -> None:
        """Factory creates service."""
        service = create_analytics_ingestion_service(event_store)
        assert isinstance(service, AnalyticsIngestionService)

    def test_create_with_all_deps(
        self,
        event_store: InMemoryEventStore,
        rate_limiter: InMemoryRateLimiter,
        time_port: MockTimePort,
    ) -> None:
        """Factory accepts all dependencies."""
        config = IngestionConfig(rate_limit_max_requests=100)
        service = create_analytics_ingestion_service(
            event_store=event_store,
            rate_limiter=rate_limiter,
            time_port=time_port,
            config=config,
        )
        assert isinstance(service, AnalyticsIngestionService)


# --- R4: Privacy Schema Enforcement Tests (T-0047) ---


class TestPrivacySchemaEnforcement:
    """
    Test R4: Privacy schema from rules.yaml is enforced.

    rules.yaml specifies:
      analytics:
        privacy:
          store_raw_events: false
          store_ip: false
          store_full_user_agent: false
          store_cookies: false
          store_visitor_identifiers: false

    These tests verify that the analytics code respects these rules.
    """

    def test_privacy_rules_forbid_ip_storage(self) -> None:
        """R4: store_ip: false means IP addresses are rejected."""
        # This is enforced by validate_forbidden_fields
        data = {"event_type": "page_view", "ip": "192.168.1.1"}
        errors = validate_forbidden_fields(data)

        assert len(errors) > 0
        assert errors[0].code == "forbidden_field"
        assert "ip" in errors[0].message.lower()

    def test_privacy_rules_forbid_user_agent_storage(self) -> None:
        """R4: store_full_user_agent: false means UA is rejected."""
        data = {"event_type": "page_view", "user_agent": "Mozilla/5.0..."}
        errors = validate_forbidden_fields(data)

        assert len(errors) > 0
        assert errors[0].code == "forbidden_field"

    def test_privacy_rules_forbid_cookie_storage(self) -> None:
        """R4: store_cookies: false means cookies are rejected."""
        data = {"event_type": "page_view", "cookie": "session=abc"}
        errors = validate_forbidden_fields(data)

        assert len(errors) > 0
        assert errors[0].code == "forbidden_field"

    def test_privacy_rules_forbid_visitor_identifiers(self) -> None:
        """R4: store_visitor_identifiers: false means visitor IDs rejected."""
        data = {"event_type": "page_view", "visitor_id": "v123"}
        errors = validate_forbidden_fields(data)

        assert len(errors) > 0
        assert errors[0].code == "forbidden_field"

    def test_analytics_event_has_no_pii_fields(self) -> None:
        """R4: AnalyticsEvent model has no PII fields."""
        from dataclasses import fields

        event_fields = {f.name for f in fields(AnalyticsEvent)}

        # These fields should NOT exist on AnalyticsEvent
        forbidden_pii_fields = {
            "ip",
            "ip_address",
            "user_agent",
            "cookie",
            "cookie_id",
            "visitor_id",
            "email",
            "fingerprint",
        }

        overlap = event_fields & forbidden_pii_fields
        assert len(overlap) == 0, f"PII fields found: {overlap}"

    def test_ingestion_enforces_privacy_at_boundary(
        self,
        service: AnalyticsIngestionService,
    ) -> None:
        """R4: Privacy is enforced at ingestion boundary."""
        # Try to inject PII - should be blocked
        pii_data = {
            "event_type": "page_view",
            "ip": "10.0.0.1",
            "user_agent": "Mozilla/5.0",
            "cookie": "session=xyz",
        }

        event, errors = service.ingest(pii_data)

        # Should be rejected
        assert event is None
        # All three PII fields should be reported
        assert len(errors) >= 3

    def test_privacy_enforcement_cannot_be_bypassed(self) -> None:
        """R4: Privacy enforcement cannot be bypassed."""
        # Even with unusual field names, PII patterns are blocked
        sneaky_pii = {
            "event_type": "page_view",
            "ip_address": "1.2.3.4",  # Variant of ip
            "cookie_id": "abc",  # Variant of cookie
        }

        errors = validate_forbidden_fields(sneaky_pii)
        assert len(errors) == 2  # Both should be caught

    @pytest.fixture
    def service(
        self,
        event_store: InMemoryEventStore,
        time_port: MockTimePort,
    ) -> AnalyticsIngestionService:
        """Create analytics service for privacy tests."""
        return AnalyticsIngestionService(
            event_store=event_store,
            time_port=time_port,
        )

    @pytest.fixture
    def event_store(self) -> InMemoryEventStore:
        """Create event store."""
        return InMemoryEventStore()

    @pytest.fixture
    def time_port(self) -> MockTimePort:
        """Create time port."""
        return MockTimePort()
