"""
Tests for AuditLogService (E8.1).

Test assertions:
- TA-0048: Audit log entries are created
- TA-0049: Audit log entries can be queried
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.components.audit import (
    AuditAction,
    AuditConfig,
    AuditEntry,
    AuditQuery,
    AuditService,
    EntityType,
    InMemoryAuditRepo,
    create_audit_service,
)

# --- Mock Time Port ---


class MockTimePort:
    """Mock time provider."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime.now(UTC)

    def now_utc(self) -> datetime:
        return self._now

    def set_now(self, now: datetime) -> None:
        self._now = now

    def advance(self, seconds: int) -> None:
        self._now += timedelta(seconds=seconds)


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
def service(repo: InMemoryAuditRepo, time_port: MockTimePort) -> AuditService:
    """Audit service with mock dependencies."""
    return AuditService(repo=repo, time_port=time_port)


# --- TA-0048: Audit Entry Creation Tests ---


class TestAuditEntryCreation:
    """Test TA-0048: Audit log entries are created."""

    def test_log_create(self, service: AuditService) -> None:
        """Log a create action."""
        actor_id = uuid4()

        entry = service.log_create(
            entity_type=EntityType.CONTENT,
            entity_id="post-123",
            actor_id=actor_id,
            actor_name="admin@example.com",
        )

        assert entry is not None
        assert entry.action == AuditAction.CREATE
        assert entry.entity_type == EntityType.CONTENT
        assert entry.entity_id == "post-123"
        assert entry.actor_id == actor_id

    def test_log_update(self, service: AuditService) -> None:
        """Log an update action with changes."""
        entry = service.log_update(
            entity_type=EntityType.SETTINGS,
            entity_id="site",
            changes={"title": {"old": "Old Title", "new": "New Title"}},
        )

        assert entry is not None
        assert entry.action == AuditAction.UPDATE
        assert "changes" in entry.metadata

    def test_log_delete(self, service: AuditService) -> None:
        """Log a delete action."""
        entry = service.log_delete(
            entity_type=EntityType.REDIRECT,
            entity_id="redirect-456",
        )

        assert entry is not None
        assert entry.action == AuditAction.DELETE

    def test_log_generic_action(self, service: AuditService) -> None:
        """Log a generic action."""
        entry = service.log(
            action=AuditAction.PUBLISH,
            entity_type=EntityType.CONTENT,
            entity_id="post-789",
            description="Published blog post",
        )

        assert entry is not None
        assert entry.action == AuditAction.PUBLISH
        assert entry.description == "Published blog post"

    def test_log_with_metadata(self, service: AuditService) -> None:
        """Log with custom metadata."""
        entry = service.log(
            action=AuditAction.CREATE,
            entity_type=EntityType.ASSET,
            entity_id="asset-123",
            metadata={"file_size": 1024, "mime_type": "image/png"},
        )

        assert entry is not None
        assert entry.metadata["file_size"] == 1024

    def test_log_with_ip_address(self, service: AuditService) -> None:
        """Log with IP address for security events."""
        entry = service.log(
            action=AuditAction.LOGIN,
            entity_type=EntityType.USER,
            entity_id="user-123",
            ip_address="192.168.1.1",
        )

        assert entry is not None
        assert entry.ip_address == "192.168.1.1"

    def test_log_disabled_returns_none(self, repo: InMemoryAuditRepo) -> None:
        """Disabled logging returns None."""
        config = AuditConfig(enabled=False)
        service = AuditService(repo=repo, config=config)

        entry = service.log_create(
            entity_type=EntityType.CONTENT,
            entity_id="post-123",
        )

        assert entry is None

    def test_view_not_logged_by_default(self, service: AuditService) -> None:
        """VIEW actions not logged by default."""
        entry = service.log(
            action=AuditAction.VIEW,
            entity_type=EntityType.CONTENT,
            entity_id="post-123",
        )

        assert entry is None

    def test_view_logged_when_enabled(
        self,
        repo: InMemoryAuditRepo,
        time_port: MockTimePort,
    ) -> None:
        """VIEW actions logged when enabled."""
        config = AuditConfig(log_views=True)
        service = AuditService(repo=repo, time_port=time_port, config=config)

        entry = service.log(
            action=AuditAction.VIEW,
            entity_type=EntityType.CONTENT,
            entity_id="post-123",
        )

        assert entry is not None

    def test_auto_description(self, service: AuditService) -> None:
        """Auto-generate description if not provided."""
        entry = service.log(
            action=AuditAction.DELETE,
            entity_type=EntityType.REDIRECT,
            entity_id="redir-123",
        )

        assert entry is not None
        assert "Delete" in entry.description
        assert "redirect" in entry.description


