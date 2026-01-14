"""
Tests for AuditHooks (E8.1).

Test assertions:
- TA-0049: All admin actions are audited
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.components.audit import (
    AuditAction,
    AuditService,
    EntityType,
    InMemoryAuditRepo,
)
from src.shell.hooks.audit_hooks import (
    ActorContext,
    AuditHooks,
    HooksConfig,
    create_audit_hooks,
)

# --- Mock Time Port ---


class MockTimePort:
    """Mock time provider."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime.now(UTC)

    def now_utc(self) -> datetime:
        return self._now


# --- Fixtures ---


@pytest.fixture
def repo() -> InMemoryAuditRepo:
    """Fresh audit repository."""
    return InMemoryAuditRepo()


@pytest.fixture
def time_port() -> MockTimePort:
    """Mock time provider."""
    return MockTimePort()


@pytest.fixture
def audit_service(repo: InMemoryAuditRepo, time_port: MockTimePort) -> AuditService:
    """Audit service with mock dependencies."""
    return AuditService(repo=repo, time_port=time_port)


@pytest.fixture
def hooks(audit_service: AuditService) -> AuditHooks:
    """Audit hooks."""
    return AuditHooks(audit_service=audit_service)


@pytest.fixture
def actor() -> ActorContext:
    """Sample actor context."""
    return ActorContext(
        actor_id=uuid4(),
        actor_name="admin@example.com",
        ip_address="192.168.1.1",
    )


# --- Settings Hooks Tests ---


