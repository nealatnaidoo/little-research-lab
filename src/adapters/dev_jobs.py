"""
Dev Job Runner Adapter (P4 Implementation).

In-process job runner for development and testing.
Uses DB polling for job claims with synchronous execution.

Spec refs: P4, E5, D-0010, TA-0105
Test assertions: TA-0105 (job trigger)

Production uses Fly.io scheduled machines; this provides
equivalent functionality for local development.

Key behaviors:
- Atomic job claim via DB transaction
- Synchronous execution for predictable testing
- Configurable poll interval for background mode
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from src.core.entities import PublishJob
from src.core.ports.jobs import (
    BatchResult,
    JobResult,
    JobStatus,
)

if TYPE_CHECKING:
    from src.core.ports.db import PublishJobRepoPort

logger = logging.getLogger(__name__)


class DevJobExecutor:
    """
    Dev job executor that delegates to a callback.

    In production, this would call the ContentService to
    transition content from 'scheduled' to 'published'.
    """

    def __init__(
        self,
        publish_callback: Callable[[PublishJob], bool] | None = None,
    ) -> None:
        """
        Initialize executor.

        Args:
            publish_callback: Function to call for publishing.
                             Returns True on success, False on failure.
                             If None, uses a no-op (for testing).
        """
        self._publish_callback = publish_callback or self._default_publish

    def _default_publish(self, job: PublishJob) -> bool:
        """Default no-op publish for testing."""
        logger.info("Dev executor: would publish content %s", job.content_id)
        return True

    def execute(self, job: PublishJob) -> JobResult:
        """
        Execute a publish job.

        Args:
            job: The job to execute

        Returns:
            JobResult with execution outcome
        """
        start_time = time.monotonic()

        try:
            success = self._publish_callback(job)
            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            if success:
                return JobResult(
                    status=JobStatus.SUCCESS,
                    job_id=job.id,
                    message=f"Published content {job.content_id}",
                    execution_time_ms=elapsed_ms,
                )
            else:
                return JobResult(
                    status=JobStatus.FAILURE,
                    job_id=job.id,
                    message=f"Failed to publish content {job.content_id}",
                    error="Publish callback returned False",
                    execution_time_ms=elapsed_ms,
                )

        except Exception as e:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return JobResult(
                status=JobStatus.FAILURE,
                job_id=job.id,
                message=f"Exception during publish of {job.content_id}",
                error=str(e),
                execution_time_ms=elapsed_ms,
            )


class DevJobRunner:
    """
    Dev job runner using DB polling.

    Implements JobRunnerPort for local development.
    Uses synchronous execution within transactions.
    """

    def __init__(
        self,
        job_repo: PublishJobRepoPort,
        executor: DevJobExecutor | None = None,
        max_attempts: int = 3,
        retry_delay_seconds: int = 60,
    ) -> None:
        """
        Initialize runner.

        Args:
            job_repo: Repository for PublishJob operations
            executor: Job executor (defaults to DevJobExecutor)
            max_attempts: Maximum execution attempts before marking failed
            retry_delay_seconds: Delay before retry on failure
        """
        self._job_repo = job_repo
        self._executor = executor or DevJobExecutor()
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds
        self._worker_id = f"dev-{uuid4().hex[:8]}"

    def run_due_jobs(
        self,
        worker_id: str | None = None,
        now_utc: datetime | None = None,
        max_jobs: int = 10,
    ) -> BatchResult:
        """
        Process all jobs due at or before now_utc.

        Args:
            worker_id: Worker identifier (defaults to instance ID)
            now_utc: Current time (defaults to now)
            max_jobs: Maximum jobs to process

        Returns:
            BatchResult with all outcomes
        """
        worker_id = worker_id or self._worker_id
        now_utc = now_utc or datetime.now(UTC)

        results: list[JobResult] = []
        succeeded = 0
        failed = 0
        skipped = 0

        for _ in range(max_jobs):
            job = self.claim_next_job(worker_id, now_utc)
            if job is None:
                break

            result = self._execute_and_update(job, now_utc)
            results.append(result)

            if result.status == JobStatus.SUCCESS:
                succeeded += 1
            elif result.status == JobStatus.FAILURE:
                failed += 1
            elif result.status == JobStatus.SKIP:
                skipped += 1

        if not results:
            return BatchResult(
                total_processed=0,
                succeeded=0,
                failed=0,
                skipped=0,
                results=[JobResult(status=JobStatus.NO_JOBS, message="No jobs to process")],
            )

        return BatchResult(
            total_processed=len(results),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            results=results,
        )

    def claim_next_job(
        self,
        worker_id: str,
        now_utc: datetime,
    ) -> PublishJob | None:
        """
        Claim the next runnable job atomically.

        Args:
            worker_id: Unique identifier for this worker
            now_utc: Current time

        Returns:
            Claimed job or None if no jobs available
        """
        return self._job_repo.claim_next_runnable(worker_id, now_utc)

    def mark_success(
        self,
        job: PublishJob,
        actual_publish_at: datetime,
    ) -> None:
        """Mark a job as successfully completed."""
        job.status = "succeeded"
        job.completed_at = actual_publish_at
        job.actual_publish_at = actual_publish_at
        job.updated_at = actual_publish_at
        self._job_repo.save(job)

    def mark_failure(
        self,
        job: PublishJob,
        error: str,
        retry: bool = True,
    ) -> None:
        """Mark a job as failed, optionally scheduling retry."""
        now = datetime.now(UTC)
        job.error_message = error
        job.updated_at = now

        if retry and job.attempts < self._max_attempts:
            job.status = "retry_wait"
            job.next_retry_at = now + timedelta(seconds=self._retry_delay_seconds)
        else:
            job.status = "failed"
            job.completed_at = now

        self._job_repo.save(job)

    def _execute_and_update(
        self,
        job: PublishJob,
        now_utc: datetime,
    ) -> JobResult:
        """Execute a job and update its status."""
        # Increment attempt counter
        job.attempts += 1
        job.last_attempt_at = now_utc
        self._job_repo.save(job)

        # Execute
        result = self._executor.execute(job)

        # Update status based on result
        if result.status == JobStatus.SUCCESS:
            self.mark_success(job, now_utc)
        elif result.status == JobStatus.FAILURE:
            self.mark_failure(job, result.error or "Unknown error")

        return result


class DevJobScheduler:
    """
    Dev job scheduler with background polling.

    Runs a background thread that polls for due jobs
    at a configurable interval.
    """

    def __init__(
        self,
        runner: DevJobRunner,
        poll_interval_seconds: float = 60.0,
    ) -> None:
        """
        Initialize scheduler.

        Args:
            runner: Job runner to use
            poll_interval_seconds: Interval between polls
        """
        self._runner = runner
        self._poll_interval = poll_interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        """Start the background scheduler."""
        if self._running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        self._running = True
        logger.info("Dev scheduler started (poll interval: %.1fs)", self._poll_interval)

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._running:
            return

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        self._running = False
        logger.info("Dev scheduler stopped")

    def trigger_now(self) -> BatchResult:
        """Trigger immediate job processing."""
        return self._runner.run_due_jobs()

    @property
    def is_running(self) -> bool:
        """Check if scheduler is active."""
        return self._running

    def _poll_loop(self) -> None:
        """Background polling loop."""
        while not self._stop_event.wait(timeout=self._poll_interval):
            try:
                result = self._runner.run_due_jobs()
                if result.total_processed > 0:
                    logger.info(
                        "Scheduler processed %d jobs: %d succeeded, %d failed",
                        result.total_processed,
                        result.succeeded,
                        result.failed,
                    )
            except Exception:
                logger.exception("Error in scheduler poll loop")


# Factory functions


def create_dev_job_runner(
    job_repo: PublishJobRepoPort,
    publish_callback: Callable[[PublishJob], bool] | None = None,
) -> DevJobRunner:
    """
    Create a dev job runner.

    Args:
        job_repo: Repository for job operations
        publish_callback: Function to call for publishing

    Returns:
        Configured DevJobRunner
    """
    executor = DevJobExecutor(publish_callback)
    return DevJobRunner(job_repo, executor)


def create_dev_scheduler(
    runner: DevJobRunner,
    poll_interval_seconds: float = 60.0,
) -> DevJobScheduler:
    """
    Create a dev scheduler.

    Args:
        runner: Job runner to use
        poll_interval_seconds: Interval between polls

    Returns:
        Configured DevJobScheduler
    """
    return DevJobScheduler(runner, poll_interval_seconds)
