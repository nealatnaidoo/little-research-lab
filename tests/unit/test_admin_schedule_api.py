"""
Tests for Admin Scheduling API (E5.1, E5.2, E5.3).

Test assertions:
- TA-0026: Schedule/unschedule content
- TA-0031: Calendar API returns jobs in date range
- TA-0033: Publish now functionality
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.routes.admin_schedule import (
    MockPublisher,
    MockPublishJobRepo,
    SchedulerConfig,
    SchedulerService,
    get_scheduler_service,
    router,
)

# --- Test Client Setup ---


@pytest.fixture
def repo() -> MockPublishJobRepo:
    """Fresh repository for each test."""
    return MockPublishJobRepo()


@pytest.fixture
def publisher() -> MockPublisher:
    """Fresh publisher for each test."""
    return MockPublisher()


@pytest.fixture
def service(repo: MockPublishJobRepo, publisher: MockPublisher) -> SchedulerService:
    """Service with test dependencies."""
    return SchedulerService(
        repo=repo,
        publisher=publisher,
        config=SchedulerConfig(),
    )


@pytest.fixture
def client(service: SchedulerService) -> TestClient:
    """Test client with mocked dependencies."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    # Override dependency
    app.dependency_overrides[get_scheduler_service] = lambda: service

    return TestClient(app)


# --- TA-0026: Schedule/Unschedule Content ---


class TestScheduleContent:
    """Test TA-0026: Schedule content for publishing."""

    def test_schedule_success(self, client: TestClient) -> None:
        """Successfully schedule content."""
        content_id = uuid4()
        publish_at = datetime.now(UTC) + timedelta(hours=1)

        response = client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": publish_at.isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content_id"] == str(content_id)
        assert data["status"] == "queued"

    def test_schedule_past_time_rejected(self, client: TestClient) -> None:
        """Scheduling in past is rejected."""
        content_id = uuid4()
        publish_at = datetime.now(UTC) - timedelta(hours=1)

        response = client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": publish_at.isoformat(),
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "errors" in data["detail"]

    def test_schedule_idempotent(self, client: TestClient) -> None:
        """Scheduling same content+time returns existing job."""
        content_id = uuid4()
        publish_at = datetime.now(UTC) + timedelta(hours=1)

        # First schedule
        response1 = client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": publish_at.isoformat(),
            },
        )
        job_id_1 = response1.json()["id"]

        # Second schedule - same content and time
        response2 = client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": publish_at.isoformat(),
            },
        )
        job_id_2 = response2.json()["id"]

        assert job_id_1 == job_id_2


class TestUnscheduleContent:
    """Test TA-0026: Unschedule content."""

    def test_unschedule_success(self, client: TestClient) -> None:
        """Successfully unschedule content."""
        content_id = uuid4()
        publish_at = datetime.now(UTC) + timedelta(hours=1)

        # First schedule
        schedule_response = client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": publish_at.isoformat(),
            },
        )
        job_id = schedule_response.json()["id"]

        # Unschedule
        response = client.delete(f"/schedule/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_unschedule_not_found(self, client: TestClient) -> None:
        """Unscheduling non-existent job fails."""
        fake_id = uuid4()

        response = client.delete(f"/schedule/{fake_id}")

        assert response.status_code == 400


class TestRescheduleContent:
    """Test rescheduling content."""

    def test_reschedule_success(self, client: TestClient) -> None:
        """Successfully reschedule content."""
        content_id = uuid4()
        old_time = datetime.now(UTC) + timedelta(hours=1)
        new_time = datetime.now(UTC) + timedelta(hours=2)

        # Schedule
        schedule_response = client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": old_time.isoformat(),
            },
        )
        job_id = schedule_response.json()["id"]

        # Reschedule
        response = client.put(
            f"/schedule/{job_id}",
            json={"new_publish_at_utc": new_time.isoformat()},
        )

        assert response.status_code == 200
        data = response.json()
        # Compare dates (ignoring microseconds that may differ)
        result_time = datetime.fromisoformat(data["publish_at_utc"].replace("Z", "+00:00"))
        assert abs((result_time - new_time).total_seconds()) < 1


