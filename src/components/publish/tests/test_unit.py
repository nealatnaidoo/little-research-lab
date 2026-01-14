"""
Publish component unit tests.

Tests for content publishing, scheduling, and unpublishing.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.components.publish import (
    ProcessDueInput,
    PublishComponent,
    PublishNowInput,
    ScheduleInput,
    UnpublishInput,
)
from src.domain.entities import ContentItem, User
from src.domain.policy import PolicyEngine
from src.rules.loader import load_rules

# --- Mock Implementations ---


class MockContentRepo:
    """In-memory content repository for testing."""

    def __init__(self) -> None:
        self._items: dict[UUID, ContentItem] = {}

    def get_by_id(self, item_id: UUID) -> ContentItem | None:
        return self._items.get(item_id)

    def list_items(self, filters: dict[str, Any]) -> list[ContentItem]:
        items = list(self._items.values())
        if "status" in filters:
            items = [i for i in items if i.status == filters["status"]]
        return items

    def save(self, content: ContentItem) -> ContentItem:
        self._items[content.id] = content
        return content

    def add(self, item: ContentItem) -> None:
        self._items[item.id] = item


class MockUserRepo:
    """In-memory user repository for testing."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    def add(self, user: User) -> None:
        self._users[user.id] = user


class MockClockPort:
    """Mock clock for deterministic testing."""

    def __init__(self, fixed_time: datetime | None = None) -> None:
        self._time = fixed_time or datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._time

    def advance(self, delta: timedelta) -> None:
        self._time = self._time + delta


# --- Fixtures ---


@pytest.fixture
def content_repo() -> MockContentRepo:
    return MockContentRepo()


@pytest.fixture
def user_repo() -> MockUserRepo:
    return MockUserRepo()


@pytest.fixture
def clock() -> MockClockPort:
    return MockClockPort()


@pytest.fixture
def policy() -> PolicyEngine:
    rules_path = Path("rules.yaml").resolve()
    rules = load_rules(rules_path)
    return PolicyEngine(rules)


@pytest.fixture
def component(
    content_repo: MockContentRepo,
    user_repo: MockUserRepo,
    policy: PolicyEngine,
    clock: MockClockPort,
) -> PublishComponent:
    return PublishComponent(
        content_repo=content_repo,
        user_repo=user_repo,
        policy=policy,
        clock=clock,
    )


@pytest.fixture
def admin_user(user_repo: MockUserRepo, clock: MockClockPort) -> User:
    """Create and save an admin user."""
    user = User(
        id=uuid4(),
        email="admin@example.com",
        display_name="Admin",
        password_hash="hashed",
        roles=["admin"],
        status="active",
        created_at=clock.now(),
        updated_at=clock.now(),
    )
    user_repo.add(user)
    return user


@pytest.fixture
def owner_user(user_repo: MockUserRepo, clock: MockClockPort) -> User:
    """Create and save an owner user."""
    user = User(
        id=uuid4(),
        email="owner@example.com",
        display_name="Owner",
        password_hash="hashed",
        roles=["owner"],
        status="active",
        created_at=clock.now(),
        updated_at=clock.now(),
    )
    user_repo.add(user)
    return user


@pytest.fixture
def draft_content(
    owner_user: User, content_repo: MockContentRepo, clock: MockClockPort
) -> ContentItem:
    """Create a draft content item."""
    item = ContentItem(
        id=uuid4(),
        owner_user_id=owner_user.id,
        type="post",
        title="Test Draft",
        slug="test-draft",
        status="draft",
        summary="A test draft",
        blocks=[],
        created_at=clock.now(),
        updated_at=clock.now(),
    )
    content_repo.add(item)
    return item


@pytest.fixture
def published_content(
    owner_user: User, content_repo: MockContentRepo, clock: MockClockPort
) -> ContentItem:
    """Create a published content item."""
    item = ContentItem(
        id=uuid4(),
        owner_user_id=owner_user.id,
        type="post",
        title="Test Published",
        slug="test-published",
        status="published",
        summary="A published post",
        blocks=[],
        published_at=clock.now(),
        created_at=clock.now(),
        updated_at=clock.now(),
    )
    content_repo.add(item)
    return item


# --- Publish Now Tests ---


class TestPublishNow:
    """Test immediate publish functionality."""

    def test_publish_now_success(
        self,
        component: PublishComponent,
        owner_user: User,
        draft_content: ContentItem,
        content_repo: MockContentRepo,
    ) -> None:
        """Owner can publish their draft content."""
        inp = PublishNowInput(user_id=owner_user.id, item_id=draft_content.id)
        result = component.run_publish_now(inp)

        assert result.success is True
        assert len(result.errors) == 0

        # Verify content is now published
        updated = content_repo.get_by_id(draft_content.id)
        assert updated is not None
        assert updated.status == "published"

    def test_publish_now_user_not_found(
        self,
        component: PublishComponent,
        draft_content: ContentItem,
    ) -> None:
        """Publish fails if user doesn't exist."""
        inp = PublishNowInput(user_id=uuid4(), item_id=draft_content.id)
        result = component.run_publish_now(inp)

        assert result.success is False
        assert any(e.code == "USER_NOT_FOUND" for e in result.errors)

    def test_publish_now_item_not_found(
        self,
        component: PublishComponent,
        owner_user: User,
    ) -> None:
        """Publish fails if content doesn't exist."""
        inp = PublishNowInput(user_id=owner_user.id, item_id=uuid4())
        result = component.run_publish_now(inp)

        assert result.success is False
        assert any(e.code == "ITEM_NOT_FOUND" for e in result.errors)


