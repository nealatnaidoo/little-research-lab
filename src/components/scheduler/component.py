"""
Scheduler component - Scheduled publishing job management.

Spec refs: E5.2
Test assertions: TA-0027, TA-0028, TA-0029, TA-0030

Handles creation, claiming, execution, and retry of publish jobs.

Invariants:
- I1: Idempotency key ensures single publish per schedule
- I2: DST transitions handled correctly
- I3: Failed jobs retry with backoff
- I4: Jobs claimed atomically to prevent double-publish
- I5: Past schedules execute immediately
"""

from __future__ import annotations

from ._impl import (
    ExecutionResult as LegacyResult,
)
from ._impl import (
    PublishJob as LegacyJob,
)
from ._impl import (
    SchedulerConfig,
    SchedulerService,
)
from ._impl import (
    SchedulerError as LegacyError,
)
from .models import (
    CancelOutput,
    CancelScheduleInput,
    ExecutionResult,
    GetJobInput,
    JobOutput,
    ProcessDueJobsInput,
    ProcessOutput,
    PublishJob,
    RescheduleInput,
    ScheduleOutput,
    SchedulePublishInput,
    SchedulerValidationError,
)
from .ports import ContentPublisherPort, PublishJobRepoPort, RulesPort, TimePort


def _convert_job(legacy: LegacyJob | None) -> PublishJob | None:
    """Convert legacy job to component model."""
    if legacy is None:
        return None
    return PublishJob(
        id=legacy.id,
        content_id=legacy.content_id,
        publish_at_utc=legacy.publish_at_utc,
        status=legacy.status,
        attempts=legacy.attempts,
        last_attempt_at=legacy.last_attempt_at,
        next_retry_at=legacy.next_retry_at,
        completed_at=legacy.completed_at,
        actual_publish_at=legacy.actual_publish_at,
        error_message=legacy.error_message,
        claimed_by=legacy.claimed_by,
        created_at=legacy.created_at,
        updated_at=legacy.updated_at,
    )


def _convert_errors(
    legacy_errors: list[LegacyError],
) -> list[SchedulerValidationError]:
    """Convert legacy errors to component errors."""
    return [
        SchedulerValidationError(
            code=e.code,
            message=e.message,
            job_id=e.job_id,
        )
        for e in legacy_errors
    ]


def _convert_result(legacy: LegacyResult) -> ExecutionResult:
    """Convert legacy execution result to component model."""
    return ExecutionResult(
        success=legacy.success,
        job_id=legacy.job_id,
        message=legacy.message,
        actual_publish_at=legacy.actual_publish_at,
    )


def _build_config(rules: RulesPort | None) -> SchedulerConfig:
    """Build scheduler config from rules port."""
    if rules is None:
        return SchedulerConfig()

    return SchedulerConfig(
        max_attempts=rules.get_max_attempts(),
        backoff_seconds=rules.get_backoff_seconds(),
        publish_grace_seconds=rules.get_publish_grace_seconds(),
        never_publish_early=rules.get_never_publish_early(),
    )


def _create_service(
    repo: PublishJobRepoPort,
    publisher: ContentPublisherPort | None,
    time_port: TimePort | None,
    rules: RulesPort | None,
) -> SchedulerService:
    """Create scheduler service from ports."""
    config = _build_config(rules)
    return SchedulerService(
        repo=repo,  # type: ignore[arg-type]  # Protocol structural mismatch
        publisher=publisher,
        time_port=time_port,
        config=config,
    )


# --- Component Entry Points ---


def run_schedule(
    inp: SchedulePublishInput,
    *,
    repo: PublishJobRepoPort,
    time_port: TimePort | None = None,
    rules: RulesPort | None = None,
) -> ScheduleOutput:
    """
    Schedule content for publishing (TA-0028).

    Creates a publish job with idempotency check.

    Args:
        inp: Input containing content_id and publish time.
        repo: Publish job repository port.
        time_port: Optional time port for timestamps.
        rules: Optional rules port for configuration.

    Returns:
        ScheduleOutput with job or errors.
    """
    service = _create_service(repo, None, time_port, rules)

    legacy_job, legacy_errors = service.schedule(
        content_id=inp.content_id,
        publish_at_utc=inp.publish_at_utc,
    )

    job = _convert_job(legacy_job)
    errors = _convert_errors(legacy_errors)

    return ScheduleOutput(
        job=job,
        errors=errors,
        success=len(errors) == 0,
    )


