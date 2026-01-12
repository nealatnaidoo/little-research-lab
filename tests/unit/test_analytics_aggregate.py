"""
Tests for AnalyticsAggregateService (E6.1, E6.4).

Test assertions:
- TA-0041: Aggregate buckets are created and updated correctly
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.core.services.analytics_aggregate import (
    AggregateConfig,
    AggregateInput,
    AggregateService,
    BucketType,
    InMemoryAggregateRepo,
    UAClass,
    calculate_bucket_end,
    calculate_bucket_start,
    create_aggregate_service,
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

    def advance(self, seconds: int) -> None:
        self._now += timedelta(seconds=seconds)


# --- Fixtures ---


@pytest.fixture
def repo() -> InMemoryAggregateRepo:
    """Fresh aggregate repository."""
    return InMemoryAggregateRepo()


@pytest.fixture
def time_port() -> MockTimePort:
    """Mock time provider."""
    return MockTimePort(datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC))


@pytest.fixture
def service(repo: InMemoryAggregateRepo, time_port: MockTimePort) -> AggregateService:
    """Aggregate service with mock dependencies."""
    return AggregateService(repo=repo, time_port=time_port)


# --- Bucket Calculation Tests ---


class TestBucketCalculation:
    """Test bucket start/end calculations."""

    def test_minute_bucket_start(self) -> None:
        """Minute bucket truncates to start of minute."""
        ts = datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=UTC)
        result = calculate_bucket_start(ts, BucketType.MINUTE)
        assert result == datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC)

    def test_hour_bucket_start(self) -> None:
        """Hour bucket truncates to start of hour."""
        ts = datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC)
        result = calculate_bucket_start(ts, BucketType.HOUR)
        assert result == datetime(2024, 6, 15, 14, 0, 0, tzinfo=UTC)

    def test_day_bucket_start(self) -> None:
        """Day bucket truncates to start of day."""
        ts = datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC)
        result = calculate_bucket_start(ts, BucketType.DAY)
        assert result == datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC)

    def test_minute_bucket_end(self) -> None:
        """Minute bucket ends 1 minute later."""
        start = datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC)
        result = calculate_bucket_end(start, BucketType.MINUTE)
        assert result == datetime(2024, 6, 15, 14, 31, 0, tzinfo=UTC)

    def test_hour_bucket_end(self) -> None:
        """Hour bucket ends 1 hour later."""
        start = datetime(2024, 6, 15, 14, 0, 0, tzinfo=UTC)
        result = calculate_bucket_end(start, BucketType.HOUR)
        assert result == datetime(2024, 6, 15, 15, 0, 0, tzinfo=UTC)

    def test_day_bucket_end(self) -> None:
        """Day bucket ends 1 day later."""
        start = datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC)
        result = calculate_bucket_end(start, BucketType.DAY)
        assert result == datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC)

    def test_naive_datetime_converted(self) -> None:
        """Naive datetime treated as UTC."""
        ts = datetime(2024, 6, 15, 14, 30, 45)  # noqa: DTZ001
        result = calculate_bucket_start(ts, BucketType.MINUTE)
        assert result.tzinfo == UTC


# --- TA-0041: Aggregate Bucket Creation Tests ---


class TestAggregateRecording:
    """Test TA-0041: Aggregate buckets are created and updated."""

    def test_record_creates_all_bucket_types(
        self,
        service: AggregateService,
    ) -> None:
        """Recording creates minute, hour, and day buckets."""
        event = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
            content_id=uuid4(),
        )

        buckets = service.record(event)

        assert len(buckets) == 3
        bucket_types = {b.bucket_type for b in buckets}
        assert bucket_types == {"minute", "hour", "day"}

    def test_record_increments_total_count(
        self,
        service: AggregateService,
    ) -> None:
        """Recording increments total count."""
        event = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
        )

        # Record twice
        service.record(event)
        buckets = service.record(event)

        # Each bucket should have count of 2
        for bucket in buckets:
            assert bucket.count_total == 2

    def test_record_tracks_real_users(self, service: AggregateService) -> None:
        """Real users counted in count_real."""
        event = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
            ua_class=UAClass.REAL,
        )

        buckets = service.record(event)

        for bucket in buckets:
            assert bucket.count_total == 1
            assert bucket.count_real == 1
            assert bucket.count_bot == 0

    def test_record_tracks_bots(self, service: AggregateService) -> None:
        """Bots counted in count_bot."""
        event = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
            ua_class=UAClass.BOT,
        )

        buckets = service.record(event)

        for bucket in buckets:
            assert bucket.count_total == 1
            assert bucket.count_real == 0
            assert bucket.count_bot == 1

    def test_unknown_ua_treated_as_real_by_default(
        self,
        service: AggregateService,
    ) -> None:
        """Unknown UA counted as real by default."""
        event = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
            ua_class=UAClass.UNKNOWN,
        )

        buckets = service.record(event)

        for bucket in buckets:
            assert bucket.count_real == 1

    def test_unknown_ua_not_counted_when_disabled(
        self,
        repo: InMemoryAggregateRepo,
        time_port: MockTimePort,
    ) -> None:
        """Unknown UA not counted as real when configured."""
        config = AggregateConfig(treat_unknown_as_real=False)
        service = AggregateService(repo=repo, time_port=time_port, config=config)

        event = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
            ua_class=UAClass.UNKNOWN,
        )

        buckets = service.record(event)

        for bucket in buckets:
            assert bucket.count_total == 1
            assert bucket.count_real == 0
            assert bucket.count_bot == 0

    def test_record_stores_content_id(self, service: AggregateService) -> None:
        """Content ID stored in bucket."""
        content_id = uuid4()
        event = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
            content_id=content_id,
        )

        buckets = service.record(event)

        for bucket in buckets:
            assert bucket.content_id == content_id

    def test_record_stores_utm_dimensions(self, service: AggregateService) -> None:
        """UTM dimensions stored in bucket."""
        event = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="summer_sale",
        )

        buckets = service.record(event)

        for bucket in buckets:
            assert bucket.utm_source == "google"
            assert bucket.utm_medium == "cpc"
            assert bucket.utm_campaign == "summer_sale"

    def test_record_stores_referrer_domain(self, service: AggregateService) -> None:
        """Referrer domain stored in bucket."""
        event = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
            referrer_domain="facebook.com",
        )

        buckets = service.record(event)

        for bucket in buckets:
            assert bucket.referrer_domain == "facebook.com"

    def test_same_bucket_reused(self, service: AggregateService) -> None:
        """Same bucket reused for events with same dimensions."""
        content_id = uuid4()
        event1 = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 15, tzinfo=UTC),
            content_id=content_id,
            ua_class=UAClass.REAL,
        )
        event2 = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
            content_id=content_id,
            ua_class=UAClass.REAL,
        )

        service.record(event1)
        buckets = service.record(event2)

        minute_bucket = next(b for b in buckets if b.bucket_type == "minute")
        assert minute_bucket.count_total == 2

    def test_different_buckets_for_different_dimensions(
        self,
        service: AggregateService,
    ) -> None:
        """Different dimensions create separate buckets."""
        content1 = uuid4()
        content2 = uuid4()

        event1 = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
            content_id=content1,
            ua_class=UAClass.REAL,
        )
        event2 = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
            content_id=content2,
            ua_class=UAClass.REAL,
        )

        service.record(event1)
        buckets = service.record(event2)

        minute_bucket = next(b for b in buckets if b.bucket_type == "minute")
        assert minute_bucket.count_total == 1
        assert minute_bucket.content_id == content2

    def test_disabled_service_returns_empty(
        self,
        repo: InMemoryAggregateRepo,
        time_port: MockTimePort,
    ) -> None:
        """Disabled service returns empty list."""
        config = AggregateConfig(enabled=False)
        service = AggregateService(repo=repo, time_port=time_port, config=config)

        event = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
        )

        buckets = service.record(event)

        assert buckets == []

    def test_custom_bucket_types(
        self,
        repo: InMemoryAggregateRepo,
        time_port: MockTimePort,
    ) -> None:
        """Only configured bucket types created."""
        config = AggregateConfig(bucket_types=(BucketType.HOUR, BucketType.DAY))
        service = AggregateService(repo=repo, time_port=time_port, config=config)

        event = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC),
        )

        buckets = service.record(event)

        assert len(buckets) == 2
        bucket_types = {b.bucket_type for b in buckets}
        assert bucket_types == {"hour", "day"}


class TestAggregateQueries:
    """Test aggregate query methods."""

    def test_query_buckets_by_time_range(self, service: AggregateService) -> None:
        """Query returns buckets in time range."""
        # Record events in different hours
        for hour in [10, 11, 12, 13, 14]:
            event = AggregateInput(
                event_type="page_view",
                timestamp=datetime(2024, 6, 15, hour, 30, 0, tzinfo=UTC),
                ua_class=UAClass.REAL,
            )
            service.record(event)

        # Query middle hours
        results = service.query_buckets(
            bucket_type=BucketType.HOUR,
            start=datetime(2024, 6, 15, 11, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 15, 14, 0, 0, tzinfo=UTC),
        )

        # Should get hours 11, 12, 13 (end is exclusive)
        assert len(results) == 3

    def test_query_buckets_by_event_type(self, service: AggregateService) -> None:
        """Query filters by event type."""
        event1 = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
            ua_class=UAClass.REAL,
        )
        event2 = AggregateInput(
            event_type="asset_download",
            timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
            ua_class=UAClass.REAL,
        )

        service.record(event1)
        service.record(event2)

        results = service.query_buckets(
            bucket_type=BucketType.HOUR,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
            event_type="page_view",
        )

        assert len(results) == 1
        assert results[0].event_type == "page_view"

    def test_query_buckets_by_content_id(self, service: AggregateService) -> None:
        """Query filters by content ID."""
        content1 = uuid4()
        content2 = uuid4()

        for cid in [content1, content2, content1]:
            event = AggregateInput(
                event_type="page_view",
                timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
                content_id=cid,
                ua_class=UAClass.REAL,
            )
            service.record(event)

        results = service.query_buckets(
            bucket_type=BucketType.HOUR,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
            content_id=content1,
        )

        assert len(results) == 1
        assert results[0].count_total == 2

    def test_query_results_sorted_by_time(self, service: AggregateService) -> None:
        """Query results sorted by bucket_start."""
        for hour in [14, 10, 12]:
            event = AggregateInput(
                event_type="page_view",
                timestamp=datetime(2024, 6, 15, hour, 30, 0, tzinfo=UTC),
                ua_class=UAClass.REAL,
            )
            service.record(event)

        results = service.query_buckets(
            bucket_type=BucketType.HOUR,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
        )

        times = [r.bucket_start for r in results]
        assert times == sorted(times)


class TestGetTotals:
    """Test total aggregation."""

    def test_get_totals_sums_buckets(self, service: AggregateService) -> None:
        """Get totals sums all matching buckets."""
        for i in range(5):
            event = AggregateInput(
                event_type="page_view",
                timestamp=datetime(2024, 6, 15, 14, 30 + i, 0, tzinfo=UTC),
                ua_class=UAClass.REAL,
            )
            service.record(event)

        totals = service.get_totals(
            bucket_type=BucketType.DAY,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
        )

        assert totals["total"] == 5
        assert totals["real"] == 5
        assert totals["bot"] == 0

    def test_get_totals_excludes_bots_by_default(
        self,
        service: AggregateService,
    ) -> None:
        """Get totals excludes bots by default."""
        event_real = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
            ua_class=UAClass.REAL,
        )
        event_bot = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 31, 0, tzinfo=UTC),
            ua_class=UAClass.BOT,
        )

        for _ in range(3):
            service.record(event_real)
        for _ in range(2):
            service.record(event_bot)

        totals = service.get_totals(
            bucket_type=BucketType.DAY,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
        )

        assert totals["total"] == 3  # Excludes bots
        assert totals["total_with_bots"] == 5
        assert totals["real"] == 3
        assert totals["bot"] == 2

    def test_get_totals_includes_bots_when_requested(
        self,
        service: AggregateService,
    ) -> None:
        """Get totals includes bots when exclude_bots=False."""
        event_real = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
            ua_class=UAClass.REAL,
        )
        event_bot = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 31, 0, tzinfo=UTC),
            ua_class=UAClass.BOT,
        )

        service.record(event_real)
        service.record(event_bot)

        totals = service.get_totals(
            bucket_type=BucketType.DAY,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
            exclude_bots=False,
        )

        assert totals["total"] == 2


class TestTimeSeries:
    """Test time series generation."""

    def test_get_time_series(self, service: AggregateService) -> None:
        """Get time series returns ordered points."""
        for hour in [10, 11, 12]:
            for _ in range(hour - 9):  # 1, 2, 3 events
                event = AggregateInput(
                    event_type="page_view",
                    timestamp=datetime(2024, 6, 15, hour, 30, 0, tzinfo=UTC),
                    ua_class=UAClass.REAL,
                )
                service.record(event)

        series = service.get_time_series(
            bucket_type=BucketType.HOUR,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
        )

        assert len(series) == 3
        assert series[0]["count"] == 1
        assert series[1]["count"] == 2
        assert series[2]["count"] == 3

    def test_get_time_series_aggregates_dimensions(
        self,
        service: AggregateService,
    ) -> None:
        """Time series sums across dimensions."""
        # Same hour, different sources
        event1 = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
            utm_source="google",
            ua_class=UAClass.REAL,
        )
        event2 = AggregateInput(
            event_type="page_view",
            timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
            utm_source="facebook",
            ua_class=UAClass.REAL,
        )

        service.record(event1)
        service.record(event2)

        series = service.get_time_series(
            bucket_type=BucketType.HOUR,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
        )

        assert len(series) == 1
        assert series[0]["count"] == 2


class TestTopContent:
    """Test top content queries."""

    def test_get_top_content(self, service: AggregateService) -> None:
        """Get top content returns sorted results."""
        content1 = uuid4()
        content2 = uuid4()
        content3 = uuid4()

        for _ in range(5):
            service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
                    content_id=content1,
                    ua_class=UAClass.REAL,
                )
            )

        for _ in range(3):
            service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
                    content_id=content2,
                    ua_class=UAClass.REAL,
                )
            )

        for _ in range(1):
            service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
                    content_id=content3,
                    ua_class=UAClass.REAL,
                )
            )

        top = service.get_top_content(
            bucket_type=BucketType.DAY,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
        )

        assert len(top) == 3
        assert top[0]["content_id"] == content1
        assert top[0]["count"] == 5
        assert top[1]["content_id"] == content2
        assert top[1]["count"] == 3

    def test_get_top_content_respects_limit(self, service: AggregateService) -> None:
        """Top content respects limit parameter."""
        for _ in range(10):
            service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
                    content_id=uuid4(),
                    ua_class=UAClass.REAL,
                )
            )

        top = service.get_top_content(
            bucket_type=BucketType.DAY,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
            limit=5,
        )

        assert len(top) == 5


class TestTopSources:
    """Test top sources queries."""

    def test_get_top_sources(self, service: AggregateService) -> None:
        """Get top sources returns sorted results."""
        for _ in range(5):
            service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
                    utm_source="google",
                    utm_medium="cpc",
                    ua_class=UAClass.REAL,
                )
            )

        for _ in range(3):
            service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
                    utm_source="facebook",
                    utm_medium="social",
                    ua_class=UAClass.REAL,
                )
            )

        top = service.get_top_sources(
            bucket_type=BucketType.DAY,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
        )

        assert len(top) == 2
        assert top[0]["source"] == "google"
        assert top[0]["medium"] == "cpc"
        assert top[0]["count"] == 5


class TestTopReferrers:
    """Test top referrers queries."""

    def test_get_top_referrers(self, service: AggregateService) -> None:
        """Get top referrers returns sorted results."""
        for _ in range(5):
            service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
                    referrer_domain="twitter.com",
                    ua_class=UAClass.REAL,
                )
            )

        for _ in range(3):
            service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
                    referrer_domain="reddit.com",
                    ua_class=UAClass.REAL,
                )
            )

        top = service.get_top_referrers(
            bucket_type=BucketType.DAY,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
        )

        assert len(top) == 2
        assert top[0]["domain"] == "twitter.com"
        assert top[0]["count"] == 5

    def test_get_top_referrers_excludes_null(self, service: AggregateService) -> None:
        """Top referrers excludes null domains."""
        service.record(
            AggregateInput(
                event_type="page_view",
                timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
                referrer_domain=None,
                ua_class=UAClass.REAL,
            )
        )
        service.record(
            AggregateInput(
                event_type="page_view",
                timestamp=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
                referrer_domain="example.com",
                ua_class=UAClass.REAL,
            )
        )

        top = service.get_top_referrers(
            bucket_type=BucketType.DAY,
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
        )

        assert len(top) == 1
        assert top[0]["domain"] == "example.com"


# --- Repository Tests ---


class TestInMemoryAggregateRepo:
    """Test in-memory repository."""

    def test_get_or_create_creates_new(self, repo: InMemoryAggregateRepo) -> None:
        """Creates new bucket when not exists."""
        bucket = repo.get_or_create_bucket(
            bucket_type="hour",
            bucket_start=datetime(2024, 6, 15, 14, 0, 0, tzinfo=UTC),
            event_type="page_view",
            dimensions={"content_id": None},
        )

        assert bucket is not None
        assert bucket.count_total == 0

    def test_get_or_create_returns_existing(self, repo: InMemoryAggregateRepo) -> None:
        """Returns existing bucket when exists."""
        bucket1 = repo.get_or_create_bucket(
            bucket_type="hour",
            bucket_start=datetime(2024, 6, 15, 14, 0, 0, tzinfo=UTC),
            event_type="page_view",
            dimensions={"content_id": None},
        )
        bucket2 = repo.get_or_create_bucket(
            bucket_type="hour",
            bucket_start=datetime(2024, 6, 15, 14, 0, 0, tzinfo=UTC),
            event_type="page_view",
            dimensions={"content_id": None},
        )

        assert bucket1.id == bucket2.id

    def test_increment_updates_counts(self, repo: InMemoryAggregateRepo) -> None:
        """Increment updates bucket counts."""
        bucket = repo.get_or_create_bucket(
            bucket_type="hour",
            bucket_start=datetime(2024, 6, 15, 14, 0, 0, tzinfo=UTC),
            event_type="page_view",
            dimensions={},
        )

        repo.increment(bucket.id, count_total=1, count_real=1)
        repo.increment(bucket.id, count_total=1, count_bot=1)

        updated = repo.get_or_create_bucket(
            bucket_type="hour",
            bucket_start=datetime(2024, 6, 15, 14, 0, 0, tzinfo=UTC),
            event_type="page_view",
            dimensions={},
        )

        assert updated.count_total == 2
        assert updated.count_real == 1
        assert updated.count_bot == 1

    def test_query_empty_returns_empty(self, repo: InMemoryAggregateRepo) -> None:
        """Query on empty repo returns empty list."""
        results = repo.query(
            bucket_type="hour",
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
        )

        assert results == []

    def test_clear(self, repo: InMemoryAggregateRepo) -> None:
        """Clear removes all buckets."""
        repo.get_or_create_bucket(
            bucket_type="hour",
            bucket_start=datetime(2024, 6, 15, 14, 0, 0, tzinfo=UTC),
            event_type="page_view",
            dimensions={},
        )
        repo.clear()

        results = repo.query(
            bucket_type="hour",
            start=datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC),
            end=datetime(2024, 6, 16, 0, 0, 0, tzinfo=UTC),
        )

        assert results == []


# --- Factory Tests ---


class TestFactory:
    """Test factory function."""

    def test_create_service(self) -> None:
        """Factory creates service."""
        service = create_aggregate_service()
        assert isinstance(service, AggregateService)

    def test_create_with_repo(self, repo: InMemoryAggregateRepo) -> None:
        """Factory accepts repo."""
        service = create_aggregate_service(repo=repo)
        assert isinstance(service, AggregateService)

    def test_create_with_config(self) -> None:
        """Factory accepts config."""
        config = AggregateConfig(enabled=False)
        service = create_aggregate_service(config=config)
        assert isinstance(service, AggregateService)
