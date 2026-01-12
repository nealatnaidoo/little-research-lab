"""
SchedulerService (E5.2) - Scheduled publishing job management.

Handles creation, claiming, execution, and retry of publish jobs.

Spec refs: E5.2, TA-0028, TA-0029, TA-0030, R3
Test assertions:
- TA-0028: PublishJob create with idempotency (content_id + publish_at_utc)
- TA-0029: Job claiming and execution
- TA-0030: Retry/backoff behavior

Key behaviors:
- Jobs are idempotent by (content_id, publish_at_utc) key
- Jobs are never executed before target time (R3)
- Workers claim jobs atomically to prevent double execution
- Failed jobs retry with exponential backoff
- DST-safe scheduling via TimePort
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from src.core.entities import PublishJob

# --- Configuration ---


@dataclass(frozen=True)
class SchedulerConfig:
    """Scheduler configuration from rules."""

    # Idempotency key fields
    idempotency_key: tuple[str, ...] = ("content_id", "publish_at_utc")

    # Timing
    never_publish_early: bool = True
    publish_grace_seconds: int = 120
    display_timezone: str = "Europe/London"

    # Retries
    max_attempts: int = 10
    backoff_seconds: tuple[int, ...] = (5, 15, 60, 300, 900, 1800)


DEFAULT_CONFIG = SchedulerConfig()


# --- Errors ---


@dataclass
class SchedulerError:
    """Scheduler operation error."""

    code: str
    message: str
    job_id: UUID | None = None


# --- Job Status ---

JobStatus = str  # "queued" | "running" | "succeeded" | "failed" | "retry_wait"


# --- PublishJob Model (imported at top) ---

# Re-export for mypy
__all__ = [
    "SchedulerConfig",
    "SchedulerError",
    "PublishJob",
    "PublishJobRepoPort",
    "SchedulerService",
    "ExecutionResult",
]

# --- Repository Protocol ---


class PublishJobRepoPort(Protocol):
    """Repository interface for publish jobs."""

    def get_by_id(self, job_id: UUID) -> PublishJob | None:
        """Get job by ID."""
        ...

    def get_by_idempotency_key(
        self,
        content_id: UUID,
        publish_at_utc: datetime,
    ) -> PublishJob | None:
        """Get job by idempotency key."""
        ...

    def save(self, job: PublishJob) -> PublishJob:
        """Save or update job."""
        ...

    def delete(self, job_id: UUID) -> None:
        """Delete job."""
        ...

    def list_due_jobs(
        self,
        now_utc: datetime,
        limit: int = 10,
    ) -> list[PublishJob]:
        """List jobs due for execution (queued or retry_wait, time passed)."""
        ...

    def claim_job(
        self,
        job_id: UUID,
        worker_id: str,
        now_utc: datetime,
    ) -> PublishJob | None:
        """Atomically claim a job. Returns None if already claimed."""
        ...

    def list_in_range(
        self,
        start_utc: datetime,
        end_utc: datetime,
        statuses: list[str] | None = None,
    ) -> list[PublishJob]:
        """List jobs with publish_at in the given date range."""
        ...


class ContentPublisherPort(Protocol):
    """Content publisher interface for executing publishes."""

    def publish(self, content_id: UUID) -> tuple[bool, str | None]:
        """
        Publish content by ID.

        Returns:
            Tuple of (success, error_message)
        """
        ...


class TimePort(Protocol):
    """Time port for DST-safe operations."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...

    def is_past_or_now(self, utc_dt: datetime) -> bool:
        """Check if datetime is at or before now."""
        ...

    def is_future(self, utc_dt: datetime, grace_seconds: int = 0) -> bool:
        """Check if datetime is in the future (with grace)."""
        ...


# --- Backoff Calculation ---


def calculate_next_retry(
    attempts: int,
    now_utc: datetime,
    config: SchedulerConfig = DEFAULT_CONFIG,
) -> datetime | None:
    """
    Calculate next retry time using exponential backoff.

    Args:
        attempts: Current attempt count (after incrementing for this failure)
        now_utc: Current time
        config: Scheduler configuration

    Returns None if max attempts reached.
    """
    if attempts >= config.max_attempts:
        return None

    # Backoff index is attempts-1 since first failure (attempts=1) uses backoff[0]
    backoff_index = min(attempts - 1, len(config.backoff_seconds) - 1)
    backoff_index = max(0, backoff_index)  # Ensure non-negative
    backoff = config.backoff_seconds[backoff_index]

    return now_utc + timedelta(seconds=backoff)


# --- Idempotency Check ---


def check_idempotency(
    repo: PublishJobRepoPort,
    content_id: UUID,
    publish_at_utc: datetime,
) -> PublishJob | None:
    """Check if a job already exists for this idempotency key."""
    return repo.get_by_idempotency_key(content_id, publish_at_utc)


# --- Job Creation ---


