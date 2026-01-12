"""
Scheduler component input/output models.

Spec refs: E5.2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

# --- Validation Error ---


@dataclass(frozen=True)
class SchedulerValidationError:
    """Scheduler validation error."""

    code: str
    message: str
    job_id: UUID | None = None


# --- Job Status Type ---


JobStatus = Literal["queued", "running", "succeeded", "failed", "retry_wait"]


# --- Job Model ---


@dataclass(frozen=True)
class PublishJob:
    """Publish job for scheduled content."""

    id: UUID
    content_id: UUID
    publish_at_utc: datetime
    status: JobStatus
    attempts: int
    last_attempt_at: datetime | None
    next_retry_at: datetime | None
    completed_at: datetime | None
    actual_publish_at: datetime | None
    error_message: str | None
    claimed_by: str | None
    created_at: datetime
    updated_at: datetime


# --- Execution Result ---


@dataclass(frozen=True)
class ExecutionResult:
    """Result of job execution."""

    success: bool
    job_id: UUID
    message: str
    actual_publish_at: datetime | None = None


# --- Input Models ---


@dataclass(frozen=True)
class SchedulePublishInput:
    """Input for scheduling content for future publish."""

    content_id: UUID
    publish_at_utc: datetime


@dataclass(frozen=True)
class CancelScheduleInput:
    """Input for cancelling a scheduled publish."""

    job_id: UUID


@dataclass(frozen=True)
class RescheduleInput:
    """Input for rescheduling a job."""

    job_id: UUID
    new_publish_at_utc: datetime


@dataclass(frozen=True)
class ProcessDueJobsInput:
    """Input for processing all due publish jobs."""

    worker_id: str
    max_jobs: int = 10


@dataclass(frozen=True)
class GetJobInput:
    """Input for getting a job by ID."""

    job_id: UUID


# --- Output Models ---


@dataclass(frozen=True)
class ScheduleOutput:
    """Output for schedule operation."""

    job: PublishJob | None
    errors: list[SchedulerValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class CancelOutput:
    """Output for cancel operation."""

    cancelled: bool
    errors: list[SchedulerValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class ProcessOutput:
    """Output for process due jobs operation."""

    results: tuple[ExecutionResult, ...]
    errors: list[SchedulerValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class JobOutput:
    """Output for get job operation."""

    job: PublishJob | None
    errors: list[SchedulerValidationError] = field(default_factory=list)
    success: bool = True
