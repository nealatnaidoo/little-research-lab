from datetime import UTC, datetime, timedelta

import pytest

from src.adapters.clock import SystemClock

# Import Atomic Component Functions
from src.components.content.component import run_create as run_create_content
from src.components.content.component import run_get as run_get_content
from src.components.content.component import run_list as run_list_content
from src.components.content.component import run_transition as run_transition_content
from src.components.content.models import (
    CreateContentInput,
    GetContentInput,
    ListContentInput,
    TransitionContentInput,
)
from src.components.scheduler.component import run_process_due_jobs, run_schedule
from src.components.scheduler.models import ProcessDueJobsInput, SchedulePublishInput
from src.ui.context import ServiceContext


class FakeClock(SystemClock):
    def __init__(self):
        self._now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def now_utc(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta):
        self._now += delta


@pytest.fixture
def journey_ctx(test_ctx: ServiceContext):
    # Override clock with fake for deterministic scheduling
    test_ctx.clock = FakeClock()
    return test_ctx


def test_full_publishing_workflow(journey_ctx: ServiceContext):
    """
    EV-0001: Integration Test using Atomic Components.
    Flow: Login -> Create -> Schedule -> Publish -> Verify.
    """
    # 1. Admin logs in (conceptually)
    admin_user = journey_ctx.user_repo.get_by_email("admin@example.com")
    assert admin_user is not None

    # 2. Create Draft Content
    # Using Content Component
    create_inp = CreateContentInput(
        owner_user_id=admin_user.id,
        type="post",
        title="Journey Post",
        slug="journey-post",
        summary="Testing flows",
        blocks=[],
    )

    res_create = run_create_content(
        create_inp, repo=journey_ctx.content_repo, time=journey_ctx.clock
    )
    assert res_create.success, f"Create failed: {res_create.errors}"
    created = res_create.content
    assert created.status == "draft"

    # 3. Schedule for future
    future_time = journey_ctx.clock.now() + timedelta(hours=2)

    # a) Transition content to scheduled
    transition_inp = TransitionContentInput(
        content_id=created.id, to_status="scheduled", publish_at=future_time
    )
    res_trans = run_transition_content(
        transition_inp,
        repo=journey_ctx.content_repo,
        time=journey_ctx.clock,
        asset_resolver=None,  # No assets to resolve
    )
    assert res_trans.success, f"Transition failed: {res_trans.errors}"

    # b) Create Schedule Job
    schedule_inp = SchedulePublishInput(content_id=created.id, publish_at_utc=future_time)
    res_sched = run_schedule(
        schedule_inp,
        repo=journey_ctx.publish_job_repo,
        time_port=journey_ctx.clock,
    )
    assert res_sched.success, f"Schedule failed: {res_sched.errors}"

    # 4. Verify NOT visible publicly yet
    list_inp = ListContentInput(status="published")
    res_list = run_list_content(list_inp, repo=journey_ctx.content_repo)
    public_items = res_list.items
    assert not any(i.id == created.id for i in public_items)

    # 5. Advance time
    clock = journey_ctx.clock
    clock.advance(timedelta(hours=3))

    # 6. Process Due Jobs
    # We need a Publisher implementation that calls run_transition
    class TestPublisher:
        def publish(self, content_id):
            t_inp = TransitionContentInput(content_id=content_id, to_status="published")
            res = run_transition_content(
                t_inp, repo=journey_ctx.content_repo, time=journey_ctx.clock
            )
            return (res.success, None if res.success else str(res.errors))

    # DEBUG: Dump DB
    conn = journey_ctx.publish_job_repo._get_conn()
    rows = conn.execute(
        "SELECT id, status, publish_at_utc, next_retry_at FROM publish_jobs"
    ).fetchall()
    print(f"DEBUG: All Jobs in DB: {rows}")
    target_time = journey_ctx.clock.now().isoformat()
    print(f"DEBUG: Target query time: {target_time}")

    # Try manual query
    manual_rows = conn.execute(
        """
        SELECT * FROM publish_jobs 
        WHERE (status = 'queued' OR status = 'retry_wait')
        AND (next_retry_at IS NULL OR next_retry_at <= ?)
        AND publish_at_utc <= ?
        ORDER BY publish_at_utc ASC
        LIMIT ?
    """,
        (target_time, target_time, 10),
    ).fetchall()
    print(f"DEBUG: Manual Query Result: {manual_rows}")
    conn.close()

    process_inp = ProcessDueJobsInput(worker_id="test-worker")
    res_proc = run_process_due_jobs(
        process_inp,
        repo=journey_ctx.publish_job_repo,
        publisher=TestPublisher(),
        time_port=journey_ctx.clock,
    )
    assert res_proc.success, f"Process failed: {res_proc.results}"

    # 7. Check Job Status Debug
    # Assuming only 1 job
    # We can't access job id easily here as run_schedule returns Job object
    # but we didn't save it to local var. Res_sched.job has it.
    job_debug = res_sched.job
    # Reload from repo
    if job_debug:
        reloaded = journey_ctx.publish_job_repo.get_by_id(job_debug.id)
        print(f"DEBUG: Job status after process: {reloaded.status if reloaded else 'Job Lost'}")
        if reloaded and reloaded.status != "succeeded":
            print(f"DEBUG: Job Error: {reloaded.error_message}")

    # 7. Verify VISIBLE publicly
    res_list_2 = run_list_content(list_inp, repo=journey_ctx.content_repo)
    found = any(i.id == created.id for i in res_list_2.items)
    if not found:
        print(f"DEBUG: Items found: {[i.id for i in res_list_2.items]}")
        # Debug why
        fresh = run_get_content(
            GetContentInput(content_id=created.id), repo=journey_ctx.content_repo
        ).content
        print(f"DEBUG: Item status: {fresh.status if fresh else 'None'}")
    assert found, (
        f"Item {created.id} not found in public list. Found: {len(res_list_2.items)} items."
    )