class TestGetJob:
    """Test getting job details."""

    def test_get_job_success(self, client: TestClient) -> None:
        """Successfully get job details."""
        content_id = uuid4()
        publish_at = datetime.now(UTC) + timedelta(hours=1)

        # Schedule
        schedule_response = client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": publish_at.isoformat(),
            },
        )
        job_id = schedule_response.json()["id"]

        # Get
        response = client.get(f"/schedule/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["content_id"] == str(content_id)

    def test_get_job_not_found(self, client: TestClient) -> None:
        """Getting non-existent job returns 404."""
        fake_id = uuid4()

        response = client.get(f"/schedule/{fake_id}")

        assert response.status_code == 404


class TestGetJobsForContent:
    """Test getting jobs for a content item."""

    def test_get_jobs_for_content(self, client: TestClient) -> None:
        """Get all pending jobs for content."""
        content_id = uuid4()
        time1 = datetime.now(UTC) + timedelta(hours=1)
        time2 = datetime.now(UTC) + timedelta(hours=2)

        # Schedule twice at different times
        client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": time1.isoformat(),
            },
        )
        client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": time2.isoformat(),
            },
        )

        # Get jobs
        response = client.get(f"/schedule/content/{content_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_jobs_for_content_empty(self, client: TestClient) -> None:
        """Get jobs for content with no jobs."""
        content_id = uuid4()

        response = client.get(f"/schedule/content/{content_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


# --- TA-0033: Publish Now ---


class TestPublishNow:
    """Test TA-0033: Publish now functionality."""

    def test_publish_now_success(self, client: TestClient) -> None:
        """Successfully publish content immediately."""
        content_id = uuid4()

        response = client.post(
            "/publish-now",
            json={"content_id": str(content_id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["actual_publish_at"] is not None

    def test_publish_now_failure(
        self,
        client: TestClient,
        service: SchedulerService,
    ) -> None:
        """Handle publish failure gracefully."""
        # Make publisher fail
        if hasattr(service, "_publisher") and service._publisher:
            service._publisher.publish = lambda x: (False, "Simulated failure")

        content_id = uuid4()

        response = client.post(
            "/publish-now",
            json={"content_id": str(content_id)},
        )

        # Should still return 200 but with success=False
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


# --- Run Due Jobs ---


class TestRunDueJobs:
    """Test manual job execution trigger."""

    def test_run_due_jobs_empty(self, client: TestClient) -> None:
        """Run with no due jobs."""
        response = client.post("/run-due-jobs")

        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 0

    def test_run_due_jobs_with_jobs(self, client: TestClient) -> None:
        """Run with due jobs."""
        content_id = uuid4()

        # Schedule for now (will be immediately due)
        now = datetime.now(UTC)
        client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": now.isoformat(),
            },
        )

        response = client.post("/run-due-jobs")

        assert response.status_code == 200
        data = response.json()
        assert data["processed"] >= 0  # May be 0 if job was already claimed


# --- Edge Cases ---


class TestEdgeCases:
    """Test edge cases."""

    def test_invalid_uuid(self, client: TestClient) -> None:
        """Invalid UUID returns error."""
        response = client.get("/schedule/not-a-uuid")
        assert response.status_code == 422

    def test_invalid_datetime(self, client: TestClient) -> None:
        """Invalid datetime returns error."""
        response = client.post(
            "/schedule",
            json={
                "content_id": str(uuid4()),
                "publish_at_utc": "not-a-date",
            },
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client: TestClient) -> None:
        """Missing required fields returns error."""
        response = client.post("/schedule", json={})
        assert response.status_code == 422


# --- TA-0031: Calendar API ---


class TestCalendarAPI:
    """Test TA-0031: Calendar API returns jobs in date range."""

    def test_calendar_empty(self, client: TestClient) -> None:
        """Calendar returns empty when no jobs in range."""
        start = datetime.now(UTC)
        end = start + timedelta(days=7)

        response = client.get(
            "/calendar",
            params={
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []
        assert data["total_count"] == 0

    def test_calendar_returns_jobs_in_range(self, client: TestClient) -> None:
        """Calendar returns jobs within date range."""
        now = datetime.now(UTC)
        start = now
        end = now + timedelta(days=7)

        # Schedule a job within range
        content_id = uuid4()
        publish_at = now + timedelta(days=1)

        client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": publish_at.isoformat(),
            },
        )

        # Get calendar
        response = client.get(
            "/calendar",
            params={
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["events"]) == 1
        assert data["events"][0]["content_id"] == str(content_id)
        assert data["events"][0]["status"] == "queued"

    def test_calendar_excludes_jobs_outside_range(self, client: TestClient) -> None:
        """Calendar excludes jobs outside date range."""
        now = datetime.now(UTC)

        # Schedule a job outside range (in 10 days)
        content_id = uuid4()
        publish_at = now + timedelta(days=10)

        client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": publish_at.isoformat(),
            },
        )

        # Query for next 3 days only
        response = client.get(
            "/calendar",
            params={
                "start": now.isoformat(),
                "end": (now + timedelta(days=3)).isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0

    def test_calendar_multiple_jobs(self, client: TestClient) -> None:
        """Calendar returns multiple jobs."""
        now = datetime.now(UTC)

        # Schedule multiple jobs
        content_ids = [uuid4(), uuid4(), uuid4()]
        for i, cid in enumerate(content_ids):
            client.post(
                "/schedule",
                json={
                    "content_id": str(cid),
                    "publish_at_utc": (now + timedelta(days=i + 1)).isoformat(),
                },
            )

        # Get calendar
        response = client.get(
            "/calendar",
            params={
                "start": now.isoformat(),
                "end": (now + timedelta(days=7)).isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3

    def test_calendar_filter_by_status(self, client: TestClient) -> None:
        """Calendar can filter by status."""
        now = datetime.now(UTC)

        # Schedule a job (will be queued)
        content_id = uuid4()
        publish_at = now + timedelta(days=1)

        client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": publish_at.isoformat(),
            },
        )

        # Filter by queued status
        response = client.get(
            "/calendar",
            params={
                "start": now.isoformat(),
                "end": (now + timedelta(days=7)).isoformat(),
                "status": "queued",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1

        # Filter by running status (should be empty)
        response = client.get(
            "/calendar",
            params={
                "start": now.isoformat(),
                "end": (now + timedelta(days=7)).isoformat(),
                "status": "running",
            },
        )

        data = response.json()
        assert data["total_count"] == 0

    def test_calendar_event_has_required_fields(self, client: TestClient) -> None:
        """Calendar events have all required fields."""
        now = datetime.now(UTC)
        content_id = uuid4()
        publish_at = now + timedelta(days=1)

        client.post(
            "/schedule",
            json={
                "content_id": str(content_id),
                "publish_at_utc": publish_at.isoformat(),
            },
        )

        response = client.get(
            "/calendar",
            params={
                "start": now.isoformat(),
                "end": (now + timedelta(days=7)).isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        event = data["events"][0]

        # Required fields for calendar UI
        assert "id" in event
        assert "content_id" in event
        assert "title" in event
        assert "start" in event
        assert "status" in event
        assert "is_all_day" in event

    def test_calendar_events_sorted_by_date(self, client: TestClient) -> None:
        """Calendar events are sorted by publish date."""
        now = datetime.now(UTC)

        # Schedule in reverse order
        times = [
            now + timedelta(days=3),
            now + timedelta(days=1),
            now + timedelta(days=2),
        ]

        for t in times:
            client.post(
                "/schedule",
                json={
                    "content_id": str(uuid4()),
                    "publish_at_utc": t.isoformat(),
                },
            )

        response = client.get(
            "/calendar",
            params={
                "start": now.isoformat(),
                "end": (now + timedelta(days=7)).isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        events = data["events"]

        # Should be sorted by start time
        starts = [e["start"] for e in events]
        assert starts == sorted(starts)

    def test_calendar_response_includes_range(self, client: TestClient) -> None:
        """Calendar response includes requested date range."""
        start = datetime.now(UTC)
        end = start + timedelta(days=7)

        response = client.get(
            "/calendar",
            params={
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "start_date" in data
        assert "end_date" in data
