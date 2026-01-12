"""
TA-0105: Job Runner adapter tests.

Verifies that the job runner correctly claims, executes, and tracks jobs.
Tests idempotency, retry logic, and scheduler behavior.

Spec refs: P4, E5, D-0010
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from src.adapters.dev_jobs import (
    DevJobExecutor,
    DevJobRunner,
    DevJobScheduler,
    create_dev_job_runner,
    create_dev_scheduler,
)
from src.core.entities import PublishJob
from src.core.ports.jobs import JobStatus


class MockJobRepo:
    """Mock PublishJobRepo for testing."""

    def __init__(self) -> None:
        self.jobs: dict[UUID, PublishJob] = {}
        self._claimed: set[UUID] = set()

    def add(self, job: PublishJob) -> PublishJob:
        """Add a job to the mock repo."""
        self.jobs[job.id] = job
        return job

    def get(self, job_id: UUID) -> PublishJob | None:
        return self.jobs.get(job_id)

    def save(self, job: PublishJob) -> PublishJob:
        """Save or update job."""
        self.jobs[job.id] = job
        return job

    def claim_next_runnable(self, worker_id: str, now_utc: datetime) -> PublishJob | None:
        """Claim next runnable job (queued/retry_wait and publish_at <= now)."""
        # Normalize to naive datetime for comparison (all times are UTC)
        now_naive = now_utc.replace(tzinfo=None) if now_utc.tzinfo else now_utc

        for job in sorted(self.jobs.values(), key=lambda j: j.publish_at_utc):
            if job.id in self._claimed:
                continue
            if job.status not in ("queued", "retry_wait"):
                continue

            publish_naive = job.publish_at_utc
            if publish_naive.tzinfo:
                publish_naive = publish_naive.replace(tzinfo=None)

            if job.status == "retry_wait" and job.next_retry_at:
                retry_naive = job.next_retry_at
                if retry_naive.tzinfo:
                    retry_naive = retry_naive.replace(tzinfo=None)
                if retry_naive > now_naive:
                    continue

            if publish_naive > now_naive:
                continue

            # Claim the job
            self._claimed.add(job.id)
            job.status = "running"
            job.claimed_by = worker_id
            job.updated_at = now_utc
            return job

        return None

    def get_by_idempotency_key(
        self, content_id: UUID, publish_at_utc: datetime
    ) -> PublishJob | None:
        for job in self.jobs.values():
            if job.content_id == content_id and job.publish_at_utc == publish_at_utc:
                return job
        return None

    def create_if_not_exists(self, job: PublishJob) -> tuple[PublishJob, bool]:
        existing = self.get_by_idempotency_key(job.content_id, job.publish_at_utc)
        if existing:
            return existing, False
        self.jobs[job.id] = job
        return job, True


@pytest.fixture
def mock_repo() -> MockJobRepo:
    """Create a mock job repository."""
    return MockJobRepo()


@pytest.fixture
def now() -> datetime:
    """Fixed 'now' time for testing."""
    return datetime(2026, 6, 15, 12, 0, 0)


def create_test_job(
    publish_at: datetime,
    status: str = "queued",
    content_id: UUID | None = None,
) -> PublishJob:
    """Helper to create test jobs."""
    return PublishJob(
        id=uuid4(),
        content_id=content_id or uuid4(),
        publish_at_utc=publish_at,
        status=status,  # type: ignore[arg-type]
    )


class TestJobClaiming:
    """TA-0105: Job claiming tests."""

    def test_claim_next_runnable_job(self, mock_repo: MockJobRepo, now: datetime) -> None:
        """Claim returns the next job due for execution."""
        job = create_test_job(now - timedelta(minutes=5))
        mock_repo.add(job)

        runner = DevJobRunner(mock_repo)
        claimed = runner.claim_next_job("worker-1", now)

        assert claimed is not None
        assert claimed.id == job.id
        assert claimed.status == "running"
        assert claimed.claimed_by == "worker-1"

    def test_claim_returns_none_when_no_jobs(self, mock_repo: MockJobRepo, now: datetime) -> None:
        """Claim returns None when no jobs are runnable."""
        runner = DevJobRunner(mock_repo)
        claimed = runner.claim_next_job("worker-1", now)

        assert claimed is None

    def test_claim_skips_future_jobs(self, mock_repo: MockJobRepo, now: datetime) -> None:
        """Jobs scheduled for the future are not claimed."""
        future_job = create_test_job(now + timedelta(hours=1))
        mock_repo.add(future_job)

        runner = DevJobRunner(mock_repo)
        claimed = runner.claim_next_job("worker-1", now)

        assert claimed is None

    def test_claim_skips_already_running_jobs(self, mock_repo: MockJobRepo, now: datetime) -> None:
        """Jobs already being processed are not claimed again."""
        job = create_test_job(now - timedelta(minutes=5), status="running")
        mock_repo.add(job)

        runner = DevJobRunner(mock_repo)
        claimed = runner.claim_next_job("worker-1", now)

        assert claimed is None

    def test_claim_picks_oldest_first(self, mock_repo: MockJobRepo, now: datetime) -> None:
        """Jobs are claimed in order of publish_at_utc."""
        older = create_test_job(now - timedelta(hours=2))
        newer = create_test_job(now - timedelta(hours=1))
        mock_repo.add(newer)
        mock_repo.add(older)

        runner = DevJobRunner(mock_repo)
        claimed = runner.claim_next_job("worker-1", now)

        assert claimed is not None
        assert claimed.id == older.id

    def test_job_cannot_be_claimed_twice(self, mock_repo: MockJobRepo, now: datetime) -> None:
        """Same job cannot be claimed by multiple workers (idempotency)."""
        job = create_test_job(now - timedelta(minutes=5))
        mock_repo.add(job)

        runner = DevJobRunner(mock_repo)

        # First worker claims
        claimed1 = runner.claim_next_job("worker-1", now)
        assert claimed1 is not None

        # Second worker gets nothing
        claimed2 = runner.claim_next_job("worker-2", now)
        assert claimed2 is None


class TestJobExecution:
    """TA-0105: Job execution tests."""

    def test_execute_success(self, now: datetime) -> None:
        """Successful execution returns SUCCESS status."""
        job = create_test_job(now)

        def success_callback(j: PublishJob) -> bool:
            return True

        executor = DevJobExecutor(success_callback)
        result = executor.execute(job)

        assert result.status == JobStatus.SUCCESS
        assert result.job_id == job.id
        assert result.execution_time_ms >= 0

    def test_execute_failure_callback_returns_false(self, now: datetime) -> None:
        """Callback returning False results in FAILURE status."""
        job = create_test_job(now)

        def fail_callback(j: PublishJob) -> bool:
            return False

        executor = DevJobExecutor(fail_callback)
        result = executor.execute(job)

        assert result.status == JobStatus.FAILURE
        assert result.error is not None

    def test_execute_failure_callback_raises(self, now: datetime) -> None:
        """Exception in callback results in FAILURE status."""
        job = create_test_job(now)

        def raise_callback(j: PublishJob) -> bool:
            raise ValueError("Simulated error")

        executor = DevJobExecutor(raise_callback)
        result = executor.execute(job)

        assert result.status == JobStatus.FAILURE
        assert "Simulated error" in (result.error or "")


class TestJobRunner:
    """TA-0105: Job runner integration tests."""

    def test_run_due_jobs_processes_all_due(self, mock_repo: MockJobRepo, now: datetime) -> None:
        """run_due_jobs processes all jobs that are due."""
        job1 = create_test_job(now - timedelta(minutes=10))
        job2 = create_test_job(now - timedelta(minutes=5))
        mock_repo.add(job1)
        mock_repo.add(job2)

        runner = DevJobRunner(mock_repo)
        result = runner.run_due_jobs("worker-1", now, max_jobs=10)

        assert result.total_processed == 2
        assert result.succeeded == 2
        assert result.failed == 0

    def test_run_due_jobs_respects_max_jobs(self, mock_repo: MockJobRepo, now: datetime) -> None:
        """run_due_jobs respects max_jobs limit."""
        for i in range(5):
            mock_repo.add(create_test_job(now - timedelta(minutes=i + 1)))

        runner = DevJobRunner(mock_repo)
        result = runner.run_due_jobs("worker-1", now, max_jobs=2)

        assert result.total_processed == 2

    def test_run_due_jobs_returns_no_jobs_result(
        self, mock_repo: MockJobRepo, now: datetime
    ) -> None:
        """run_due_jobs returns NO_JOBS when nothing to process."""
        runner = DevJobRunner(mock_repo)
        result = runner.run_due_jobs("worker-1", now)

        assert result.total_processed == 0
        assert len(result.results) == 1
        assert result.results[0].status == JobStatus.NO_JOBS

    def test_mark_success_updates_job(self, mock_repo: MockJobRepo, now: datetime) -> None:
        """mark_success updates job status and timestamps."""
        job = create_test_job(now)
        mock_repo.add(job)

        runner = DevJobRunner(mock_repo)
        runner.mark_success(job, now)

        updated = mock_repo.get(job.id)
        assert updated is not None
        assert updated.status == "succeeded"
        assert updated.completed_at == now
        assert updated.actual_publish_at == now

    def test_mark_failure_schedules_retry(self, mock_repo: MockJobRepo, now: datetime) -> None:
        """mark_failure with retry=True schedules a retry."""
        job = create_test_job(now)
        job.attempts = 1
        mock_repo.add(job)

        runner = DevJobRunner(mock_repo, retry_delay_seconds=120)
        runner.mark_failure(job, "Test error", retry=True)

        updated = mock_repo.get(job.id)
        assert updated is not None
        assert updated.status == "retry_wait"
        assert updated.next_retry_at is not None
        assert updated.error_message == "Test error"

    def test_mark_failure_no_retry_after_max_attempts(
        self, mock_repo: MockJobRepo, now: datetime
    ) -> None:
        """mark_failure marks as failed after max attempts."""
        job = create_test_job(now)
        job.attempts = 3
        mock_repo.add(job)

        runner = DevJobRunner(mock_repo, max_attempts=3)
        runner.mark_failure(job, "Final error", retry=True)

        updated = mock_repo.get(job.id)
        assert updated is not None
        assert updated.status == "failed"
        assert updated.completed_at is not None


class TestJobScheduler:
    """TA-0105: Scheduler tests."""

    def test_scheduler_start_stop(self, mock_repo: MockJobRepo) -> None:
        """Scheduler can be started and stopped."""
        runner = DevJobRunner(mock_repo)
        scheduler = DevJobScheduler(runner, poll_interval_seconds=10.0)

        assert scheduler.is_running is False

        scheduler.start()
        assert scheduler.is_running is True

        scheduler.stop()
        assert scheduler.is_running is False

    def test_scheduler_trigger_now(self, mock_repo: MockJobRepo) -> None:
        """trigger_now immediately processes due jobs."""
        from datetime import UTC

        # Use real current time since trigger_now uses datetime.utcnow()
        real_now = datetime.now(UTC).replace(tzinfo=None)
        job = create_test_job(real_now - timedelta(minutes=5))
        mock_repo.add(job)

        runner = DevJobRunner(mock_repo)
        scheduler = DevJobScheduler(runner)

        result = scheduler.trigger_now()

        assert result.total_processed == 1
        assert result.succeeded == 1

    def test_scheduler_double_start_is_noop(self, mock_repo: MockJobRepo) -> None:
        """Calling start twice doesn't create multiple threads."""
        runner = DevJobRunner(mock_repo)
        scheduler = DevJobScheduler(runner, poll_interval_seconds=10.0)

        scheduler.start()
        scheduler.start()  # Second call should be no-op

        assert scheduler.is_running is True

        scheduler.stop()