class TestSettingsHooks:
    """Test settings audit hooks (TA-0049)."""

    def test_log_settings_update(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Settings update is logged."""
        hooks.log_settings_update(
            setting_key="site_title",
            old_value="Old Title",
            new_value="New Title",
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.SETTINGS)
        assert len(results) == 1
        assert results[0].action == AuditAction.UPDATE
        assert results[0].entity_id == "site_title"
        assert results[0].actor_id == actor.actor_id

    def test_log_settings_update_captures_changes(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
    ) -> None:
        """Settings update captures old and new values."""
        hooks.log_settings_update(
            setting_key="logo_url",
            old_value="/old/logo.png",
            new_value="/new/logo.png",
        )

        results = audit_service.query(entity_type=EntityType.SETTINGS)
        assert results[0].metadata["changes"]["logo_url"]["old"] == "/old/logo.png"
        assert results[0].metadata["changes"]["logo_url"]["new"] == "/new/logo.png"

    def test_log_settings_bulk_update(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Bulk settings update is logged."""
        changes = {
            "site_title": {"old": "Old", "new": "New"},
            "description": {"old": "Old desc", "new": "New desc"},
        }

        hooks.log_settings_bulk_update(changes=changes, actor=actor)

        results = audit_service.query(entity_type=EntityType.SETTINGS)
        assert len(results) == 1
        assert results[0].entity_id == "bulk"
        assert "Updated 2 settings" in results[0].description


# --- Content Hooks Tests ---


class TestContentHooks:
    """Test content audit hooks (TA-0049)."""

    def test_log_content_create(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Content creation is logged."""
        content_id = uuid4()

        hooks.log_content_create(
            content_id=content_id,
            content_type="post",
            title="My First Post",
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.CONTENT)
        assert len(results) == 1
        assert results[0].action == AuditAction.CREATE
        assert results[0].entity_id == str(content_id)
        assert results[0].metadata["content_type"] == "post"
        assert results[0].metadata["title"] == "My First Post"

    def test_log_content_update(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Content update is logged."""
        content_id = uuid4()
        changes = {"title": {"old": "Old", "new": "New"}}

        hooks.log_content_update(
            content_id=content_id,
            changes=changes,
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.CONTENT)
        assert len(results) == 1
        assert results[0].action == AuditAction.UPDATE
        assert results[0].metadata["changes"] == changes

    def test_log_content_delete(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Content deletion is logged."""
        content_id = uuid4()

        hooks.log_content_delete(
            content_id=content_id,
            title="Deleted Post",
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.CONTENT)
        assert len(results) == 1
        assert results[0].action == AuditAction.DELETE
        assert results[0].metadata["title"] == "Deleted Post"

    def test_log_content_publish(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Content publish is logged."""
        content_id = uuid4()

        hooks.log_content_publish(content_id=content_id, actor=actor)

        results = audit_service.query(action=AuditAction.PUBLISH)
        assert len(results) == 1
        assert results[0].entity_type == EntityType.CONTENT
        assert results[0].entity_id == str(content_id)

    def test_log_content_unpublish(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Content unpublish is logged."""
        content_id = uuid4()

        hooks.log_content_unpublish(content_id=content_id, actor=actor)

        results = audit_service.query(action=AuditAction.UNPUBLISH)
        assert len(results) == 1
        assert results[0].entity_id == str(content_id)


# --- Asset Hooks Tests ---


class TestAssetHooks:
    """Test asset audit hooks (TA-0049)."""

    def test_log_asset_upload(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Asset upload is logged."""
        asset_id = uuid4()

        hooks.log_asset_upload(
            asset_id=asset_id,
            filename="document.pdf",
            mime_type="application/pdf",
            file_size=102400,
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.ASSET)
        assert len(results) == 1
        assert results[0].action == AuditAction.CREATE
        assert results[0].metadata["filename"] == "document.pdf"
        assert results[0].metadata["mime_type"] == "application/pdf"
        assert results[0].metadata["file_size"] == 102400

    def test_log_asset_update(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Asset update is logged."""
        asset_id = uuid4()
        changes = {"alt_text": {"old": "", "new": "Description"}}

        hooks.log_asset_update(
            asset_id=asset_id,
            changes=changes,
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.ASSET)
        assert len(results) == 1
        assert results[0].action == AuditAction.UPDATE

    def test_log_asset_delete(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Asset deletion is logged."""
        asset_id = uuid4()

        hooks.log_asset_delete(
            asset_id=asset_id,
            filename="deleted.pdf",
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.ASSET)
        assert len(results) == 1
        assert results[0].action == AuditAction.DELETE
        assert results[0].metadata["filename"] == "deleted.pdf"

    def test_log_asset_version_create(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Asset version creation is logged."""
        asset_id = uuid4()
        version_id = uuid4()

        hooks.log_asset_version_create(
            asset_id=asset_id,
            version_id=version_id,
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.ASSET)
        assert len(results) == 1
        assert results[0].metadata["version_id"] == str(version_id)

    def test_log_asset_latest_update(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Setting latest asset version is logged."""
        asset_id = uuid4()
        version_id = uuid4()

        hooks.log_asset_latest_update(
            asset_id=asset_id,
            version_id=version_id,
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.ASSET)
        assert len(results) == 1
        assert results[0].action == AuditAction.UPDATE
        assert results[0].metadata["latest_version_id"] == str(version_id)


# --- Schedule Hooks Tests ---


class TestScheduleHooks:
    """Test schedule audit hooks (TA-0049)."""

    def test_log_schedule_create(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Schedule creation is logged."""
        schedule_id = uuid4()
        content_id = uuid4()

        hooks.log_schedule_create(
            schedule_id=schedule_id,
            content_id=content_id,
            scheduled_for="2024-06-15T10:00:00Z",
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.SCHEDULE)
        assert len(results) == 1
        assert results[0].action == AuditAction.SCHEDULE
        assert results[0].metadata["content_id"] == str(content_id)
        assert results[0].metadata["scheduled_for"] == "2024-06-15T10:00:00Z"

    def test_log_schedule_update(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Schedule update is logged."""
        schedule_id = uuid4()
        changes = {"scheduled_for": {"old": "10:00", "new": "11:00"}}

        hooks.log_schedule_update(
            schedule_id=schedule_id,
            changes=changes,
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.SCHEDULE)
        assert len(results) == 1
        assert results[0].action == AuditAction.UPDATE

    def test_log_schedule_cancel(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Schedule cancellation is logged."""
        schedule_id = uuid4()
        content_id = uuid4()

        hooks.log_schedule_cancel(
            schedule_id=schedule_id,
            content_id=content_id,
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.SCHEDULE)
        assert len(results) == 1
        assert results[0].action == AuditAction.UNSCHEDULE
        assert results[0].metadata["content_id"] == str(content_id)

    def test_log_schedule_execute_success(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
    ) -> None:
        """Successful schedule execution is logged."""
        schedule_id = uuid4()
        content_id = uuid4()

        hooks.log_schedule_execute(
            schedule_id=schedule_id,
            content_id=content_id,
            success=True,
        )

        results = audit_service.query(entity_type=EntityType.SCHEDULE)
        assert len(results) == 1
        assert results[0].action == AuditAction.PUBLISH
        assert results[0].metadata["success"] is True
        assert results[0].metadata["system_action"] is True

    def test_log_schedule_execute_failure(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
    ) -> None:
        """Failed schedule execution is logged."""
        schedule_id = uuid4()
        content_id = uuid4()

        hooks.log_schedule_execute(
            schedule_id=schedule_id,
            content_id=content_id,
            success=False,
        )

        results = audit_service.query(entity_type=EntityType.SCHEDULE)
        assert len(results) == 1
        assert results[0].action == AuditAction.UPDATE
        assert results[0].metadata["success"] is False


# --- Redirect Hooks Tests ---


class TestRedirectHooks:
    """Test redirect audit hooks (TA-0049)."""

    def test_log_redirect_create(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Redirect creation is logged."""
        redirect_id = uuid4()

        hooks.log_redirect_create(
            redirect_id=redirect_id,
            source_path="/old-path",
            target_path="/new-path",
            status_code=301,
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.REDIRECT)
        assert len(results) == 1
        assert results[0].action == AuditAction.CREATE
        assert results[0].metadata["source"] == "/old-path"
        assert results[0].metadata["target"] == "/new-path"
        assert results[0].metadata["status_code"] == 301

    def test_log_redirect_update(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Redirect update is logged."""
        redirect_id = uuid4()
        changes = {"target": {"old": "/old", "new": "/new"}}

        hooks.log_redirect_update(
            redirect_id=redirect_id,
            changes=changes,
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.REDIRECT)
        assert len(results) == 1
        assert results[0].action == AuditAction.UPDATE

    def test_log_redirect_delete(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Redirect deletion is logged."""
        redirect_id = uuid4()

        hooks.log_redirect_delete(
            redirect_id=redirect_id,
            source_path="/deleted-path",
            actor=actor,
        )

        results = audit_service.query(entity_type=EntityType.REDIRECT)
        assert len(results) == 1
        assert results[0].action == AuditAction.DELETE
        assert results[0].metadata["source"] == "/deleted-path"

    def test_log_redirect_enable(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Redirect enable is logged."""
        redirect_id = uuid4()

        hooks.log_redirect_enable(redirect_id=redirect_id, actor=actor)

        results = audit_service.query(action=AuditAction.ENABLE)
        assert len(results) == 1
        assert results[0].entity_type == EntityType.REDIRECT

    def test_log_redirect_disable(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Redirect disable is logged."""
        redirect_id = uuid4()

        hooks.log_redirect_disable(redirect_id=redirect_id, actor=actor)

        results = audit_service.query(action=AuditAction.DISABLE)
        assert len(results) == 1
        assert results[0].entity_type == EntityType.REDIRECT


# --- Configuration Tests ---


class TestHooksConfiguration:
    """Test hooks configuration."""

    def test_disabled_hooks_do_not_log(
        self,
        audit_service: AuditService,
    ) -> None:
        """Disabled hooks don't log anything."""
        config = HooksConfig(enabled=False)
        hooks = AuditHooks(audit_service=audit_service, config=config)

        hooks.log_content_create(
            content_id=uuid4(),
            content_type="post",
            title="Test",
        )

        results = audit_service.query()
        assert len(results) == 0

    def test_hooks_without_actor(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
    ) -> None:
        """Hooks work without actor context."""
        hooks.log_content_create(
            content_id=uuid4(),
            content_type="post",
            title="Test",
        )

        results = audit_service.query()
        assert len(results) == 1
        assert results[0].actor_id is None

    def test_actor_ip_address_captured(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
    ) -> None:
        """Actor IP address is captured."""
        actor = ActorContext(
            actor_id=uuid4(),
            actor_name="admin",
            ip_address="10.0.0.1",
        )

        hooks.log_settings_update(
            setting_key="test",
            old_value="old",
            new_value="new",
            actor=actor,
        )

        results = audit_service.query()
        assert results[0].ip_address == "10.0.0.1"


# --- Factory Tests ---


class TestFactory:
    """Test factory function."""

    def test_create_audit_hooks(self, audit_service: AuditService) -> None:
        """Factory creates hooks."""
        hooks = create_audit_hooks(audit_service)
        assert isinstance(hooks, AuditHooks)

    def test_create_with_config(self, audit_service: AuditService) -> None:
        """Factory accepts config."""
        config = HooksConfig(enabled=False)
        hooks = create_audit_hooks(audit_service, config=config)
        assert isinstance(hooks, AuditHooks)


# --- Integration Tests ---


class TestAuditIntegration:
    """Test audit hooks integration with services."""

    def test_full_content_lifecycle(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Full content lifecycle is audited."""
        content_id = uuid4()

        # Create
        hooks.log_content_create(
            content_id=content_id,
            content_type="post",
            title="Draft Post",
            actor=actor,
        )

        # Update
        hooks.log_content_update(
            content_id=content_id,
            changes={"title": {"old": "Draft Post", "new": "Final Post"}},
            actor=actor,
        )

        # Publish
        hooks.log_content_publish(content_id=content_id, actor=actor)

        # Verify all logged
        results = audit_service.get_for_entity(EntityType.CONTENT, str(content_id))
        assert len(results) == 3

        actions = [r.action for r in results]
        assert AuditAction.CREATE in actions
        assert AuditAction.UPDATE in actions
        assert AuditAction.PUBLISH in actions

    def test_full_redirect_lifecycle(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Full redirect lifecycle is audited."""
        redirect_id = uuid4()

        # Create
        hooks.log_redirect_create(
            redirect_id=redirect_id,
            source_path="/old",
            target_path="/new",
            status_code=301,
            actor=actor,
        )

        # Disable
        hooks.log_redirect_disable(redirect_id=redirect_id, actor=actor)

        # Enable
        hooks.log_redirect_enable(redirect_id=redirect_id, actor=actor)

        # Delete
        hooks.log_redirect_delete(
            redirect_id=redirect_id,
            source_path="/old",
            actor=actor,
        )

        results = audit_service.get_for_entity(EntityType.REDIRECT, str(redirect_id))
        assert len(results) == 4

    def test_query_by_actor(
        self,
        hooks: AuditHooks,
        audit_service: AuditService,
        actor: ActorContext,
    ) -> None:
        """Can query all actions by specific actor."""
        # Log various actions
        hooks.log_content_create(uuid4(), "post", "Post 1", actor=actor)
        hooks.log_settings_update("key", "old", "new", actor=actor)
        hooks.log_redirect_create(uuid4(), "/a", "/b", 301, actor=actor)

        results = audit_service.query(actor_id=actor.actor_id)
        assert len(results) == 3
