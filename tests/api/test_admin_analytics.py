"""
Tests for Admin Analytics API (E6.4).

Test assertions:
- TA-0041: Dashboard queries return correct aggregated data
- TA-0042: Analytics data can be queried by time range and filters
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import admin_analytics
from src.components.analytics import (
    AggregateInput,
    AggregateService,
    InMemoryAggregateRepo,
    UAClass,
)

# --- Test Setup ---


@pytest.fixture
def repo() -> InMemoryAggregateRepo:
    """Fresh aggregate repository."""
    return InMemoryAggregateRepo()


@pytest.fixture
def aggregate_service(repo: InMemoryAggregateRepo) -> AggregateService:
    """Aggregate service with test repo."""
    return AggregateService(repo=repo)


@pytest.fixture
def app(aggregate_service: AggregateService) -> FastAPI:
    """Test FastAPI app with analytics routes."""
    app = FastAPI()
    app.include_router(admin_analytics.router, prefix="/analytics")

    # Override dependency
    app.dependency_overrides[admin_analytics.get_aggregate_service] = lambda: aggregate_service

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Test client."""
    return TestClient(app)


# --- Helper Functions ---


def record_events(
    service: AggregateService,
    count: int = 1,
    timestamp: datetime | None = None,
    event_type: str = "page_view",
    content_id: str | None = None,
    ua_class: UAClass = UAClass.REAL,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    referrer_domain: str | None = None,
) -> None:
    """Record test events."""
    ts = timestamp or datetime.now(UTC)
    content_uuid = uuid4() if content_id == "random" else (uuid4() if content_id is None else None)

    for _ in range(count):
        event = AggregateInput(
            event_type=event_type,
            timestamp=ts,
            content_id=content_uuid,
            ua_class=ua_class,
            utm_source=utm_source,
            utm_medium=utm_medium,
            referrer_domain=referrer_domain,
        )
        service.record(event)


# --- TA-0041: Dashboard Query Tests ---


