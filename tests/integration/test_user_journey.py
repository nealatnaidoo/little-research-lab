import pytest
from datetime import datetime, timedelta
import uuid

from src.ui.context import ServiceContext
from src.ui.state import AppState
from src.domain.entities import ContentItem, ContentBlock
from src.adapters.clock import SystemClock

class FakeClock(SystemClock):
    def __init__(self):
        self._now = datetime(2025, 1, 1, 12, 0, 0)
    
    def now(self) -> datetime:
        return self._now
    
    def advance(self, delta: timedelta):
        self._now += delta

@pytest.fixture
def journey_ctx(test_ctx: ServiceContext):
    # Override clock with fake for deterministic scheduling
    test_ctx.clock = FakeClock()
    # Re-inject services if they depend on clock (PublishService does)
    from src.services.publish import PublishService
    test_ctx.publish_service = PublishService(test_ctx.content_repo, test_ctx.policy, test_ctx.clock)
    return test_ctx

def test_full_publishing_workflow(journey_ctx: ServiceContext):
    """
    EV-0001: Service Integration Test simulating a full user journey.
    Flow: Login -> Create -> Schedule -> Publish -> Verify.
    """
    # 1. Admin logs in (conceptually, we just need the user obj)
    # We use journey_ctx.user_repo directly as auth_service encapsulates logic
    admin_user = journey_ctx.user_repo.get_by_email("admin@example.com")
    assert admin_user is not None
    
    # 2. Create Draft Content
    draft = ContentItem(
        owner_user_id=admin_user.id,
        type="post",
        title="Journey Post",
        slug="journey-post",
        status="draft",
        summary="Testing flows",
        blocks=[],
        created_at=journey_ctx.clock.now(),
        updated_at=journey_ctx.clock.now()
    )
    created = journey_ctx.content_service.create_item(admin_user, draft)
    assert created.id is not None
    assert created.status == "draft"

    # 3. Schedule for future
    future_time = journey_ctx.clock.now() + timedelta(hours=2)
    journey_ctx.publish_service.schedule(admin_user, created.id, future_time)
    
    # Reload and verify scheduled
    item = journey_ctx.content_service.repo.get_by_id(created.id)
    assert item is not None
    assert item.status == "scheduled"
    assert item.publish_at == future_time
    
    # 4. Verify NOT visible publicly yet
    public_items = journey_ctx.content_service.list_public_items()
    assert not any(i.id == created.id for i in public_items)
    
    # 5. Advance time but NOT enough (e.g., 1 hour)
    clock = journey_ctx.clock # type: ignore
    clock.advance(timedelta(hours=1))
    
    # Run publish check
    published_count = journey_ctx.publish_service.process_due_items()
    assert published_count == 0
    
    # 6. Advance time past schedule (another 2 hours)
    clock.advance(timedelta(hours=2))
    
    # Run publish check
    published_count = journey_ctx.publish_service.process_due_items()
    assert published_count == 1
    
    # 7. Verify VISIBLE publicly
    public_items = journey_ctx.content_service.list_public_items()
    assert any(i.id == created.id for i in public_items)
    
    # Reload and check published_at
    item = journey_ctx.content_service.repo.get_by_id(created.id)
    assert item is not None
    assert item.status == "published"
    assert item.published_at is not None