class TestIdempotency:
    """TA-0105: Idempotency tests (R3: at-most-once per idempotency key)."""

    def test_create_if_not_exists_prevents_duplicates(
        self, mock_repo: MockJobRepo, now: datetime
    ) -> None:
        """Same content_id + publish_at creates only one job."""
        content_id = uuid4()

        job1 = PublishJob(
            content_id=content_id,
            publish_at_utc=now,
        )
        job2 = PublishJob(
            content_id=content_id,
            publish_at_utc=now,
        )

        result1, created1 = mock_repo.create_if_not_exists(job1)
        result2, created2 = mock_repo.create_if_not_exists(job2)

        assert created1 is True
        assert created2 is False
        assert result1.id == result2.id

    def test_different_publish_times_are_separate_jobs(
        self, mock_repo: MockJobRepo, now: datetime
    ) -> None:
        """Same content but different times creates separate jobs."""
        content_id = uuid4()

        job1 = PublishJob(
            content_id=content_id,
            publish_at_utc=now,
        )
        job2 = PublishJob(
            content_id=content_id,
            publish_at_utc=now + timedelta(hours=1),
        )

        result1, created1 = mock_repo.create_if_not_exists(job1)
        result2, created2 = mock_repo.create_if_not_exists(job2)

        assert created1 is True
        assert created2 is True
        assert result1.id != result2.id


class TestFactoryFunctions:
    """Factory function tests."""

    def test_create_dev_job_runner(self, mock_repo: MockJobRepo) -> None:
        """create_dev_job_runner creates configured runner."""
        from datetime import UTC

        published: list[UUID] = []

        def callback(job: PublishJob) -> bool:
            published.append(job.content_id)
            return True

        runner = create_dev_job_runner(mock_repo, callback)

        # Use current time minus 1 minute (naive for PublishJob)
        real_now = datetime.now(UTC).replace(tzinfo=None)
        job = create_test_job(real_now - timedelta(minutes=1))
        mock_repo.add(job)

        runner.run_due_jobs()

        assert job.content_id in published

    def test_create_dev_scheduler(self, mock_repo: MockJobRepo) -> None:
        """create_dev_scheduler creates configured scheduler."""
        runner = create_dev_job_runner(mock_repo)
        scheduler = create_dev_scheduler(runner, poll_interval_seconds=5.0)

        assert scheduler._poll_interval == 5.0
        assert scheduler.is_running is False
