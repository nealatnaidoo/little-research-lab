"""
v3 Job Runner Adapter Interface (P4).

Protocol-based interface for background job execution.
Supports scheduled publishing via cron-triggered idempotent execution.

Spec refs: P4, E5, D-0010
Test assertions: TA-0105 (job trigger)

Key requirements:
- Jobs are claimed atomically from DB (no double execution)
- Execution is idempotent (same result on retry)
- Worker processes can be stateless (DB provides coordination)

Implementation strategies (per D-0010):
1. Fly.io scheduled machines (production)
2. In-process scheduler (dev/test)
3. External cron trigger

All strategies call the same idempotent publish endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from src.core.entities import PublishJob


class JobStatus(Enum):
    """Job execution result status."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIP = "skip"  # Job already processed (idempotency)
    NO_JOBS = "no_jobs"  # No jobs to process


@dataclass
class JobResult:
    """Result of a job execution attempt."""

    status: JobStatus
    job_id: UUID | None = None
    message: str = ""
    error: str | None = None
    execution_time_ms: int = 0


@dataclass
class BatchResult:
    """Result of processing a batch of jobs."""

    total_processed: int
    succeeded: int
    failed: int
    skipped: int
    results: list[JobResult]


class JobExecutorPort(Protocol):
    """
    Job executor interface.

    Executes a single job and returns the result.
    Implementations should be idempotent.
    """

    def execute(self, job: PublishJob) -> JobResult:
        """
        Execute a publish job.

        Args:
            job: The job to execute

        Returns:
            JobResult with execution outcome

        Notes:
            - Must be idempotent (safe to retry)
            - Should not raise exceptions; return failure status instead
        """
        ...


class JobRunnerPort(Protocol):
    """
    Job runner interface.

    Coordinates job claiming, execution, and status updates.
    Triggered by cron or internal scheduler.
    """

    def run_due_jobs(
        self,
        worker_id: str,
        now_utc: datetime,
        max_jobs: int = 10,
    ) -> BatchResult:
        """
        Process all jobs due at or before now_utc.

        Args:
            worker_id: Unique identifier for this worker instance
            now_utc: Current time (for DST-safe scheduling)
            max_jobs: Maximum jobs to process in one batch

        Returns:
            BatchResult with outcomes for all processed jobs

        Notes:
            - Jobs are claimed atomically (DB transaction)
            - Idempotent: safe to call from multiple workers
            - R3: Never publishes before target time
        """
        ...

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

        Notes:
            - Atomic claim prevents double execution
            - Job status changes to 'running' on claim
        """
        ...

    def mark_success(
        self,
        job: PublishJob,
        actual_publish_at: datetime,
    ) -> None:
        """
        Mark a job as successfully completed.

        Args:
            job: The completed job
            actual_publish_at: When content was actually published
        """
        ...

    def mark_failure(
        self,
        job: PublishJob,
        error: str,
        retry: bool = True,
    ) -> None:
        """
        Mark a job as failed.

        Args:
            job: The failed job
            error: Error message
            retry: Whether to schedule a retry
        """
        ...


class JobSchedulerPort(Protocol):
    """
    Job scheduler interface for triggering runs.

    Abstracts the trigger mechanism (cron, in-process, external).
    """

    def start(self) -> None:
        """
        Start the scheduler.

        For in-process: starts background thread/task.
        For cron: no-op (external trigger).
        """
        ...

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        ...

    def trigger_now(self) -> BatchResult:
        """
        Trigger immediate job processing.

        Useful for testing and manual intervention.
        """
        ...

    @property
    def is_running(self) -> bool:
        """Check if scheduler is active."""
        ...


# Error types


class JobError(Exception):
    """Base exception for job-related errors."""

    pass


class JobClaimError(JobError):
    """Failed to claim a job (already claimed or invalid state)."""

    def __init__(self, job_id: UUID, message: str = "Failed to claim job") -> None:
        self.job_id = job_id
        super().__init__(f"{message}: {job_id}")


class JobExecutionError(JobError):
    """Job execution failed."""

    def __init__(
        self,
        job_id: UUID,
        error: str,
        retriable: bool = True,
    ) -> None:
        self.job_id = job_id
        self.error = error
        self.retriable = retriable
        super().__init__(f"Job {job_id} failed: {error}")
