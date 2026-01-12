"""
Admin Scheduling API Routes (E5.1, E5.2, E5.3).

Provides scheduling endpoints for content publishing and calendar view.

Spec refs: E5.1, E5.2, E5.3, TA-0026, TA-0031, TA-0033
Test assertions:
- TA-0026: Schedule/unschedule content
- TA-0031: Calendar API returns jobs in date range
- TA-0033: Publish now functionality
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.components.scheduler import (
    PublishJob,
    SchedulerConfig,
    SchedulerError,
    SchedulerService,
)

router = APIRouter()


# --- Request/Response Models ---


class ScheduleRequest(BaseModel):
    """Request to schedule content."""

    content_id: UUID
    publish_at_utc: datetime = Field(..., description="Target publish time in UTC")


class RescheduleRequest(BaseModel):
    """Request to reschedule a job."""

    new_publish_at_utc: datetime = Field(..., description="New publish time in UTC")


class JobResponse(BaseModel):
    """Publish job response."""

    id: UUID
    content_id: UUID
    publish_at_utc: datetime
    status: str
    attempts: int
    created_at: datetime
    updated_at: datetime
    next_retry_at: datetime | None = None
    completed_at: datetime | None = None
    actual_publish_at: datetime | None = None
    error_message: str | None = None


class ScheduleErrorResponse(BaseModel):
    """Error response for scheduling operations."""

    code: str
    message: str
    job_id: UUID | None = None


class PublishNowRequest(BaseModel):
    """Request to publish content immediately."""

    content_id: UUID


class PublishNowResponse(BaseModel):
    """Response for publish now operation."""

    success: bool
    message: str
    actual_publish_at: datetime | None = None


class CalendarEvent(BaseModel):
    """A scheduled job as a calendar event (TA-0031)."""

    id: UUID
    content_id: UUID
    title: str  # Job title for calendar display
    start: datetime  # publish_at_utc
    status: str
    is_all_day: bool = False


class CalendarResponse(BaseModel):
    """Calendar API response (TA-0031)."""

    events: list[CalendarEvent]
    start_date: datetime
    end_date: datetime
    total_count: int


# --- Helpers ---


def job_to_response(job: Any) -> JobResponse:
    """Convert PublishJob to response model."""
    return JobResponse(
        id=job.id,
        content_id=job.content_id,
        publish_at_utc=job.publish_at_utc,
        status=job.status,
        attempts=job.attempts,
        created_at=job.created_at,
        updated_at=job.updated_at,
        next_retry_at=job.next_retry_at,
        completed_at=job.completed_at,
        actual_publish_at=job.actual_publish_at,
        error_message=job.error_message,
    )


def errors_to_response(errors: list[SchedulerError]) -> list[ScheduleErrorResponse]:
    """Convert SchedulerErrors to response models."""
    return [
        ScheduleErrorResponse(
            code=e.code,
            message=e.message,
            job_id=e.job_id,
        )
        for e in errors
    ]


def _serialize_errors(errors: list[SchedulerError]) -> list[dict[str, Any]]:
    """Serialize errors for JSON response."""
    return [
        {
            "code": e.code,
            "message": e.message,
            "job_id": str(e.job_id) if e.job_id else None,
        }
        for e in errors
    ]


# --- Mock Dependencies (to be replaced with real DI) ---


class MockPublishJobRepo:
    """In-memory repository for testing."""

    def __init__(self) -> None:
        self.jobs: dict[UUID, PublishJob] = {}
        self.claimed_jobs: set[UUID] = set()

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

    def list_due_jobs(self, now_utc: datetime, limit: int = 10) -> list[PublishJob]:
        due = []
        for job in self.jobs.values():
            if job.status == "queued" and job.publish_at_utc <= now_utc:
                due.append(job)
            elif job.status == "retry_wait":
                if job.next_retry_at and job.next_retry_at <= now_utc:
                    due.append(job)
        return due[:limit]

    def list_in_range(
        self,
        start_utc: datetime,
        end_utc: datetime,
        statuses: list[str] | None = None,
    ) -> list[PublishJob]:
        """List jobs with publish_at in the given date range (TA-0031)."""
        result = []
        for job in self.jobs.values():
            if start_utc <= job.publish_at_utc <= end_utc:
                if statuses is None or job.status in statuses:
                    result.append(job)
        # Sort by publish_at
        result.sort(key=lambda j: j.publish_at_utc)
        return result

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
            updated_job = replace(
                job,
                status="running",
                claimed_by=worker_id,
                updated_at=now_utc,
            )
            self.jobs[job_id] = updated_job
            return updated_job
        return None


class MockPublisher:
    """Mock publisher for testing."""

    def publish(self, content_id: UUID) -> tuple[bool, str | None]:
        return True, None


# Singleton instances for testing
_repo = MockPublishJobRepo()
_publisher = MockPublisher()


def get_scheduler_service() -> SchedulerService:
    """Get scheduler service dependency."""
    # Cast to Any to work around type mismatch between two PublishJob definitions
    # (src.components.scheduler.models.PublishJob vs src.core.entities.PublishJob)
    return SchedulerService(
        repo=cast(Any, _repo),
        publisher=_publisher,
        config=SchedulerConfig(),
    )


# --- Routes ---


@router.post("/schedule", response_model=JobResponse)
def schedule_content(
    request: ScheduleRequest,
    service: SchedulerService = Depends(get_scheduler_service),
) -> Any:
    """
    Schedule content for publishing (TA-0026).

    Creates a publish job with idempotency check.
    """
    job, errors = service.schedule(
        content_id=request.content_id,
        publish_at_utc=request.publish_at_utc,
    )

    if errors:
        raise HTTPException(
            status_code=400,
            detail={"errors": _serialize_errors(errors)},
        )

    if job is None:
        raise HTTPException(status_code=500, detail="Failed to create job")

    return job_to_response(job)


@router.delete("/schedule/{job_id}")
def unschedule_content(
    job_id: UUID,
    service: SchedulerService = Depends(get_scheduler_service),
) -> dict[str, Any]:
    """
    Unschedule (cancel) a publish job (TA-0026).

    Only queued jobs can be cancelled.
    """
    success, errors = service.unschedule(job_id)

    if errors:
        raise HTTPException(
            status_code=400,
            detail={"errors": _serialize_errors(errors)},
        )

    return {"success": success, "job_id": str(job_id)}


@router.put("/schedule/{job_id}", response_model=JobResponse)
def reschedule_content(
    job_id: UUID,
    request: RescheduleRequest,
    service: SchedulerService = Depends(get_scheduler_service),
) -> Any:
    """
    Reschedule a publish job to a new time.

    Only queued jobs can be rescheduled.
    """
    job, errors = service.reschedule(
        job_id=job_id,
        new_publish_at_utc=request.new_publish_at_utc,
    )

    if errors:
        raise HTTPException(
            status_code=400,
            detail={"errors": _serialize_errors(errors)},
        )

    if job is None:
        raise HTTPException(status_code=500, detail="Failed to reschedule job")

    return job_to_response(job)


@router.get("/schedule/{job_id}", response_model=JobResponse)
def get_job(
    job_id: UUID,
    service: SchedulerService = Depends(get_scheduler_service),
) -> Any:
    """Get a publish job by ID."""
    job = service.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_to_response(job)


@router.get("/schedule/content/{content_id}", response_model=list[JobResponse])
def get_jobs_for_content(
    content_id: UUID,
    service: SchedulerService = Depends(get_scheduler_service),
) -> Any:
    """
    Get all scheduled jobs for a content item.

    Returns pending jobs (queued, running, retry_wait).
    """
    # Get pending jobs and filter by content_id
    pending = service.get_pending_jobs(limit=100)
    filtered = [job for job in pending if job.content_id == content_id]
    return [job_to_response(job) for job in filtered]


@router.post("/publish-now", response_model=PublishNowResponse)
def publish_now(
    request: PublishNowRequest,
    service: SchedulerService = Depends(get_scheduler_service),
) -> Any:
    """
    Publish content immediately (TA-0033).

    Creates a job for now and immediately executes it.
    """
    now = datetime.now(UTC)

    # Schedule for now
    job, errors = service.schedule(
        content_id=request.content_id,
        publish_at_utc=now,
    )

    if errors:
        raise HTTPException(
            status_code=400,
            detail={"errors": _serialize_errors(errors)},
        )

    if job is None:
        raise HTTPException(status_code=500, detail="Failed to create job")

    # Claim and execute
    claimed = service.claim_next("publish-now-worker")
    if claimed is None:
        # Job might have been claimed by another worker or already executed
        return PublishNowResponse(
            success=False,
            message="Could not claim job for immediate execution",
        )

    result = service.execute_job(claimed)

    return PublishNowResponse(
        success=result.success,
        message=result.message,
        actual_publish_at=result.actual_publish_at,
    )


@router.post("/run-due-jobs")
def run_due_jobs(
    worker_id: str = "api-worker",
    max_jobs: int = 10,
    service: SchedulerService = Depends(get_scheduler_service),
) -> dict[str, Any]:
    """
    Manually trigger processing of due jobs.

    For testing and manual intervention.
    """
    results = service.run_due_jobs(worker_id, max_jobs)

    return {
        "processed": len(results),
        "succeeded": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "results": [
            {
                "job_id": str(r.job_id),
                "success": r.success,
                "message": r.message,
            }
            for r in results
        ],
    }


# --- Calendar API (E5.3, TA-0031) ---


@router.get("/calendar", response_model=CalendarResponse)
def get_calendar(
    start: datetime,
    end: datetime,
    status: str | None = None,
    service: SchedulerService = Depends(get_scheduler_service),
) -> CalendarResponse:
    """
    Get scheduled jobs for calendar display (TA-0031).

    Returns jobs within the specified date range formatted for calendar UI.

    Args:
        start: Start of date range (UTC)
        end: End of date range (UTC)
        status: Optional filter by status (queued, running, completed, failed)

    Returns:
        CalendarResponse with events list
    """
    # Ensure dates are UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)

    # Parse status filter
    statuses = [status] if status else None

    # Get jobs in range from repo (access through service's internal repo)
    repo = service._repo
    jobs = repo.list_in_range(start, end, statuses)

    # Convert to calendar events
    events = [
        CalendarEvent(
            id=job.id,
            content_id=job.content_id,
            title=f"Publish: {job.content_id}",  # Could be enriched with content title
            start=job.publish_at_utc,
            status=job.status,
            is_all_day=False,
        )
        for job in jobs
    ]

    return CalendarResponse(
        events=events,
        start_date=start,
        end_date=end,
        total_count=len(events),
    )
