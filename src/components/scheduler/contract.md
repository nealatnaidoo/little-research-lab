## COMPONENT_ID
C4-scheduler

## PURPOSE
Schedule content for future publication with idempotent job execution.
Handles DST transitions and retry logic for failed publishes.

## INPUTS
- `SchedulePublishInput`: Schedule content for future publish time
- `ProcessDueJobsInput`: Process all due publish jobs
- `CancelScheduleInput`: Cancel a scheduled publish

## OUTPUTS
- `ScheduleOutput`: Schedule result with job ID
- `ProcessOutput`: List of processed jobs with results
- `CancelOutput`: Cancellation result

## DEPENDENCIES (PORTS)
- `PublishJobRepoPort`: Database access for publish jobs
- `ContentPort`: Content service for actual publish
- `TimePort`: Time source for scheduling
- `RulesPort`: Scheduler rules (idempotency, timing, retries)

## SIDE EFFECTS
- Database write for job creation/update
- Content publish on job execution

## INVARIANTS
- I1: Idempotency key ensures single publish per schedule (TA-0027)
- I2: DST transitions handled correctly (TA-0027)
- I3: Failed jobs retry with backoff
- I4: Jobs claimed atomically to prevent double-publish
- I5: Past schedules execute immediately

## ERROR SEMANTICS
- Returns errors for invalid schedule times
- Captures and records job execution errors
- Idempotent re-execution is safe

## TESTS
- `tests/unit/test_scheduler.py`: TA-0027, TA-0028 (tests)
  - Idempotent publish scheduling
  - DST handling
  - Retry logic

## EVIDENCE
- `artifacts/pytest-scheduler-report.json`