class TestTotalsEndpoint:
    """Test totals endpoint (TA-0041)."""

    def test_get_totals_empty(self, client: TestClient) -> None:
        """Empty data returns zero counts."""
        response = client.get(
            "/analytics/totals",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["real"] == 0
        assert data["bot"] == 0

    def test_get_totals_with_data(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Returns correct totals."""
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        record_events(aggregate_service, count=5, timestamp=ts)
        record_events(aggregate_service, count=2, timestamp=ts, ua_class=UAClass.BOT)

        response = client.get(
            "/analytics/totals",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
                "bucket_type": "day",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5  # Excludes bots by default
        assert data["total_with_bots"] == 7
        assert data["real"] == 5
        assert data["bot"] == 2

    def test_get_totals_includes_bots(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Can include bots in total."""
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        record_events(aggregate_service, count=3, timestamp=ts)
        record_events(aggregate_service, count=2, timestamp=ts, ua_class=UAClass.BOT)

        response = client.get(
            "/analytics/totals",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
                "exclude_bots": "false",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5

    def test_get_totals_default_time_range(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Uses default 7-day range when not specified."""
        ts = datetime.now(UTC) - timedelta(days=3)
        record_events(aggregate_service, count=3, timestamp=ts)

        response = client.get("/analytics/totals")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    def test_get_totals_invalid_datetime(self, client: TestClient) -> None:
        """Invalid datetime returns 400."""
        response = client.get(
            "/analytics/totals",
            params={"start": "not-a-date", "end": "2024-06-16T00:00:00Z"},
        )

        assert response.status_code == 400

    def test_get_totals_invalid_bucket_type(self, client: TestClient) -> None:
        """Invalid bucket type returns 400."""
        response = client.get(
            "/analytics/totals",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
                "bucket_type": "invalid",
            },
        )

        assert response.status_code == 400


class TestTimeSeriesEndpoint:
    """Test time series endpoint (TA-0041)."""

    def test_get_time_series_empty(self, client: TestClient) -> None:
        """Empty data returns empty points."""
        response = client.get(
            "/analytics/time-series",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["points"] == []

    def test_get_time_series_with_data(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Returns time series data points."""
        for hour in [10, 11, 12]:
            ts = datetime(2024, 6, 15, hour, 30, 0, tzinfo=UTC)
            record_events(aggregate_service, count=hour, timestamp=ts)

        response = client.get(
            "/analytics/time-series",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
                "bucket_type": "hour",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["points"]) == 3
        assert data["bucket_type"] == "hour"

    def test_get_time_series_sorted(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Time series points are sorted by timestamp."""
        for hour in [14, 10, 12]:
            ts = datetime(2024, 6, 15, hour, 0, 0, tzinfo=UTC)
            record_events(aggregate_service, count=1, timestamp=ts)

        response = client.get(
            "/analytics/time-series",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
                "bucket_type": "hour",
            },
        )

        data = response.json()
        timestamps = [p["timestamp"] for p in data["points"]]
        assert timestamps == sorted(timestamps)


# --- TA-0042: Query Filter Tests ---


class TestTopContentEndpoint:
    """Test top content endpoint (TA-0042)."""

    def test_get_top_content_empty(self, client: TestClient) -> None:
        """Empty data returns empty items."""
        response = client.get(
            "/analytics/top-content",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_get_top_content_with_data(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Returns sorted content by views."""
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        content1 = uuid4()
        content2 = uuid4()

        for _ in range(5):
            aggregate_service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=ts,
                    content_id=content1,
                    ua_class=UAClass.REAL,
                )
            )
        for _ in range(3):
            aggregate_service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=ts,
                    content_id=content2,
                    ua_class=UAClass.REAL,
                )
            )

        response = client.get(
            "/analytics/top-content",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["count"] == 5
        assert data["items"][1]["count"] == 3

    def test_get_top_content_respects_limit(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Respects limit parameter."""
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

        for _ in range(10):
            aggregate_service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=ts,
                    content_id=uuid4(),
                    ua_class=UAClass.REAL,
                )
            )

        response = client.get(
            "/analytics/top-content",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
                "limit": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5


class TestTopSourcesEndpoint:
    """Test top sources endpoint (TA-0042)."""

    def test_get_top_sources_empty(self, client: TestClient) -> None:
        """Empty data returns empty items."""
        response = client.get(
            "/analytics/top-sources",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_get_top_sources_with_data(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Returns sorted sources by views."""
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

        for _ in range(5):
            aggregate_service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=ts,
                    utm_source="google",
                    utm_medium="cpc",
                    ua_class=UAClass.REAL,
                )
            )
        for _ in range(3):
            aggregate_service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=ts,
                    utm_source="facebook",
                    utm_medium="social",
                    ua_class=UAClass.REAL,
                )
            )

        response = client.get(
            "/analytics/top-sources",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["source"] == "google"
        assert data["items"][0]["count"] == 5


class TestTopReferrersEndpoint:
    """Test top referrers endpoint (TA-0042)."""

    def test_get_top_referrers_empty(self, client: TestClient) -> None:
        """Empty data returns empty items."""
        response = client.get(
            "/analytics/top-referrers",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_get_top_referrers_with_data(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Returns sorted referrers by views."""
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

        for _ in range(5):
            aggregate_service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=ts,
                    referrer_domain="twitter.com",
                    ua_class=UAClass.REAL,
                )
            )
        for _ in range(3):
            aggregate_service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=ts,
                    referrer_domain="reddit.com",
                    ua_class=UAClass.REAL,
                )
            )

        response = client.get(
            "/analytics/top-referrers",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["domain"] == "twitter.com"
        assert data["items"][0]["count"] == 5


class TestDashboardEndpoint:
    """Test dashboard endpoint (TA-0041, TA-0042)."""

    def test_get_dashboard_empty(self, client: TestClient) -> None:
        """Empty dashboard returns structure with zeros."""
        response = client.get(
            "/analytics/dashboard",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "totals" in data
        assert "time_series" in data
        assert "top_content" in data
        assert "top_sources" in data
        assert "top_referrers" in data

        assert data["totals"]["total"] == 0

    def test_get_dashboard_with_data(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Dashboard returns all metrics."""
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        content_id = uuid4()

        for _ in range(5):
            aggregate_service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=ts,
                    content_id=content_id,
                    utm_source="google",
                    utm_medium="cpc",
                    referrer_domain="google.com",
                    ua_class=UAClass.REAL,
                )
            )

        response = client.get(
            "/analytics/dashboard",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all sections have data
        assert data["totals"]["total"] == 5
        assert len(data["time_series"]["points"]) >= 1
        assert len(data["top_content"]["items"]) == 1
        assert len(data["top_sources"]["items"]) == 1
        assert len(data["top_referrers"]["items"]) == 1

    def test_get_dashboard_period_info(self, client: TestClient) -> None:
        """Dashboard includes period information."""
        response = client.get(
            "/analytics/dashboard",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "2024-06-15" in data["period_start"]
        assert "2024-06-16" in data["period_end"]


class TestBucketTypeParameter:
    """Test bucket type parameter across endpoints."""

    def test_minute_bucket(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Minute bucket type works."""
        ts = datetime(2024, 6, 15, 12, 30, 0, tzinfo=UTC)
        record_events(aggregate_service, count=1, timestamp=ts)

        response = client.get(
            "/analytics/totals",
            params={
                "start": "2024-06-15T12:00:00Z",
                "end": "2024-06-15T13:00:00Z",
                "bucket_type": "minute",
            },
        )

        assert response.status_code == 200

    def test_hour_bucket(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Hour bucket type works."""
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        record_events(aggregate_service, count=1, timestamp=ts)

        response = client.get(
            "/analytics/totals",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
                "bucket_type": "hour",
            },
        )

        assert response.status_code == 200

    def test_day_bucket(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Day bucket type works."""
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        record_events(aggregate_service, count=1, timestamp=ts)

        response = client.get(
            "/analytics/totals",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
                "bucket_type": "day",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1


class TestEventTypeFilter:
    """Test event type filter."""

    def test_filter_by_event_type(
        self,
        client: TestClient,
        aggregate_service: AggregateService,
    ) -> None:
        """Can filter by event type."""
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

        for _ in range(5):
            aggregate_service.record(
                AggregateInput(
                    event_type="page_view",
                    timestamp=ts,
                    ua_class=UAClass.REAL,
                )
            )
        for _ in range(3):
            aggregate_service.record(
                AggregateInput(
                    event_type="asset_download",
                    timestamp=ts,
                    ua_class=UAClass.REAL,
                )
            )

        response = client.get(
            "/analytics/totals",
            params={
                "start": "2024-06-15T00:00:00Z",
                "end": "2024-06-16T00:00:00Z",
                "event_type": "page_view",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
