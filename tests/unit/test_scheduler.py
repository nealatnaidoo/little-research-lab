"""
Tests for SchedulerService (E5.2).

Test assertions:
- TA-0028: PublishJob create with idempotency
- TA-0029: Job claiming and execution
- TA-0030: Retry/backoff behavior
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from src.core.services.scheduler import (
    PublishJob,
    SchedulerConfig,
    SchedulerService,
    calculate_next_retry,
    check_idempotency,
    create_publish_job,
)

# --- Mock Implementations ---


@dataclass
class MockPublishJobRepo:
    """In-memory publish job repository for testing."""

    jobs: dict[UUID, PublishJob] = field(default_factory=dict)
    claimed_jobs: set[UUID] = field(default_factory=set)

    def get_by_id(self, job_id: UUID) -> PublishJob | None:
        return self.jobs.get(job_id)

    def get_by_idempotency_key(
        self,
        content_id: UUID,
        publish_at_utc: datetime,
    ) -> PublishJob | None:
        for job in self.jobs.values():
            if job.content_id == content_id and job.publish_at_utc == publish_at_utc:
                return job
        return None

    def save(self, job: PublishJob) -> PublishJob:
        self.jobs[job.id] = job
        return job

    def delete(self, job_id: UUID) -> None:
        self.jobs.pop(job_id, None)

    def list_due_jobs(
        self,
        now_utc: datetime,
        limit: int = 10,
    ) -> list[PublishJob]:
        due = []
        for job in self.jobs.values():
            if job.status == "queued" and job.publish_at_utc <= now_utc:
                due.append(job)
            elif job.status == "retry_wait":
                if job.next_retry_at and job.next_retry_at <= now_utc:
                    due.append(job)
        return due[:limit]

    def claim_job(
        self,
        job_id: UUID,
        worker_id: str,
        now_utc: datetime,
    ) -> PublishJob | None:
        if job_id in self.claimed_jobs:
            return None

        job = self.jobs.get(job_id)
        if job and job.status in ("queued", "retry_wait"):
            self.claimed_jobs.add(job_id)
            job.status = "running"
            job.claimed_by = worker_id
            job.updated_at = now_utc
            return job
        return None


@dataclass
class MockTimePort:
    """Mock time port for testing."""

    current_time: datetime = field(
        default_factory=lambda: datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    )

    def now_utc(self) -> datetime:
        return self.current_time

    def is_past_or_now(self, utc_dt: datetime) -> bool:
        return utc_dt <= self.current_time

    def is_future(self, utc_dt: datetime, grace_seconds: int = 0) -> bool:
        threshold = self.current_time - timedelta(seconds=grace_seconds)
        return utc_dt > threshold

    def advance(self, seconds: int) -> None:
        """Advance time for testing."""
        self.current_time += timedelta(seconds=seconds)


@dataclass
class MockPublisher:
    """Mock content publisher for testing."""

    should_succeed: bool = True
    publish_calls: list[UUID] = field(default_factory=list)
    error_message: str = "Simulated failure"

    def publish(self, content_id: UUID) -> tuple[bool, str | None]:
        self.publish_calls.append(content_id)
        if self.should_succeed:
            return True, None
        return False, self.error_message


# --- Fixtures ---


@pytest.fixture
def repo() -> MockPublishJobRepo:
    return MockPublishJobRepo()


@pytest.fixture
def time_port() -> MockTimePort:
    return MockTimePort()


@pytest.fixture
def publisher() -> MockPublisher:
    return MockPublisher()


@pytest.fixture
def config() -> SchedulerConfig:
    return SchedulerConfig()


@pytest.fixture
def service(
    repo: MockPublishJobRepo,
    time_port: MockTimePort,
    publisher: MockPublisher,
    config: SchedulerConfig,
) -> SchedulerService:
    return SchedulerService(
        repo=repo,
        publisher=publisher,
        time_port=time_port,
        config=config,
    )


# --- TA-0028: Job Creation with Idempotency ---


class TestJobCreation:
    """Test TA-0028: PublishJob creation with idempotency."""

    def test_create_job_success(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
    ) -> None:
        """Successfully create a publish job."""
        content_id = uuid4()
        publish_at = time_port.now_utc() + timedelta(hours=1)

        job, errors = service.schedule(content_id, publish_at)

        assert job is not None
        assert len(errors) == 0
        assert job.content_id == content_id
        assert job.publish_at_utc == publish_at
        assert job.status == "queued"
        assert job.attempts == 0

    def test_create_job_past_time_rejected(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
    ) -> None:
        """Reject scheduling in the past."""
        content_id = uuid4()
        publish_at = time_port.now_utc() - timedelta(hours=1)

        job, errors = service.schedule(content_id, publish_at)

        assert job is None
        assert len(errors) > 0
        assert any(e.code == "publish_time_past" for e in errors)

    def test_create_job_with_grace_period(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
        config: SchedulerConfig,
    ) -> None:
        """Accept scheduling within grace period."""
        content_id = uuid4()
        # Just barely in the past but within grace
        publish_at = time_port.now_utc() - timedelta(seconds=config.publish_grace_seconds - 10)

        job, errors = service.schedule(content_id, publish_at)

        assert job is not None
        assert len(errors) == 0

    def test_idempotency_returns_existing_job(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
    ) -> None:
        """Same content_id + publish_at returns existing job."""
        content_id = uuid4()
        publish_at = time_port.now_utc() + timedelta(hours=1)

        # Create first job
        job1, _ = service.schedule(content_id, publish_at)
        assert job1 is not None

        # Try to create again - should return same job
        job2, errors = service.schedule(content_id, publish_at)

        assert job2 is not None
        assert len(errors) == 0
        assert job2.id == job1.id

    def test_different_times_create_different_jobs(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
    ) -> None:
        """Different publish times create different jobs."""
        content_id = uuid4()
        publish_at_1 = time_port.now_utc() + timedelta(hours=1)
        publish_at_2 = time_port.now_utc() + timedelta(hours=2)

        job1, _ = service.schedule(content_id, publish_at_1)
        job2, _ = service.schedule(content_id, publish_at_2)

        assert job1 is not None
        assert job2 is not None
        assert job1.id != job2.id

    def test_unschedule_queued_job(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
    ) -> None:
        """Can unschedule a queued job."""
        content_id = uuid4()
        publish_at = time_port.now_utc() + timedelta(hours=1)

        job, _ = service.schedule(content_id, publish_at)
        assert job is not None

        success, errors = service.unschedule(job.id)

        assert success is True
        assert len(errors) == 0
        assert service.get_job(job.id) is None

    def test_unschedule_running_job_rejected(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
        repo: MockPublishJobRepo,
    ) -> None:
        """Cannot unschedule a running job."""
        content_id = uuid4()
        publish_at = time_port.now_utc() + timedelta(hours=1)

        job, _ = service.schedule(content_id, publish_at)
        assert job is not None

        # Manually set to running
        job.status = "running"
        repo.save(job)

        success, errors = service.unschedule(job.id)

        assert success is False
        assert any(e.code == "cannot_cancel" for e in errors)


# --- TA-0029: Job Claiming and Execution ---


class TestJobClaiming:
    """Test TA-0029: Job claiming and execution."""

    def test_claim_due_job(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
    ) -> None:
        """Can claim a job that is due."""
        content_id = uuid4()
        publish_at = time_port.now_utc()  # Due now

        job, _ = service.schedule(content_id, publish_at)
        assert job is not None

        claimed = service.claim_next("worker-1")

        assert claimed is not None
        assert claimed.id == job.id
        assert claimed.status == "running"
        assert claimed.claimed_by == "worker-1"

    def test_claim_future_job_rejected(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
    ) -> None:
        """Cannot claim a job that is not yet due."""
        content_id = uuid4()
        publish_at = time_port.now_utc() + timedelta(hours=1)

        job, _ = service.schedule(content_id, publish_at)
        assert job is not None

        claimed = service.claim_next("worker-1")

        assert claimed is None

    def test_double_claim_prevented(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
        repo: MockPublishJobRepo,
    ) -> None:
        """Same job cannot be claimed twice."""
        content_id = uuid4()
        publish_at = time_port.now_utc()

        job, _ = service.schedule(content_id, publish_at)
        assert job is not None

        claimed1 = service.claim_next("worker-1")
        claimed2 = service.claim_next("worker-2")

        assert claimed1 is not None
        assert claimed2 is None  # Already claimed

    def test_execute_job_success(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
        publisher: MockPublisher,
    ) -> None:
        """Successfully execute a claimed job."""
        content_id = uuid4()
        publish_at = time_port.now_utc()

        job, _ = service.schedule(content_id, publish_at)
        claimed = service.claim_next("worker-1")
        assert claimed is not None

        result = service.execute_job(claimed)

        assert result.success is True
        assert result.actual_publish_at is not None
        assert content_id in publisher.publish_calls

        # Check job state
        updated = service.get_job(claimed.id)
        assert updated is not None
        assert updated.status == "succeeded"
        assert updated.actual_publish_at is not None

    def test_execute_job_failure(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
        publisher: MockPublisher,
    ) -> None:
        """Handle job execution failure."""
        publisher.should_succeed = False
        content_id = uuid4()
        publish_at = time_port.now_utc()

        job, _ = service.schedule(content_id, publish_at)
        claimed = service.claim_next("worker-1")
        assert claimed is not None

        result = service.execute_job(claimed)

        assert result.success is False
        assert "retry" in result.message.lower() or "failed" in result.message.lower()

    def test_never_publish_early(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
        repo: MockPublishJobRepo,
    ) -> None:
        """R3: Jobs never execute before target time."""
        content_id = uuid4()
        # Schedule for 1 hour in future
        publish_at = time_port.now_utc() + timedelta(hours=1)

        job, _ = service.schedule(content_id, publish_at)
        assert job is not None

        # Manually make it claimable by changing status in repo
        job.status = "queued"
        repo.save(job)

        # Try to claim - should fail due to never_publish_early
        claimed = service.claim_next("worker-1")
        assert claimed is None


# --- TA-0030: Retry/Backoff Behavior ---


class TestRetryBackoff:
    """Test TA-0030: Retry and backoff behavior."""

    def test_calculate_next_retry_first_attempt(self) -> None:
        """First failure (attempts=1) uses first backoff value."""
        now = datetime.now(UTC)
        config = SchedulerConfig(backoff_seconds=(5, 15, 60))

        # After first failure, attempts=1, use backoff[0]=5
        next_retry = calculate_next_retry(1, now, config)

        assert next_retry is not None
        expected = now + timedelta(seconds=5)
        assert next_retry == expected

    def test_calculate_next_retry_progressive(self) -> None:
        """Backoff increases with each attempt."""
        now = datetime.now(UTC)
        config = SchedulerConfig(backoff_seconds=(5, 15, 60, 300))

        # attempts=1 uses backoff[0]=5
        # attempts=2 uses backoff[1]=15
        # attempts=3 uses backoff[2]=60
        retry_1 = calculate_next_retry(1, now, config)
        retry_2 = calculate_next_retry(2, now, config)
        retry_3 = calculate_next_retry(3, now, config)

        assert retry_1 == now + timedelta(seconds=5)
        assert retry_2 == now + timedelta(seconds=15)
        assert retry_3 == now + timedelta(seconds=60)

    def test_calculate_next_retry_max_backoff(self) -> None:
        """Uses last backoff value when attempts exceed array length."""
        now = datetime.now(UTC)
        config = SchedulerConfig(backoff_seconds=(5, 15, 60))

        # Default max_attempts is 10, so attempts=10 returns None
        assert calculate_next_retry(10, now, config) is None

        # With higher max_attempts, attempts=10 should use last backoff
        config_high = SchedulerConfig(backoff_seconds=(5, 15, 60), max_attempts=20)
        retry = calculate_next_retry(10, now, config_high)
        assert retry == now + timedelta(seconds=60)

    def test_calculate_next_retry_max_attempts(self) -> None:
        """Returns None when max attempts reached."""
        now = datetime.now(UTC)
        config = SchedulerConfig(max_attempts=3)

        # At max_attempts, returns None
        retry = calculate_next_retry(3, now, config)
        assert retry is None

        # Below max_attempts, returns retry time
        retry_before = calculate_next_retry(2, now, config)
        assert retry_before is not None

    def test_failed_job_enters_retry_wait(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
        publisher: MockPublisher,
    ) -> None:
        """Failed job transitions to retry_wait with scheduled retry."""
        publisher.should_succeed = False
        content_id = uuid4()
        publish_at = time_port.now_utc()

        job, _ = service.schedule(content_id, publish_at)
        claimed = service.claim_next("worker-1")
        assert claimed is not None

        result = service.execute_job(claimed)

        assert result.success is False

        updated = service.get_job(claimed.id)
        assert updated is not None
        assert updated.status == "retry_wait"
        assert updated.next_retry_at is not None
        assert updated.attempts == 1

    def test_retry_job_becomes_claimable(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
        publisher: MockPublisher,
    ) -> None:
        """Retry_wait job becomes claimable after retry time."""
        publisher.should_succeed = False
        content_id = uuid4()
        publish_at = time_port.now_utc()

        job, _ = service.schedule(content_id, publish_at)
        claimed = service.claim_next("worker-1")
        assert claimed is not None

        # First execution fails
        service.execute_job(claimed)

        updated = service.get_job(claimed.id)
        assert updated is not None
        assert updated.status == "retry_wait"

        # Advance time past retry (first retry uses backoff_seconds[0] = 5s)
        time_port.advance(seconds=10)

        # Reset claim state for retry
        updated.claimed_by = None
        service._repo.save(updated)
        service._repo.claimed_jobs.discard(updated.id)

        # Now should be claimable
        publisher.should_succeed = True
        reclaimed = service.claim_next("worker-2")
        assert reclaimed is not None
        assert reclaimed.id == claimed.id

    def test_max_attempts_leads_to_failed(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
        publisher: MockPublisher,
        repo: MockPublishJobRepo,
    ) -> None:
        """Job fails permanently after max attempts."""
        publisher.should_succeed = False
        config = SchedulerConfig(max_attempts=2, backoff_seconds=(1,))
        service = SchedulerService(
            repo=repo,
            publisher=publisher,
            time_port=time_port,
            config=config,
        )

        content_id = uuid4()
        publish_at = time_port.now_utc()

        job, _ = service.schedule(content_id, publish_at)

        # First attempt
        claimed = service.claim_next("worker-1")
        assert claimed is not None
        service.execute_job(claimed)

        updated = service.get_job(claimed.id)
        assert updated is not None
        assert updated.status == "retry_wait"

        # Advance time and retry
        time_port.advance(seconds=2)
        updated.claimed_by = None
        repo.save(updated)
        repo.claimed_jobs.discard(updated.id)

        claimed2 = service.claim_next("worker-1")
        assert claimed2 is not None
        service.execute_job(claimed2)

        # Should now be failed permanently
        final = service.get_job(claimed.id)
        assert final is not None
        assert final.status == "failed"
        assert final.attempts == 2


# --- Batch Processing ---


class TestBatchProcessing:
    """Test batch job processing."""

    def test_run_due_jobs(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
        publisher: MockPublisher,
    ) -> None:
        """Process multiple due jobs."""
        # Create 3 jobs all due now
        for _ in range(3):
            content_id = uuid4()
            publish_at = time_port.now_utc()
            service.schedule(content_id, publish_at)

        results = service.run_due_jobs("worker-1", max_jobs=10)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert len(publisher.publish_calls) == 3

    def test_run_due_jobs_respects_limit(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
    ) -> None:
        """Respects max_jobs limit."""
        # Create 5 jobs
        for _ in range(5):
            content_id = uuid4()
            publish_at = time_port.now_utc()
            service.schedule(content_id, publish_at)

        results = service.run_due_jobs("worker-1", max_jobs=2)

        assert len(results) == 2


# --- Query Methods ---


class TestQueryMethods:
    """Test query methods."""

    def test_get_job(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
    ) -> None:
        """Get job by ID."""
        content_id = uuid4()
        publish_at = time_port.now_utc() + timedelta(hours=1)

        job, _ = service.schedule(content_id, publish_at)
        assert job is not None

        retrieved = service.get_job(job.id)

        assert retrieved is not None
        assert retrieved.id == job.id

    def test_get_job_for_content(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
    ) -> None:
        """Get job by content and publish time."""
        content_id = uuid4()
        publish_at = time_port.now_utc() + timedelta(hours=1)

        job, _ = service.schedule(content_id, publish_at)
        assert job is not None

        retrieved = service.get_job_for_content(content_id, publish_at)

        assert retrieved is not None
        assert retrieved.id == job.id


# --- Helper Functions ---


class TestHelperFunctions:
    """Test helper functions."""

    def test_check_idempotency_found(self, repo: MockPublishJobRepo) -> None:
        """Find existing job by idempotency key."""
        content_id = uuid4()
        publish_at = datetime.now(UTC)
        job = create_publish_job(content_id, publish_at)
        repo.save(job)

        found = check_idempotency(repo, content_id, publish_at)

        assert found is not None
        assert found.id == job.id

    def test_check_idempotency_not_found(self, repo: MockPublishJobRepo) -> None:
        """No job for idempotency key."""
        content_id = uuid4()
        publish_at = datetime.now(UTC)

        found = check_idempotency(repo, content_id, publish_at)

        assert found is None

    def test_create_publish_job(self) -> None:
        """Create a new publish job."""
        content_id = uuid4()
        publish_at = datetime.now(UTC)

        job = create_publish_job(content_id, publish_at)

        assert job.content_id == content_id
        assert job.publish_at_utc == publish_at
        assert job.status == "queued"
        assert job.attempts == 0


# --- Edge Cases ---


class TestEdgeCases:
    """Test edge cases."""

    def test_reschedule_job(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
    ) -> None:
        """Reschedule a queued job."""
        content_id = uuid4()
        old_time = time_port.now_utc() + timedelta(hours=1)
        new_time = time_port.now_utc() + timedelta(hours=2)

        job, _ = service.schedule(content_id, old_time)
        assert job is not None

        rescheduled, errors = service.reschedule(job.id, new_time)

        assert rescheduled is not None
        assert len(errors) == 0
        assert rescheduled.publish_at_utc == new_time

    def test_reschedule_running_job_rejected(
        self,
        service: SchedulerService,
        time_port: MockTimePort,
        repo: MockPublishJobRepo,
    ) -> None:
        """Cannot reschedule running job."""
        content_id = uuid4()
        publish_at = time_port.now_utc() + timedelta(hours=1)

        job, _ = service.schedule(content_id, publish_at)
        assert job is not None

        job.status = "running"
        repo.save(job)

        new_time = time_port.now_utc() + timedelta(hours=2)
        rescheduled, errors = service.reschedule(job.id, new_time)

        assert rescheduled is None
        assert any(e.code == "cannot_reschedule" for e in errors)

    def test_execute_without_publisher(
        self,
        time_port: MockTimePort,
        repo: MockPublishJobRepo,
    ) -> None:
        """Execute fails gracefully without publisher."""
        service = SchedulerService(repo=repo, time_port=time_port)

        content_id = uuid4()
        publish_at = time_port.now_utc()
        job, _ = service.schedule(content_id, publish_at)
        claimed = service.claim_next("worker-1")
        assert claimed is not None

        result = service.execute_job(claimed)

        assert result.success is False
        assert "publisher" in result.message.lower()
