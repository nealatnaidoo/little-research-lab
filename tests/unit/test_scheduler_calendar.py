"""
Tests for Scheduler Calendar functionality (TA-0031).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.components.scheduler import SchedulerService
from src.components.scheduler._impl import create_publish_job
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
            # We need to hack the frozen dataclass or just use the repo's internal dict since it's a mock
            # But the repo mock saves the job passed in. 
            # In real code we can't mutate frozen, but for test setup of mock repo we can just recreate or mock behavior.
            # However implementation uses replace() often.
            # Let's verify `create_publish_job` returns mutable? No, dataclass(frozen=True).
            # The test_scheduler.py uses `job.status = "running"` which implies it might NOT be frozen in the implementation being tested?
            # Let's check _impl.py lines 27-28 "from src.core.entities import PublishJob".
            # Check src/core/entities.py... step 1162 says `frozen=False` was explicitly set!
            # So mutation is allowed.
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
