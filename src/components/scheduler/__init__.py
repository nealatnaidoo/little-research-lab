"""
Scheduler component - Scheduled publishing job management.

Spec refs: E5.2
"""

# Re-exports from _impl for backwards compatibility
# Re-exports from legacy scheduler service (pending full migration)
from src.core.services.scheduler import (
    calculate_next_retry,
    check_idempotency,
    create_scheduler_service,
)

from ._impl import (
    SchedulerConfig,
    SchedulerError,
    SchedulerService,
    create_publish_job,
)
from .component import (
    run,
    run_cancel,
    run_get_job,
    run_process_due_jobs,
    run_reschedule,
    run_schedule,
)
from .models import (
    CancelOutput,
    CancelScheduleInput,
    ExecutionResult,
    GetJobInput,
    JobOutput,
    JobStatus,
    ProcessDueJobsInput,
    ProcessOutput,
    PublishJob,
    RescheduleInput,
    ScheduleOutput,
    SchedulePublishInput,
    SchedulerValidationError,
)
from .ports import ContentPublisherPort, PublishJobRepoPort, RulesPort, TimePort

__all__ = [
    # Entry points
    "run",
    "run_cancel",
    "run_get_job",
    "run_process_due_jobs",
    "run_reschedule",
    "run_schedule",
    # Input models
    "CancelScheduleInput",
    "GetJobInput",
    "ProcessDueJobsInput",
    "RescheduleInput",
    "SchedulePublishInput",
    # Output models
    "CancelOutput",
    "ExecutionResult",
    "JobOutput",
    "JobStatus",
    "ProcessOutput",
    "PublishJob",
    "ScheduleOutput",
    "SchedulerValidationError",
    # Ports
    "ContentPublisherPort",
    "PublishJobRepoPort",
    "RulesPort",
    "TimePort",
    # Legacy _impl re-exports
    "SchedulerConfig",
    "SchedulerError",
    "SchedulerService",
    "create_publish_job",
    # Legacy service re-exports
    "calculate_next_retry",
    "check_idempotency",
    "create_scheduler_service",
]
