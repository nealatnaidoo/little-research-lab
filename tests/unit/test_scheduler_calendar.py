"""
Tests for Scheduler Calendar functionality (TA-0031).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.components.scheduler import SchedulerService, create_publish_job
from tests.unit.test_scheduler import (
    MockPublishJobRepo,
    MockTimePort,
    SchedulerConfig,
)


@pytest.fixture
def repo() -> MockPublishJobRepo:
    return MockPublishJobRepo()


@pytest.fixture
def service(repo: MockPublishJobRepo) -> SchedulerService:
    return SchedulerService(
        repo=repo,
        time_port=MockTimePort(),  # Uses fixed time 2024-06-15 12:00:00
        config=SchedulerConfig(),
    )


class TestCalendarQuery:
    """Test TA-0031: Calendar API returns jobs in date range."""

    def test_list_jobs_in_range_filtering(
        self,
        service: SchedulerService,
        repo: MockPublishJobRepo,
    ) -> None:
        """Only jobs within start/end range are returned."""
        base_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        
        # Create jobs at different times
        times = [
            base_time - timedelta(days=1),  # Before
            base_time,                      # Start
            base_time + timedelta(hours=12), # Middle
            base_time + timedelta(days=1),   # End
            base_time + timedelta(days=2),   # After
        ]
        
        jobs = []
        for t in times:
            job = create_publish_job(uuid4(), t)
            repo.save(job)
            jobs.append(job)

        # Range inclusive of start and end
        start = base_time
        end = base_time + timedelta(days=1)
        
        results = service.list_jobs_in_range(start, end)
        
        ids = [j.id for j in results]
        
        assert len(ids) == 3
        assert jobs[0].id not in ids # Before
        assert jobs[1].id in ids     # Start
        assert jobs[2].id in ids     # Middle
        assert jobs[3].id in ids     # End
        assert jobs[4].id not in ids # After

    def test_list_jobs_in_range_status_filter(
        self,
        service: SchedulerService,
        repo: MockPublishJobRepo,
    ) -> None:
        """Filter jobs by status list."""
        base_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        
        # Create jobs with different statuses
        statuses = ["queued", "running", "succeeded", "failed"]
        for status in statuses:
            job = create_publish_job(uuid4(), base_time)
            # Manually set status since create makes them "queued"
            # We need to hack the frozen dataclass or use the repo's internal dict
            # since it's a mock. The repo mock saves the job passed in.
            # In real code we can't mutate frozen, but for test setup we can
            # recreate or mock behavior. Implementation uses replace() often.
            # Note: src/core/entities.py has `frozen=False` explicitly set,
            # so mutation is allowed.
            job.status = status
            repo.save(job)

        start = base_time - timedelta(hours=1)
        end = base_time + timedelta(hours=1)
        
        # Filter for "queued" and "running"
        results = service.list_jobs_in_range(start, end, statuses=["queued", "running"])
        
        assert len(results) == 2
        assert all(j.status in ("queued", "running") for j in results)

    def test_list_jobs_in_range_sorting(
        self,
        service: SchedulerService,
        repo: MockPublishJobRepo,
    ) -> None:
        """Results are sorted by publish_at_utc."""
        base_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        
        # Create unsorted
        t1 = base_time + timedelta(hours=2)
        t2 = base_time
        t3 = base_time + timedelta(hours=1)
        
        for t in [t1, t2, t3]:
            job = create_publish_job(uuid4(), t)
            repo.save(job)
            
        results = service.list_jobs_in_range(base_time, base_time + timedelta(hours=3))
        
        assert len(results) == 3
        assert results[0].publish_at_utc == t2
        assert results[1].publish_at_utc == t3
        assert results[2].publish_at_utc == t1