def run_cancel(
    inp: CancelScheduleInput,
    *,
    repo: PublishJobRepoPort,
    time_port: TimePort | None = None,
    rules: RulesPort | None = None,
) -> CancelOutput:
    """
    Cancel a scheduled job.

    Args:
        inp: Input containing job_id to cancel.
        repo: Publish job repository port.
        time_port: Optional time port for timestamps.
        rules: Optional rules port for configuration.

    Returns:
        CancelOutput indicating success or failure.
    """
    service = _create_service(repo, None, time_port, rules)

    cancelled, legacy_errors = service.unschedule(inp.job_id)
    errors = _convert_errors(legacy_errors)

    return CancelOutput(
        cancelled=cancelled,
        errors=errors,
        success=cancelled,
    )


def run_reschedule(
    inp: RescheduleInput,
    *,
    repo: PublishJobRepoPort,
    time_port: TimePort | None = None,
    rules: RulesPort | None = None,
) -> ScheduleOutput:
    """
    Reschedule a job to a new time.

    Args:
        inp: Input containing job_id and new publish time.
        repo: Publish job repository port.
        time_port: Optional time port for timestamps.
        rules: Optional rules port for configuration.

    Returns:
        ScheduleOutput with updated job or errors.
    """
    service = _create_service(repo, None, time_port, rules)

    legacy_job, legacy_errors = service.reschedule(
        job_id=inp.job_id,
        new_publish_at_utc=inp.new_publish_at_utc,
    )

    job = _convert_job(legacy_job)
    errors = _convert_errors(legacy_errors)

    return ScheduleOutput(
        job=job,
        errors=errors,
        success=len(errors) == 0,
    )


def run_process_due_jobs(
    inp: ProcessDueJobsInput,
    *,
    repo: PublishJobRepoPort,
    publisher: ContentPublisherPort,
    time_port: TimePort | None = None,
    rules: RulesPort | None = None,
) -> ProcessOutput:
    """
    Process all due publish jobs (TA-0029).

    Args:
        inp: Input containing worker_id and max_jobs.
        repo: Publish job repository port.
        publisher: Content publisher port.
        time_port: Optional time port for timestamps.
        rules: Optional rules port for configuration.

    Returns:
        ProcessOutput with execution results.
    """
    service = _create_service(repo, publisher, time_port, rules)

    legacy_results = service.run_due_jobs(
        worker_id=inp.worker_id,
        max_jobs=inp.max_jobs,
    )

    results = tuple(_convert_result(r) for r in legacy_results)

    return ProcessOutput(
        results=results,
        errors=[],
        success=True,
    )


def run_get_job(
    inp: GetJobInput,
    *,
    repo: PublishJobRepoPort,
    time_port: TimePort | None = None,
    rules: RulesPort | None = None,
) -> JobOutput:
    """
    Get a job by ID.

    Args:
        inp: Input containing job_id.
        repo: Publish job repository port.
        time_port: Optional time port for timestamps.
        rules: Optional rules port for configuration.

    Returns:
        JobOutput with job or not found error.
    """
    service = _create_service(repo, None, time_port, rules)

    legacy_job = service.get_job(inp.job_id)
    job = _convert_job(legacy_job)

    if job is None:
        return JobOutput(
            job=None,
            errors=[
                SchedulerValidationError(
                    code="job_not_found",
                    message=f"Job {inp.job_id} not found",
                    job_id=inp.job_id,
                )
            ],
            success=False,
        )

    return JobOutput(
        job=job,
        errors=[],
        success=True,
    )


def run(
    inp: (
        SchedulePublishInput
        | CancelScheduleInput
        | RescheduleInput
        | ProcessDueJobsInput
        | GetJobInput
    ),
    *,
    repo: PublishJobRepoPort,
    publisher: ContentPublisherPort | None = None,
    time_port: TimePort | None = None,
    rules: RulesPort | None = None,
) -> ScheduleOutput | CancelOutput | ProcessOutput | JobOutput:
    """
    Main entry point for the scheduler component.

    Dispatches to appropriate handler based on input type.

    Args:
        inp: Input object determining the operation.
        repo: Publish job repository port.
        publisher: Optional content publisher port (required for process).
        time_port: Optional time port for timestamps.
        rules: Optional rules port for configuration.

    Returns:
        Appropriate output object based on input type.
    """
    if isinstance(inp, SchedulePublishInput):
        return run_schedule(inp, repo=repo, time_port=time_port, rules=rules)
    elif isinstance(inp, CancelScheduleInput):
        return run_cancel(inp, repo=repo, time_port=time_port, rules=rules)
    elif isinstance(inp, RescheduleInput):
        return run_reschedule(inp, repo=repo, time_port=time_port, rules=rules)
    elif isinstance(inp, ProcessDueJobsInput):
        if publisher is None:
            raise ValueError("ContentPublisherPort is required for process operations")
        return run_process_due_jobs(
            inp, repo=repo, publisher=publisher, time_port=time_port, rules=rules
        )
    elif isinstance(inp, GetJobInput):
        return run_get_job(inp, repo=repo, time_port=time_port, rules=rules)
    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
