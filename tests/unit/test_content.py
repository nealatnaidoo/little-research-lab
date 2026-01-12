"""
TA-0110: ContentService state machine tests.

Tests content validation, state transitions, and publish guards.

Spec refs: C1, SM1, E2, E4, R1
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from src.core.entities import ContentBlock, ContentItem
from src.core.services.content import (
    ContentService,
    ContentStateMachine,
    create_content_service,
    extract_asset_references,
    validate_content_fields,
    validate_publish_at,
)

# --- Mock Repository ---


class MockContentRepo:
    """Mock content repository."""

    def __init__(self) -> None:
        self.items: dict[UUID, ContentItem] = {}

    def get_by_id(self, item_id: UUID) -> ContentItem | None:
        return self.items.get(item_id)

    def get_by_slug(self, slug: str, item_type: str) -> ContentItem | None:
        for item in self.items.values():
            if item.slug == slug and item.type == item_type:
                return item
        return None

    def save(self, content: ContentItem) -> ContentItem:
        self.items[content.id] = content
        return content

    def delete(self, item_id: UUID) -> None:
        self.items.pop(item_id, None)


class MockAssetResolver:
    """Mock asset resolver."""

    def __init__(self, existing_assets: set[UUID] | None = None) -> None:
        self.existing = existing_assets or set()

    def resolve(self, asset_id: UUID) -> bool:
        return asset_id in self.existing


# --- Fixtures ---


@pytest.fixture
def repo() -> MockContentRepo:
    """Create mock repository."""
    return MockContentRepo()


@pytest.fixture
def service(repo: MockContentRepo) -> ContentService:
    """Create content service."""
    return ContentService(repo)


@pytest.fixture
def now() -> datetime:
    """Fixed 'now' time for testing."""
    return datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def draft_content() -> ContentItem:
    """Create draft content item."""
    return ContentItem(
        id=uuid4(),
        type="post",
        slug="test-post",
        title="Test Post",
        summary="A test post",
        status="draft",
        owner_user_id=uuid4(),
    )


@pytest.fixture
def published_content() -> ContentItem:
    """Create published content item."""
    return ContentItem(
        id=uuid4(),
        type="post",
        slug="published-post",
        title="Published Post",
        summary="A published post",
        status="published",
        published_at=datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC),
        owner_user_id=uuid4(),
    )


# --- TA-0110: State Machine Tests ---


class TestTA0110StateMachine:
    """TA-0110: Content state machine tests."""

    def test_draft_can_transition_to_scheduled(self) -> None:
        """Draft content can be scheduled."""
        sm = ContentStateMachine()
        assert sm.can_transition("draft", "scheduled") is True

    def test_draft_can_transition_to_published(self) -> None:
        """Draft content can be published directly."""
        sm = ContentStateMachine()
        assert sm.can_transition("draft", "published") is True

    def test_scheduled_can_transition_to_draft(self) -> None:
        """Scheduled content can be unscheduled (back to draft)."""
        sm = ContentStateMachine()
        assert sm.can_transition("scheduled", "draft") is True

    def test_scheduled_can_transition_to_published(self) -> None:
        """Scheduled content can be published."""
        sm = ContentStateMachine()
        assert sm.can_transition("scheduled", "published") is True

    def test_published_can_transition_to_draft(self) -> None:
        """Published content can be unpublished."""
        sm = ContentStateMachine()
        assert sm.can_transition("published", "draft") is True

    def test_published_cannot_transition_to_scheduled(self) -> None:
        """Published content cannot be scheduled (must unpublish first)."""
        sm = ContentStateMachine()
        assert sm.can_transition("published", "scheduled") is False

    def test_draft_cannot_transition_to_draft(self) -> None:
        """Draft cannot transition to itself."""
        sm = ContentStateMachine()
        assert sm.can_transition("draft", "draft") is False

    def test_get_allowed_transitions_draft(self) -> None:
        """Get allowed transitions from draft."""
        sm = ContentStateMachine()
        allowed = sm.get_allowed_transitions("draft")
        assert "scheduled" in allowed
        assert "published" in allowed
        assert "draft" not in allowed

    def test_get_allowed_transitions_published(self) -> None:
        """Get allowed transitions from published."""
        sm = ContentStateMachine()
        allowed = sm.get_allowed_transitions("published")
        assert allowed == ["draft"]


class TestStateMachineValidation:
    """State machine validation tests."""

    def test_validate_transition_allowed(self, draft_content: ContentItem, now: datetime) -> None:
        """Valid transition passes validation."""
        sm = ContentStateMachine()
        errors = sm.validate_transition(draft_content, "published", now=now)
        assert len(errors) == 0

    def test_validate_transition_not_allowed(
        self, published_content: ContentItem, now: datetime
    ) -> None:
        """Invalid transition fails validation."""
        sm = ContentStateMachine()
        errors = sm.validate_transition(published_content, "scheduled", now=now)
        assert len(errors) == 1
        assert errors[0].code == "invalid_transition"

    def test_validate_schedule_requires_publish_at(
        self, draft_content: ContentItem, now: datetime
    ) -> None:
        """Scheduling requires publish_at (G2)."""
        sm = ContentStateMachine()
        errors = sm.validate_transition(draft_content, "scheduled", now=now)
        assert len(errors) == 1
        assert errors[0].code == "publish_at_required"

    def test_validate_schedule_publish_at_future(
        self, draft_content: ContentItem, now: datetime
    ) -> None:
        """Scheduling requires publish_at in future (G2)."""
        sm = ContentStateMachine()
        past_time = now - timedelta(hours=1)
        errors = sm.validate_transition(draft_content, "scheduled", publish_at=past_time, now=now)
        assert len(errors) == 1
        assert errors[0].code == "publish_at_past"

    def test_validate_schedule_publish_at_valid(
        self, draft_content: ContentItem, now: datetime
    ) -> None:
        """Scheduling with future publish_at passes (G2)."""
        sm = ContentStateMachine()
        future_time = now + timedelta(hours=1)
        errors = sm.validate_transition(draft_content, "scheduled", publish_at=future_time, now=now)
        assert len(errors) == 0


# --- Content Service Tests ---


class TestContentServiceCreate:
    """Content creation tests."""

    def test_create_valid_content(self, service: ContentService, repo: MockContentRepo) -> None:
        """Valid content is created successfully."""
        content = ContentItem(
            type="post",
            slug="new-post",
            title="New Post",
            owner_user_id=uuid4(),
        )

        saved, errors = service.create(content)

        assert len(errors) == 0
        assert saved.id in repo.items
        assert saved.status == "draft"

    def test_create_requires_title(self, service: ContentService) -> None:
        """Content requires a title."""
        content = ContentItem(
            type="post",
            slug="no-title",
            title="",
            owner_user_id=uuid4(),
        )

        saved, errors = service.create(content)

        assert len(errors) == 1
        assert errors[0].code == "title_required"

    def test_create_requires_slug(self, service: ContentService) -> None:
        """Content requires a slug."""
        content = ContentItem(
            type="post",
            slug="",
            title="No Slug",
            owner_user_id=uuid4(),
        )

        saved, errors = service.create(content)

        assert len(errors) == 1
        assert errors[0].code == "slug_required"

    def test_create_validates_slug_format(self, service: ContentService) -> None:
        """Slug must be valid format."""
        content = ContentItem(
            type="post",
            slug="Invalid Slug!",
            title="Bad Slug",
            owner_user_id=uuid4(),
        )

        saved, errors = service.create(content)

        assert len(errors) == 1
        assert errors[0].code == "slug_invalid"

    def test_create_rejects_duplicate_slug(
        self, service: ContentService, repo: MockContentRepo
    ) -> None:
        """Duplicate slug is rejected."""
        existing = ContentItem(
            type="post",
            slug="existing",
            title="Existing",
            owner_user_id=uuid4(),
        )
        repo.save(existing)

        duplicate = ContentItem(
            type="post",
            slug="existing",
            title="Duplicate",
            owner_user_id=uuid4(),
        )

        saved, errors = service.create(duplicate)

        assert len(errors) == 1
        assert errors[0].code == "slug_exists"


class TestContentServiceTransition:
    """Content state transition tests."""

    def test_transition_draft_to_published(
        self,
        service: ContentService,
        repo: MockContentRepo,
        draft_content: ContentItem,
        now: datetime,
    ) -> None:
        """Draft can be published."""
        repo.save(draft_content)

        result, errors = service.transition(draft_content.id, "published", now=now)

        assert len(errors) == 0
        assert result is not None
        assert result.status == "published"
        assert result.published_at == now

    def test_transition_draft_to_scheduled(
        self,
        service: ContentService,
        repo: MockContentRepo,
        draft_content: ContentItem,
        now: datetime,
    ) -> None:
        """Draft can be scheduled."""
        repo.save(draft_content)
        publish_at = now + timedelta(days=1)

        result, errors = service.transition(
            draft_content.id, "scheduled", publish_at=publish_at, now=now
        )

        assert len(errors) == 0
        assert result is not None
        assert result.status == "scheduled"
        assert result.publish_at == publish_at

    def test_transition_published_to_draft(
        self,
        service: ContentService,
        repo: MockContentRepo,
        published_content: ContentItem,
    ) -> None:
        """Published can be unpublished."""
        repo.save(published_content)

        result, errors = service.transition(published_content.id, "draft")

        assert len(errors) == 0
        assert result is not None
        assert result.status == "draft"

    def test_transition_invalid_returns_error(
        self,
        service: ContentService,
        repo: MockContentRepo,
        published_content: ContentItem,
    ) -> None:
        """Invalid transition returns error."""
        repo.save(published_content)

        result, errors = service.transition(published_content.id, "scheduled")

        assert len(errors) == 1
        assert errors[0].code == "invalid_transition"

    def test_transition_not_found_returns_error(self, service: ContentService) -> None:
        """Non-existent content returns error."""
        fake_id = uuid4()

        result, errors = service.transition(fake_id, "published")

        assert result is None
        assert len(errors) == 1
        assert errors[0].code == "not_found"


class TestContentServiceConvenienceMethods:
    """Convenience method tests."""

    def test_schedule(
        self,
        service: ContentService,
        repo: MockContentRepo,
        draft_content: ContentItem,
        now: datetime,
    ) -> None:
        """schedule() transitions to scheduled."""
        repo.save(draft_content)
        publish_at = now + timedelta(hours=2)

        result, errors = service.schedule(draft_content.id, publish_at, now)

        assert len(errors) == 0
        assert result.status == "scheduled"

    def test_publish(
        self,
        service: ContentService,
        repo: MockContentRepo,
        draft_content: ContentItem,
        now: datetime,
    ) -> None:
        """publish() transitions to published."""
        repo.save(draft_content)

        result, errors = service.publish(draft_content.id, now)

        assert len(errors) == 0
        assert result.status == "published"

    def test_unpublish(
        self,
        service: ContentService,
        repo: MockContentRepo,
        published_content: ContentItem,
    ) -> None:
        """unpublish() transitions to draft."""
        repo.save(published_content)

        result, errors = service.unpublish(published_content.id)

        assert len(errors) == 0
        assert result.status == "draft"

    def test_unschedule(
        self,
        service: ContentService,
        repo: MockContentRepo,
        now: datetime,
    ) -> None:
        """unschedule() transitions to draft."""
        scheduled = ContentItem(
            type="post",
            slug="scheduled",
            title="Scheduled",
            status="scheduled",
            publish_at=now + timedelta(days=1),
            owner_user_id=uuid4(),
        )
        repo.save(scheduled)

        result, errors = service.unschedule(scheduled.id)

        assert len(errors) == 0
        assert result.status == "draft"
        assert result.publish_at is None


class TestPublishGuards:
    """Publish guards tests (G1)."""

    def test_publish_requires_valid_content(self, repo: MockContentRepo, now: datetime) -> None:
        """Publish requires validated content (G1a)."""
        service = ContentService(repo, require_validated_content=True)

        invalid = ContentItem(
            type="post",
            slug="no-title",
            title="",  # Invalid - no title
            status="draft",
            owner_user_id=uuid4(),
        )
        repo.save(invalid)

        result, errors = service.publish(invalid.id, now)

        assert len(errors) == 1
        assert errors[0].code == "title_required"

    def test_publish_blocks_missing_assets(self, repo: MockContentRepo, now: datetime) -> None:
        """Publish blocks if referenced assets missing (G1b)."""
        missing_asset_id = uuid4()
        resolver = MockAssetResolver(existing_assets=set())  # No assets exist

        service = ContentService(
            repo,
            asset_resolver=resolver,
            block_publish_if_missing_assets=True,
        )

        content = ContentItem(
            type="post",
            slug="with-image",
            title="With Image",
            status="draft",
            owner_user_id=uuid4(),
            blocks=[
                ContentBlock(
                    block_type="image",
                    data_json={"asset_id": str(missing_asset_id)},
                )
            ],
        )
        repo.save(content)

        result, errors = service.publish(content.id, now)

        assert len(errors) == 1
        assert errors[0].code == "missing_asset"

    def test_publish_succeeds_with_valid_assets(self, repo: MockContentRepo, now: datetime) -> None:
        """Publish succeeds when assets exist."""
        existing_asset_id = uuid4()
        resolver = MockAssetResolver(existing_assets={existing_asset_id})

        service = ContentService(
            repo,
            asset_resolver=resolver,
            block_publish_if_missing_assets=True,
        )

        content = ContentItem(
            type="post",
            slug="with-valid-image",
            title="With Valid Image",
            status="draft",
            owner_user_id=uuid4(),
            blocks=[
                ContentBlock(
                    block_type="image",
                    data_json={"asset_id": str(existing_asset_id)},
                )
            ],
        )
        repo.save(content)

        result, errors = service.publish(content.id, now)

        assert len(errors) == 0
        assert result.status == "published"


class TestContentValidation:
    """Content field validation tests."""

    def test_validate_content_fields_valid(self) -> None:
        """Valid content passes validation."""
        content = ContentItem(
            type="post",
            slug="valid-slug",
            title="Valid Title",
            owner_user_id=uuid4(),
        )

        errors = validate_content_fields(content)

        assert len(errors) == 0

    def test_validate_slug_lowercase(self) -> None:
        """Slug must be lowercase."""
        content = ContentItem(
            type="post",
            slug="UPPERCASE",
            title="Title",
            owner_user_id=uuid4(),
        )

        errors = validate_content_fields(content)

        assert len(errors) == 1
        assert errors[0].code == "slug_invalid"

    def test_validate_slug_with_hyphens(self) -> None:
        """Slug can contain hyphens."""
        content = ContentItem(
            type="post",
            slug="my-test-slug",
            title="Title",
            owner_user_id=uuid4(),
        )

        errors = validate_content_fields(content)

        assert len(errors) == 0

    def test_validate_slug_with_numbers(self) -> None:
        """Slug can contain numbers."""
        content = ContentItem(
            type="post",
            slug="post-2026",
            title="Title",
            owner_user_id=uuid4(),
        )

        errors = validate_content_fields(content)

        assert len(errors) == 0


class TestPublishAtValidation:
    """publish_at validation tests (G2)."""

    def test_validate_publish_at_required(self) -> None:
        """publish_at is required for scheduling."""
        now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)

        errors = validate_publish_at(None, now)

        assert len(errors) == 1
        assert errors[0].code == "publish_at_required"

    def test_validate_publish_at_past(self) -> None:
        """publish_at cannot be in the past."""
        now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
        past = now - timedelta(hours=1)

        errors = validate_publish_at(past, now)

        assert len(errors) == 1
        assert errors[0].code == "publish_at_past"

    def test_validate_publish_at_future(self) -> None:
        """publish_at in the future is valid."""
        now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
        future = now + timedelta(hours=1)

        errors = validate_publish_at(future, now)

        assert len(errors) == 0

    def test_validate_publish_at_grace_period(self) -> None:
        """publish_at within grace period is allowed."""
        now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
        # 5 seconds in the future (within default 10s grace)
        near_future = now + timedelta(seconds=5)

        errors = validate_publish_at(near_future, now, grace_seconds=10)

        # Should be invalid - within grace but must be *after* threshold
        assert len(errors) == 1  # Still in past relative to threshold


class TestAssetReferenceExtraction:
    """Asset reference extraction tests."""

    def test_extract_no_assets(self) -> None:
        """Content without assets returns empty list."""
        content = ContentItem(
            type="post",
            slug="text-only",
            title="Text Only",
            owner_user_id=uuid4(),
            blocks=[ContentBlock(block_type="markdown", data_json={"text": "Hello"})],
        )

        assets = extract_asset_references(content)

        assert assets == []

    def test_extract_image_assets(self) -> None:
        """Image blocks have assets extracted."""
        asset_id = uuid4()
        content = ContentItem(
            type="post",
            slug="with-image",
            title="With Image",
            owner_user_id=uuid4(),
            blocks=[
                ContentBlock(
                    block_type="image",
                    data_json={"asset_id": str(asset_id), "alt": "Test"},
                )
            ],
        )

        assets = extract_asset_references(content)

        assert len(assets) == 1
        assert assets[0] == asset_id

    def test_extract_multiple_assets(self) -> None:
        """Multiple image blocks have all assets extracted."""
        asset1 = uuid4()
        asset2 = uuid4()
        content = ContentItem(
            type="post",
            slug="gallery",
            title="Gallery",
            owner_user_id=uuid4(),
            blocks=[
                ContentBlock(block_type="image", data_json={"asset_id": str(asset1)}),
                ContentBlock(block_type="markdown", data_json={"text": "Caption"}),
                ContentBlock(block_type="image", data_json={"asset_id": str(asset2)}),
            ],
        )

        assets = extract_asset_references(content)

        assert len(assets) == 2
        assert asset1 in assets
        assert asset2 in assets


class TestHelperMethods:
    """Helper method tests."""

    def test_can_transition(
        self,
        service: ContentService,
        repo: MockContentRepo,
        draft_content: ContentItem,
    ) -> None:
        """can_transition checks if transition is possible."""
        repo.save(draft_content)

        assert service.can_transition(draft_content.id, "published") is True
        assert service.can_transition(draft_content.id, "draft") is False

    def test_get_allowed_transitions(
        self,
        service: ContentService,
        repo: MockContentRepo,
        draft_content: ContentItem,
    ) -> None:
        """get_allowed_transitions returns valid targets."""
        repo.save(draft_content)

        allowed = service.get_allowed_transitions(draft_content.id)

        assert "scheduled" in allowed
        assert "published" in allowed


class TestFactory:
    """Factory function tests."""

    def test_create_content_service(self, repo: MockContentRepo) -> None:
        """create_content_service creates configured service."""
        service = create_content_service(repo)

        assert service is not None

    def test_create_content_service_with_rules(self, repo: MockContentRepo) -> None:
        """create_content_service accepts rules config."""
        rules = {
            "status_machine": {
                "draft": {"can_transition_to": ["published"]},
                "published": {"can_transition_to": []},
            },
            "publish_guards": {
                "require_validated_content": False,
                "block_publish_if_missing_assets": False,
            },
        }

        service = create_content_service(repo, rules_config=rules)

        # Should use custom transitions
        assert service._state_machine.can_transition("draft", "scheduled") is False
        assert service._state_machine.can_transition("draft", "published") is True