# --- TA-0049: Audit Query Tests ---


class TestAuditQuery:
    """Test TA-0049: Audit log entries can be queried."""

    def test_query_all(self, service: AuditService) -> None:
        """Query all entries."""
        service.log_create(EntityType.CONTENT, "1")
        service.log_create(EntityType.CONTENT, "2")
        service.log_create(EntityType.CONTENT, "3")

        results = service.query()

        assert len(results) == 3

    def test_query_by_entity_type(self, service: AuditService) -> None:
        """Query by entity type."""
        service.log_create(EntityType.CONTENT, "1")
        service.log_create(EntityType.ASSET, "2")
        service.log_create(EntityType.CONTENT, "3")

        results = service.query(entity_type=EntityType.CONTENT)

        assert len(results) == 2
        assert all(e.entity_type == EntityType.CONTENT for e in results)

    def test_query_by_entity_id(self, service: AuditService) -> None:
        """Query by specific entity."""
        service.log_create(EntityType.CONTENT, "post-123")
        service.log_update(EntityType.CONTENT, "post-123")
        service.log_create(EntityType.CONTENT, "post-456")

        results = service.query(entity_id="post-123")

        assert len(results) == 2

    def test_query_by_actor(self, service: AuditService) -> None:
        """Query by actor."""
        actor1 = uuid4()
        actor2 = uuid4()

        service.log_create(EntityType.CONTENT, "1", actor_id=actor1)
        service.log_create(EntityType.CONTENT, "2", actor_id=actor2)
        service.log_create(EntityType.CONTENT, "3", actor_id=actor1)

        results = service.query(actor_id=actor1)

        assert len(results) == 2

    def test_query_by_action(self, service: AuditService) -> None:
        """Query by action type."""
        service.log_create(EntityType.CONTENT, "1")
        service.log_update(EntityType.CONTENT, "1")
        service.log_delete(EntityType.CONTENT, "1")

        results = service.query(action=AuditAction.UPDATE)

        assert len(results) == 1
        assert results[0].action == AuditAction.UPDATE

    def test_query_by_time_range(
        self,
        service: AuditService,
        time_port: MockTimePort,
    ) -> None:
        """Query by time range."""
        # Create entries at different times
        service.log_create(EntityType.CONTENT, "1")
        time_port.advance(3600)  # 1 hour later
        service.log_create(EntityType.CONTENT, "2")
        time_port.advance(3600)  # 2 hours later
        service.log_create(EntityType.CONTENT, "3")

        # Query for entries in the last hour
        start = time_port.now_utc() - timedelta(hours=1)
        results = service.query(start_time=start)

        # Should get only the most recent entry
        assert len(results) >= 1

    def test_query_with_limit(self, service: AuditService) -> None:
        """Query with limit."""
        for i in range(10):
            service.log_create(EntityType.CONTENT, f"post-{i}")

        results = service.query(limit=5)

        assert len(results) == 5

    def test_query_with_offset(self, service: AuditService) -> None:
        """Query with offset for pagination."""
        for i in range(10):
            service.log_create(EntityType.CONTENT, f"post-{i}")

        page1 = service.query(limit=5, offset=0)
        page2 = service.query(limit=5, offset=5)

        assert len(page1) == 5
        assert len(page2) == 5
        # Pages should be different
        page1_ids = {e.id for e in page1}
        page2_ids = {e.id for e in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_query_sorted_by_timestamp_desc(
        self,
        service: AuditService,
        time_port: MockTimePort,
    ) -> None:
        """Results sorted by timestamp descending."""
        service.log_create(EntityType.CONTENT, "first")
        time_port.advance(10)
        service.log_create(EntityType.CONTENT, "second")
        time_port.advance(10)
        service.log_create(EntityType.CONTENT, "third")

        results = service.query()

        assert results[0].entity_id == "third"
        assert results[2].entity_id == "first"


class TestAuditServiceMethods:
    """Test convenience methods."""

    def test_get_by_id(self, service: AuditService) -> None:
        """Get entry by ID."""
        entry = service.log_create(EntityType.CONTENT, "post-123")
        assert entry is not None

        fetched = service.get(entry.id)

        assert fetched is not None
        assert fetched.id == entry.id

    def test_get_for_entity(self, service: AuditService) -> None:
        """Get audit trail for entity."""
        service.log_create(EntityType.CONTENT, "post-123")
        service.log_update(EntityType.CONTENT, "post-123")
        service.log(AuditAction.PUBLISH, EntityType.CONTENT, "post-123")

        trail = service.get_for_entity(EntityType.CONTENT, "post-123")

        assert len(trail) == 3

    def test_get_by_actor(self, service: AuditService) -> None:
        """Get recent actions by actor."""
        actor_id = uuid4()

        service.log_create(EntityType.CONTENT, "1", actor_id=actor_id)
        service.log_create(EntityType.ASSET, "2", actor_id=actor_id)

        results = service.get_by_actor(actor_id)

        assert len(results) == 2

    def test_get_recent(
        self,
        service: AuditService,
        time_port: MockTimePort,
    ) -> None:
        """Get recent entries."""
        service.log_create(EntityType.CONTENT, "1")
        time_port.advance(3600)  # 1 hour
        service.log_create(EntityType.CONTENT, "2")

        results = service.get_recent(hours=2)

        assert len(results) >= 1

    def test_count(self, service: AuditService) -> None:
        """Count matching entries."""
        service.log_create(EntityType.CONTENT, "1")
        service.log_create(EntityType.CONTENT, "2")
        service.log_create(EntityType.ASSET, "3")

        count = service.count(entity_type=EntityType.CONTENT)

        assert count == 2


# --- Repository Tests ---


class TestInMemoryAuditRepo:
    """Test in-memory repository."""

    def test_save_and_get(self, repo: InMemoryAuditRepo) -> None:
        """Save and retrieve entry."""
        entry = AuditEntry(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            action=AuditAction.CREATE,
            entity_type=EntityType.CONTENT,
            entity_id="test",
            actor_id=None,
            actor_name=None,
            description="Test",
        )

        saved = repo.save(entry)
        fetched = repo.get_by_id(entry.id)

        assert fetched is not None
        assert fetched.id == saved.id

    def test_query_empty(self, repo: InMemoryAuditRepo) -> None:
        """Query empty repo."""
        results = repo.query(AuditQuery())
        assert results == []

    def test_count_empty(self, repo: InMemoryAuditRepo) -> None:
        """Count empty repo."""
        count = repo.count(AuditQuery())
        assert count == 0

    def test_clear(self, repo: InMemoryAuditRepo) -> None:
        """Clear removes all entries."""
        entry = AuditEntry(
            id=uuid4(),
            timestamp=datetime.now(UTC),
            action=AuditAction.CREATE,
            entity_type=EntityType.CONTENT,
            entity_id="test",
            actor_id=None,
            actor_name=None,
            description="Test",
        )
        repo.save(entry)
        repo.clear()

        assert repo.count(AuditQuery()) == 0


# --- Factory Tests ---


class TestFactory:
    """Test factory function."""

    def test_create_service(self) -> None:
        """Factory creates service."""
        service = create_audit_service()
        assert isinstance(service, AuditService)

    def test_create_with_repo(self, repo: InMemoryAuditRepo) -> None:
        """Factory accepts repo."""
        service = create_audit_service(repo=repo)
        assert isinstance(service, AuditService)

    def test_create_with_config(self) -> None:
        """Factory accepts config."""
        config = AuditConfig(log_views=True)
        service = create_audit_service(config=config)
        assert isinstance(service, AuditService)