def create_publish_job(
    content_id: UUID,
    publish_at_utc: datetime,
    now_utc: datetime | None = None,
) -> PublishJob:
    """Create a new publish job."""
    now = now_utc or datetime.now(UTC)
    return PublishJob(
        id=uuid4(),
        content_id=content_id,
        publish_at_utc=publish_at_utc,
        status="queued",
        attempts=0,
        last_attempt_at=None,
        next_retry_at=None,
        completed_at=None,
        actual_publish_at=None,
        error_message=None,
        claimed_by=None,
        created_at=now,
        updated_at=now,
    )


# --- Execution Result ---


@dataclass
class ExecutionResult:
    """Result of job execution."""

    success: bool
    job_id: UUID
    message: str
    actual_publish_at: datetime | None = None


# --- SchedulerService ---


class SchedulerService:
    """
    Scheduler service (E5.2).

    Manages publish jobs with idempotency and retry logic.
    """

    def __init__(
        self,
        repo: PublishJobRepoPort,
        publisher: ContentPublisherPort | None = None,
        time_port: TimePort | None = None,
        config: SchedulerConfig | None = None,
    ) -> None:
        """Initialize scheduler service."""
        self._repo = repo
        self._publisher = publisher
        self._time = time_port
        self._config = config or DEFAULT_CONFIG

    def _now_utc(self) -> datetime:
        """Get current UTC time."""
        if self._time:
            return self._time.now_utc()
        return datetime.now(UTC)

    def _is_past_or_now(self, dt: datetime) -> bool:
        """Check if time is past or now."""
        if self._time:
            return self._time.is_past_or_now(dt)
        return dt <= self._now_utc()

    def _is_future(self, dt: datetime, grace: int = 0) -> bool:
        """Check if time is in future."""
        if self._time:
            return self._time.is_future(dt, grace)
        if grace:
            return dt > (self._now_utc() - timedelta(seconds=grace))
        return dt > self._now_utc()

    # --- Job Creation (TA-0028) ---

    def schedule(
        self,
        content_id: UUID,
        publish_at_utc: datetime,
    ) -> tuple[PublishJob | None, list[SchedulerError]]:
        """
        Schedule content for publishing (TA-0028).

        Creates a publish job with idempotency check.

        Args:
            content_id: Content to publish
            publish_at_utc: Target publish time (UTC)

        Returns:
            Tuple of (job, errors). Job is None if errors.
        """
        errors: list[SchedulerError] = []
        now = self._now_utc()

        # Validate publish time is in future (with grace period)
        if not self._is_future(publish_at_utc, self._config.publish_grace_seconds):
            errors.append(
                SchedulerError(
                    code="publish_time_past",
                    message="Publish time must be in the future",
                )
            )
            return None, errors

        # Check idempotency - existing job for same key
        existing = check_idempotency(self._repo, content_id, publish_at_utc)
        if existing:
            # Return existing job if still pending
            if existing.status in ("queued", "running", "retry_wait"):
                return existing, []
            # If completed/failed, could create new or return existing
            # For now, return existing to allow inspection
            return existing, []

        # Create new job
        job = create_publish_job(content_id, publish_at_utc, now)
        saved = self._repo.save(job)
        return saved, []

    def unschedule(self, job_id: UUID) -> tuple[bool, list[SchedulerError]]:
        """
        Cancel a scheduled job.

        Only queued jobs can be cancelled.

        Returns:
            Tuple of (success, errors)
        """
        errors: list[SchedulerError] = []

        job = self._repo.get_by_id(job_id)
        if job is None:
            errors.append(
                SchedulerError(
                    code="job_not_found",
                    message=f"Job {job_id} not found",
                    job_id=job_id,
                )
            )
            return False, errors

        if job.status != "queued":
            errors.append(
                SchedulerError(
                    code="cannot_cancel",
                    message=f"Cannot cancel job in '{job.status}' status",
                    job_id=job_id,
                )
            )
            return False, errors

        self._repo.delete(job_id)
        return True, []

    def reschedule(
        self,
        job_id: UUID,
        new_publish_at_utc: datetime,
    ) -> tuple[PublishJob | None, list[SchedulerError]]:
        """
        Reschedule a job to a new time.

        Only queued jobs can be rescheduled.

        Returns:
            Tuple of (updated_job, errors)
        """
        errors: list[SchedulerError] = []

        job = self._repo.get_by_id(job_id)
        if job is None:
            errors.append(
                SchedulerError(
                    code="job_not_found",
                    message=f"Job {job_id} not found",
                    job_id=job_id,
                )
            )
            return None, errors

        if job.status != "queued":
            errors.append(
                SchedulerError(
                    code="cannot_reschedule",
                    message=f"Cannot reschedule job in '{job.status}' status",
                    job_id=job_id,
                )
            )
            return None, errors

        # Validate new time
        if not self._is_future(new_publish_at_utc, self._config.publish_grace_seconds):
            errors.append(
                SchedulerError(
                    code="publish_time_past",
                    message="New publish time must be in the future",
                    job_id=job_id,
                )
            )
            return None, errors

        # Check for collision at new time
        existing = check_idempotency(
            self._repo,
            job.content_id,
            new_publish_at_utc,
        )
        if existing and existing.id != job_id:
            errors.append(
                SchedulerError(
                    code="schedule_conflict",
                    message="Another job already scheduled for this time",
                    job_id=job_id,
                )
            )
            return None, errors

        # Update job
        job.publish_at_utc = new_publish_at_utc
        job.updated_at = self._now_utc()
        saved = self._repo.save(job)
        return saved, []

    # --- Job Claiming (TA-0029) ---

    def claim_next(
        self,
        worker_id: str,
    ) -> PublishJob | None:
        """
        Claim the next available job for execution (TA-0029).

        Atomically claims a job to prevent double execution.

        Args:
            worker_id: Unique identifier for this worker

        Returns:
            Claimed job or None if no jobs available
        """
        now = self._now_utc()

        # Find due jobs
        due_jobs = self._repo.list_due_jobs(now, limit=1)
        if not due_jobs:
            return None

        # Try to claim
        job = due_jobs[0]

        # Verify job is runnable (R3 - never publish early)
        if self._config.never_publish_early:
            if not self._is_past_or_now(job.publish_at_utc):
                return None

        # Atomic claim
        claimed = self._repo.claim_job(job.id, worker_id, now)
        return claimed

    def execute_job(
        self,
        job: PublishJob,
    ) -> ExecutionResult:
        """
        Execute a claimed job (TA-0029).

        Must have a publisher configured.

        Args:
            job: The job to execute

        Returns:
            ExecutionResult with outcome
        """
        if self._publisher is None:
            return ExecutionResult(
                success=False,
                job_id=job.id,
                message="No publisher configured",
            )

        now = self._now_utc()

        # Verify job is in running state
        if job.status != "running":
            return ExecutionResult(
                success=False,
                job_id=job.id,
                message=f"Job not in running state: {job.status}",
            )

        # R3: Never publish early
        if self._config.never_publish_early:
            if not self._is_past_or_now(job.publish_at_utc):
                return ExecutionResult(
                    success=False,
                    job_id=job.id,
                    message="Publish time not yet reached",
                )

        # Execute publish
        success, error = self._publisher.publish(job.content_id)

        if success:
            # Mark succeeded
            job.status = "succeeded"
            job.completed_at = now
            job.actual_publish_at = now
            job.attempts += 1
            job.last_attempt_at = now
            job.updated_at = now
            self._repo.save(job)

            return ExecutionResult(
                success=True,
                job_id=job.id,
                message="Published successfully",
                actual_publish_at=now,
            )
        else:
            # Handle failure with retry
            return self._handle_failure(job, error or "Unknown error")

    def _handle_failure(
        self,
        job: PublishJob,
        error: str,
    ) -> ExecutionResult:
        """Handle job execution failure with retry logic (TA-0030)."""
        now = self._now_utc()

        job.attempts += 1
        job.last_attempt_at = now
        job.error_message = error
        job.updated_at = now

        # Calculate next retry (passes current attempts count)
        next_retry = calculate_next_retry(job.attempts, now, self._config)

        if next_retry:
            # Schedule retry
            job.status = "retry_wait"
            job.next_retry_at = next_retry
            job.claimed_by = None  # Release claim
            self._repo.save(job)

            return ExecutionResult(
                success=False,
                job_id=job.id,
                message=f"Failed, retry scheduled at {next_retry}",
            )
        else:
            # Max attempts reached
            job.status = "failed"
            job.completed_at = now
            job.claimed_by = None
            self._repo.save(job)

            return ExecutionResult(
                success=False,
                job_id=job.id,
                message=f"Failed after {job.attempts} attempts: {error}",
            )

    # --- Batch Processing ---

    def run_due_jobs(
        self,
        worker_id: str,
        max_jobs: int = 10,
    ) -> list[ExecutionResult]:
        """
        Process all due jobs.

        Args:
            worker_id: Worker identifier
            max_jobs: Maximum jobs to process

        Returns:
            List of execution results
        """
        results: list[ExecutionResult] = []

        for _ in range(max_jobs):
            job = self.claim_next(worker_id)
            if job is None:
                break

            result = self.execute_job(job)
            results.append(result)

        return results

    # --- Query Methods ---

    def get_job(self, job_id: UUID) -> PublishJob | None:
        """Get job by ID."""
        return self._repo.get_by_id(job_id)

    def get_job_for_content(
        self,
        content_id: UUID,
        publish_at_utc: datetime,
    ) -> PublishJob | None:
        """Get job by content and publish time."""
        return self._repo.get_by_idempotency_key(content_id, publish_at_utc)

    def get_pending_jobs(
        self,
        limit: int = 100,
    ) -> list[PublishJob]:
        """Get all pending jobs (queued or retry_wait)."""
        # This would need a repo method, for now use list_due with far future
        far_future = self._now_utc() + timedelta(days=365 * 10)
        return self._repo.list_due_jobs(far_future, limit)


# --- Factory ---


def create_scheduler_service(
    repo: PublishJobRepoPort,
    publisher: ContentPublisherPort | None = None,
    time_port: TimePort | None = None,
    config: SchedulerConfig | None = None,
) -> SchedulerService:
    """Create a SchedulerService."""
    return SchedulerService(
        repo=repo,
        publisher=publisher,
        time_port=time_port,
        config=config,
    )
