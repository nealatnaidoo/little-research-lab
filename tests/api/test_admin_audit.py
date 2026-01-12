"""
Tests for Admin Audit Log API (E8.1).

Test assertions:
- TA-0049: Audit logs can be queried and viewed
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import admin_audit
from src.core.services.audit import (
    AuditAction,
    AuditService,
    EntityType,
    InMemoryAuditRepo,
)

# --- Test Setup ---


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
    """Audit service with test repo."""
    return AuditService(repo=repo, time_port=time_port)


@pytest.fixture
def app(audit_service: AuditService) -> FastAPI:
    """Test FastAPI app with audit routes."""
    app = FastAPI()
    app.include_router(admin_audit.router, prefix="/audit")

    app.dependency_overrides[admin_audit.get_audit_service] = lambda: audit_service

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Test client."""
    return TestClient(app)


# --- TA-0049: Query Tests ---


class TestQueryAuditLogs:
    """Test audit log query endpoint (TA-0049)."""

    def test_query_empty(self, client: TestClient) -> None:
        """Empty query returns empty list."""
        response = client.get("/audit")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_query_returns_entries(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Query returns audit entries."""
        audit_service.log_create(EntityType.CONTENT, "post-1")
        audit_service.log_create(EntityType.CONTENT, "post-2")

        response = client.get("/audit")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2

    def test_query_filter_by_entity_type(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Can filter by entity type."""
        audit_service.log_create(EntityType.CONTENT, "post-1")
        audit_service.log_create(EntityType.ASSET, "asset-1")
        audit_service.log_create(EntityType.CONTENT, "post-2")

        response = client.get("/audit", params={"entity_type": "content"})

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert all(i["entity_type"] == "content" for i in data["items"])

    def test_query_filter_by_entity_id(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Can filter by entity ID."""
        audit_service.log_create(EntityType.CONTENT, "post-123")
        audit_service.log_update(EntityType.CONTENT, "post-123")
        audit_service.log_create(EntityType.CONTENT, "post-456")

        response = client.get("/audit", params={"entity_id": "post-123"})

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    def test_query_filter_by_action(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Can filter by action."""
        audit_service.log_create(EntityType.CONTENT, "1")
        audit_service.log_update(EntityType.CONTENT, "1")
        audit_service.log_delete(EntityType.CONTENT, "1")

        response = client.get("/audit", params={"action": "update"})

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["action"] == "update"

    def test_query_filter_by_actor(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Can filter by actor ID."""
        actor1 = uuid4()
        actor2 = uuid4()

        audit_service.log_create(EntityType.CONTENT, "1", actor_id=actor1)
        audit_service.log_create(EntityType.CONTENT, "2", actor_id=actor2)
        audit_service.log_create(EntityType.CONTENT, "3", actor_id=actor1)

        response = client.get("/audit", params={"actor_id": str(actor1)})

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    def test_query_pagination(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Pagination works correctly."""
        for i in range(10):
            audit_service.log_create(EntityType.CONTENT, f"post-{i}")

        response = client.get("/audit", params={"limit": 5, "offset": 0})
        page1 = response.json()

        response = client.get("/audit", params={"limit": 5, "offset": 5})
        page2 = response.json()

        assert len(page1["items"]) == 5
        assert len(page2["items"]) == 5
        assert page1["total"] == 10
        assert page2["total"] == 10

        # Pages should be different
        page1_ids = {i["id"] for i in page1["items"]}
        page2_ids = {i["id"] for i in page2["items"]}
        assert page1_ids.isdisjoint(page2_ids)

    def test_query_invalid_entity_type(self, client: TestClient) -> None:
        """Invalid entity type returns 400."""
        response = client.get("/audit", params={"entity_type": "invalid"})

        assert response.status_code == 400

    def test_query_invalid_action(self, client: TestClient) -> None:
        """Invalid action returns 400."""
        response = client.get("/audit", params={"action": "invalid"})

        assert response.status_code == 400

    def test_query_invalid_actor_id(self, client: TestClient) -> None:
        """Invalid actor ID returns 400."""
        response = client.get("/audit", params={"actor_id": "not-a-uuid"})

        assert response.status_code == 400


class TestRecentAuditLogs:
    """Test recent audit logs endpoint (TA-0049)."""

    def test_get_recent_empty(self, client: TestClient) -> None:
        """Empty returns empty list."""
        response = client.get("/audit/recent")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_get_recent_returns_entries(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Returns recent entries."""
        audit_service.log_create(EntityType.CONTENT, "1")
        audit_service.log_create(EntityType.CONTENT, "2")

        response = client.get("/audit/recent")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    def test_get_recent_with_limit(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Respects limit parameter."""
        for i in range(10):
            audit_service.log_create(EntityType.CONTENT, f"post-{i}")

        response = client.get("/audit/recent", params={"limit": 5})

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5


class TestEntityHistory:
    """Test entity history endpoint (TA-0049)."""

    def test_get_entity_history_empty(self, client: TestClient) -> None:
        """Empty entity returns empty list."""
        response = client.get("/audit/entity/content/post-123")

        assert response.status_code == 200
        data = response.json()
        assert data["entries"] == []

    def test_get_entity_history_returns_entries(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Returns full entity history."""
        audit_service.log_create(EntityType.CONTENT, "post-123")
        audit_service.log_update(EntityType.CONTENT, "post-123")
        audit_service.log(AuditAction.PUBLISH, EntityType.CONTENT, "post-123")

        response = client.get("/audit/entity/content/post-123")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 3
        assert data["entity_type"] == "content"
        assert data["entity_id"] == "post-123"

    def test_get_entity_history_invalid_type(self, client: TestClient) -> None:
        """Invalid entity type returns 400."""
        response = client.get("/audit/entity/invalid/123")

        assert response.status_code == 400


class TestActorActivity:
    """Test actor activity endpoint (TA-0049)."""

    def test_get_actor_activity_empty(self, client: TestClient) -> None:
        """Unknown actor returns empty list."""
        response = client.get(f"/audit/actor/{uuid4()}")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_get_actor_activity_returns_entries(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Returns all activity by actor."""
        actor_id = uuid4()

        audit_service.log_create(EntityType.CONTENT, "1", actor_id=actor_id)
        audit_service.log_create(EntityType.ASSET, "2", actor_id=actor_id)
        audit_service.log_update(EntityType.SETTINGS, "site", actor_id=actor_id)

        response = client.get(f"/audit/actor/{actor_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

    def test_get_actor_activity_invalid_uuid(self, client: TestClient) -> None:
        """Invalid UUID returns 400."""
        response = client.get("/audit/actor/not-a-uuid")

        assert response.status_code == 400


class TestGetAuditEntry:
    """Test get single entry endpoint (TA-0049)."""

    def test_get_entry_not_found(self, client: TestClient) -> None:
        """Unknown entry returns 404."""
        response = client.get(f"/audit/{uuid4()}")

        assert response.status_code == 404

    def test_get_entry_returns_entry(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Returns entry by ID."""
        entry = audit_service.log_create(EntityType.CONTENT, "post-123")
        assert entry is not None

        response = client.get(f"/audit/{entry.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(entry.id)
        assert data["entity_type"] == "content"
        assert data["entity_id"] == "post-123"

    def test_get_entry_invalid_uuid(self, client: TestClient) -> None:
        """Invalid UUID returns 400."""
        response = client.get("/audit/not-a-uuid")

        assert response.status_code == 400


class TestAuditSummary:
    """Test audit summary endpoint (TA-0049)."""

    def test_summary_empty(self, client: TestClient) -> None:
        """Empty returns zero counts."""
        response = client.get("/audit/stats/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["by_action"] == {}
        assert data["by_entity_type"] == {}

    def test_summary_counts_actions(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Counts actions correctly."""
        audit_service.log_create(EntityType.CONTENT, "1")
        audit_service.log_create(EntityType.CONTENT, "2")
        audit_service.log_update(EntityType.CONTENT, "1")
        audit_service.log_delete(EntityType.CONTENT, "2")

        response = client.get("/audit/stats/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert data["by_action"]["create"] == 2
        assert data["by_action"]["update"] == 1
        assert data["by_action"]["delete"] == 1

    def test_summary_counts_entity_types(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Counts entity types correctly."""
        audit_service.log_create(EntityType.CONTENT, "1")
        audit_service.log_create(EntityType.CONTENT, "2")
        audit_service.log_create(EntityType.ASSET, "1")
        audit_service.log_create(EntityType.REDIRECT, "1")

        response = client.get("/audit/stats/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["by_entity_type"]["content"] == 2
        assert data["by_entity_type"]["asset"] == 1
        assert data["by_entity_type"]["redirect"] == 1


class TestEntryResponseFormat:
    """Test response format."""

    def test_entry_has_all_fields(
        self,
        client: TestClient,
        audit_service: AuditService,
    ) -> None:
        """Entry response has all expected fields."""
        actor_id = uuid4()

        entry = audit_service.log(
            action=AuditAction.CREATE,
            entity_type=EntityType.CONTENT,
            entity_id="post-123",
            actor_id=actor_id,
            actor_name="admin@example.com",
            description="Created post",
            metadata={"title": "Test Post"},
            ip_address="192.168.1.1",
        )
        assert entry is not None

        response = client.get(f"/audit/{entry.id}")

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert "timestamp" in data
        assert data["action"] == "create"
        assert data["entity_type"] == "content"
        assert data["entity_id"] == "post-123"
        assert data["actor_id"] == str(actor_id)
        assert data["actor_name"] == "admin@example.com"
        assert data["description"] == "Created post"
        assert data["metadata"] == {"title": "Test Post"}
        assert data["ip_address"] == "192.168.1.1"