# --- Schedule Tests ---


class TestSchedule:
    """Test scheduled publish functionality."""

    def test_schedule_success(
        self,
        component: PublishComponent,
        owner_user: User,
        draft_content: ContentItem,
        content_repo: MockContentRepo,
        clock: MockClockPort,
    ) -> None:
        """Owner can schedule content for future publication."""
        future_time = clock.now() + timedelta(days=1)
        inp = ScheduleInput(
            user_id=owner_user.id,
            item_id=draft_content.id,
            at_datetime=future_time,
        )
        result = component.run_schedule(inp)

        assert result.success is True

        # Verify content is now scheduled
        updated = content_repo.get_by_id(draft_content.id)
        assert updated is not None
        assert updated.status == "scheduled"
        assert updated.publish_at == future_time

    def test_schedule_past_time_fails(
        self,
        component: PublishComponent,
        owner_user: User,
        draft_content: ContentItem,
        clock: MockClockPort,
    ) -> None:
        """Cannot schedule in the past."""
        past_time = clock.now() - timedelta(hours=1)
        inp = ScheduleInput(
            user_id=owner_user.id,
            item_id=draft_content.id,
            at_datetime=past_time,
        )
        result = component.run_schedule(inp)

        assert result.success is False
        assert any(e.code == "INVALID_SCHEDULE_TIME" for e in result.errors)


# --- Unpublish Tests ---


class TestUnpublish:
    """Test unpublish functionality."""

    def test_unpublish_success(
        self,
        component: PublishComponent,
        owner_user: User,
        published_content: ContentItem,
        content_repo: MockContentRepo,
    ) -> None:
        """Owner can unpublish their content."""
        inp = UnpublishInput(user_id=owner_user.id, item_id=published_content.id)
        result = component.run_unpublish(inp)

        assert result.success is True

        # Verify content is now draft
        updated = content_repo.get_by_id(published_content.id)
        assert updated is not None
        assert updated.status == "draft"


# --- Process Due Tests ---


class TestProcessDue:
    """Test processing scheduled items."""

    def test_process_due_publishes_ready_items(
        self,
        component: PublishComponent,
        owner_user: User,
        content_repo: MockContentRepo,
        clock: MockClockPort,
    ) -> None:
        """Process due publishes items whose schedule time has passed."""
        # Create scheduled content with time in the past
        scheduled_item = ContentItem(
            id=uuid4(),
            owner_user_id=owner_user.id,
            type="post",
            title="Scheduled Post",
            slug="scheduled-post",
            status="scheduled",
            summary="Scheduled",
            blocks=[],
            publish_at=clock.now() - timedelta(hours=1),  # Due
            created_at=clock.now() - timedelta(days=1),
            updated_at=clock.now() - timedelta(days=1),
        )
        content_repo.add(scheduled_item)

        inp = ProcessDueInput()
        result = component.run_process_due(inp)

        assert result.success is True
        assert result.count == 1

        # Verify item is now published
        updated = content_repo.get_by_id(scheduled_item.id)
        assert updated is not None
        assert updated.status == "published"

    def test_process_due_skips_future_items(
        self,
        component: PublishComponent,
        owner_user: User,
        content_repo: MockContentRepo,
        clock: MockClockPort,
    ) -> None:
        """Process due skips items scheduled for the future."""
        # Create scheduled content with time in the future
        future_item = ContentItem(
            id=uuid4(),
            owner_user_id=owner_user.id,
            type="post",
            title="Future Post",
            slug="future-post",
            status="scheduled",
            summary="Future",
            blocks=[],
            publish_at=clock.now() + timedelta(days=1),  # Not due
            created_at=clock.now(),
            updated_at=clock.now(),
        )
        content_repo.add(future_item)

        inp = ProcessDueInput()
        result = component.run_process_due(inp)

        assert result.success is True
        assert result.count == 0

        # Verify item is still scheduled
        updated = content_repo.get_by_id(future_item.id)
        assert updated is not None
        assert updated.status == "scheduled"

    def test_process_due_no_scheduled_items(
        self,
        component: PublishComponent,
    ) -> None:
        """Process due succeeds with zero count when no items scheduled."""
        inp = ProcessDueInput()
        result = component.run_process_due(inp)

        assert result.success is True
        assert result.count == 0
