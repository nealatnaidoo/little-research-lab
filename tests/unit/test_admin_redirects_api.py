"""
Tests for Admin Redirects API (E7.1).

Test assertions:
- TA-0043: Loop detection prevents circular redirects
- TA-0044: Open redirect prevention (internal targets only)
- TA-0045: Chain length validation (max 3)
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.admin_redirects import get_redirect_repo, router
from src.components.redirects import Redirect

# --- In-Memory Repository for Testing ---


class InMemoryRedirectRepo:
    """In-memory redirect repository for testing."""

    def __init__(self) -> None:
        self._redirects: dict[UUID, Redirect] = {}
        self._by_source: dict[str, UUID] = {}

    def get_by_id(self, redirect_id: UUID) -> Redirect | None:
        return self._redirects.get(redirect_id)

    def get_by_source(self, source_path: str) -> Redirect | None:
        redirect_id = self._by_source.get(source_path)
        if redirect_id is None:
            return None
        return self._redirects.get(redirect_id)

    def save(self, redirect: Redirect) -> Redirect:
        # Remove old source mapping if updating
        if redirect.id in self._redirects:
            old = self._redirects[redirect.id]
            if old.source_path in self._by_source:
                del self._by_source[old.source_path]

        self._redirects[redirect.id] = redirect
        self._by_source[redirect.source_path] = redirect.id
        return redirect

    def delete(self, redirect_id: UUID) -> None:
        redirect = self._redirects.get(redirect_id)
        if redirect:
            if redirect.source_path in self._by_source:
                del self._by_source[redirect.source_path]
            del self._redirects[redirect_id]

    def list_all(self) -> list[Redirect]:
        return list(self._redirects.values())

    def clear(self) -> None:
        """Clear all redirects (for testing)."""
        self._redirects.clear()
        self._by_source.clear()


# --- Test Fixtures ---


@pytest.fixture
def test_repo() -> InMemoryRedirectRepo:
    """Fresh in-memory repository for each test."""
    return InMemoryRedirectRepo()


@pytest.fixture
def client(test_repo: InMemoryRedirectRepo) -> TestClient:
    """Test client with dependency override."""
    app = FastAPI()
    app.include_router(router)

    # Override the dependency
    app.dependency_overrides[get_redirect_repo] = lambda: test_repo

    return TestClient(app)


# --- Create Redirect Tests ---


class TestCreateRedirect:
    """Test redirect creation."""

    def test_create_success(self, client: TestClient) -> None:
        """Successfully create a redirect."""
        response = client.post(
            "/redirects",
            json={"source_path": "/old", "target_path": "/new"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source_path"] == "/old"
        assert data["target_path"] == "/new"
        assert data["status_code"] == 301
        assert data["enabled"] is True

    def test_create_with_custom_status(self, client: TestClient) -> None:
        """Create redirect with custom status code."""
        response = client.post(
            "/redirects",
            json={
                "source_path": "/old",
                "target_path": "/new",
                "status_code": 302,
            },
        )

        assert response.status_code == 200
        assert response.json()["status_code"] == 302

    def test_create_with_notes(self, client: TestClient) -> None:
        """Create redirect with notes."""
        response = client.post(
            "/redirects",
            json={
                "source_path": "/old",
                "target_path": "/new",
                "notes": "Migration from old site",
            },
        )

        assert response.status_code == 200
        assert response.json()["notes"] == "Migration from old site"


# --- TA-0043: Loop Detection Tests ---


class TestLoopDetection:
    """Test TA-0043: Loop detection."""

    def test_direct_loop_rejected(self, client: TestClient) -> None:
        """TA-0043: A -> A loop is rejected."""
        response = client.post(
            "/redirects",
            json={"source_path": "/page", "target_path": "/page"},
        )

        assert response.status_code == 400
        data = response.json()["detail"]
        assert any(e["code"] == "redirect_loop" for e in data["errors"])

    def test_indirect_loop_rejected(self, client: TestClient) -> None:
        """TA-0043: A -> B -> A loop is rejected."""
        # Create B -> A
        client.post(
            "/redirects",
            json={"source_path": "/b", "target_path": "/a"},
        )

        # Try to create A -> B (would create loop)
        response = client.post(
            "/redirects",
            json={"source_path": "/a", "target_path": "/b"},
        )

        assert response.status_code == 400
        data = response.json()["detail"]
        assert any(e["code"] == "redirect_loop" for e in data["errors"])


# --- TA-0044: Open Redirect Prevention Tests ---


class TestOpenRedirectPrevention:
    """Test TA-0044: Open redirect prevention."""

    def test_external_url_rejected(self, client: TestClient) -> None:
        """TA-0044: External URL is rejected."""
        response = client.post(
            "/redirects",
            json={
                "source_path": "/redirect",
                "target_path": "https://evil.com/phish",
            },
        )

        assert response.status_code == 400
        data = response.json()["detail"]
        assert any(e["code"] == "external_target_not_allowed" for e in data["errors"])

    def test_protocol_relative_rejected(self, client: TestClient) -> None:
        """TA-0044: Protocol-relative URL is rejected."""
        response = client.post(
            "/redirects",
            json={"source_path": "/redirect", "target_path": "//evil.com/path"},
        )

        assert response.status_code == 400
        data = response.json()["detail"]
        assert any(e["code"] == "invalid_target_path" for e in data["errors"])

    def test_javascript_url_rejected(self, client: TestClient) -> None:
        """TA-0044: JavaScript URL is rejected."""
        response = client.post(
            "/redirects",
            json={"source_path": "/redirect", "target_path": "javascript:alert(1)"},
        )

        assert response.status_code == 400


# --- TA-0045: Chain Length Validation Tests ---


class TestChainLengthValidation:
    """Test TA-0045: Chain length validation."""

    def test_chain_of_three_allowed(self, client: TestClient) -> None:
        """TA-0045: Chain of 3 is allowed."""
        # Create B -> C -> D chain
        client.post(
            "/redirects",
            json={"source_path": "/b", "target_path": "/c"},
        )
        client.post(
            "/redirects",
            json={"source_path": "/c", "target_path": "/d"},
        )

        # A -> B creates chain of 3 (A -> B -> C -> D)
        response = client.post(
            "/redirects",
            json={"source_path": "/a", "target_path": "/b"},
        )

        assert response.status_code == 200

    def test_chain_of_four_rejected(self, client: TestClient) -> None:
        """TA-0045: Chain of 4 exceeds max."""
        # Create B -> C -> D -> E chain
        client.post(
            "/redirects",
            json={"source_path": "/b", "target_path": "/c"},
        )
        client.post(
            "/redirects",
            json={"source_path": "/c", "target_path": "/d"},
        )
        client.post(
            "/redirects",
            json={"source_path": "/d", "target_path": "/e"},
        )

        # A -> B would create chain of 4
        response = client.post(
            "/redirects",
            json={"source_path": "/a", "target_path": "/b"},
        )

        assert response.status_code == 400
        data = response.json()["detail"]
        assert any(e["code"] == "chain_too_long" for e in data["errors"])


# --- List Redirects Tests ---


class TestListRedirects:
    """Test listing redirects."""

    def test_list_empty(self, client: TestClient) -> None:
        """List empty repository."""
        response = client.get("/redirects")

        assert response.status_code == 200
        data = response.json()
        assert data["redirects"] == []
        assert data["count"] == 0

    def test_list_with_redirects(self, client: TestClient) -> None:
        """List with multiple redirects."""
        client.post("/redirects", json={"source_path": "/a", "target_path": "/b"})
        client.post("/redirects", json={"source_path": "/c", "target_path": "/d"})

        response = client.get("/redirects")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2


# --- Get Redirect Tests ---


class TestGetRedirect:
    """Test getting a single redirect."""

    def test_get_success(self, client: TestClient) -> None:
        """Get existing redirect."""
        create_response = client.post(
            "/redirects",
            json={"source_path": "/old", "target_path": "/new"},
        )
        redirect_id = create_response.json()["id"]

        response = client.get(f"/redirects/{redirect_id}")

        assert response.status_code == 200
        assert response.json()["id"] == redirect_id

    def test_get_not_found(self, client: TestClient) -> None:
        """Get non-existent redirect."""
        response = client.get(f"/redirects/{uuid4()}")
        assert response.status_code == 404


# --- Update Redirect Tests ---


class TestUpdateRedirect:
    """Test updating redirects."""

    def test_update_target(self, client: TestClient) -> None:
        """Update redirect target."""
        create_response = client.post(
            "/redirects",
            json={"source_path": "/old", "target_path": "/new"},
        )
        redirect_id = create_response.json()["id"]

        response = client.put(
            f"/redirects/{redirect_id}",
            json={"target_path": "/newer"},
        )

        assert response.status_code == 200
        assert response.json()["target_path"] == "/newer"

    def test_update_enabled(self, client: TestClient) -> None:
        """Update enabled status."""
        create_response = client.post(
            "/redirects",
            json={"source_path": "/old", "target_path": "/new"},
        )
        redirect_id = create_response.json()["id"]

        response = client.put(
            f"/redirects/{redirect_id}",
            json={"enabled": False},
        )

        assert response.status_code == 200
        assert response.json()["enabled"] is False

    def test_update_not_found(self, client: TestClient) -> None:
        """Update non-existent redirect."""
        response = client.put(
            f"/redirects/{uuid4()}",
            json={"target_path": "/new"},
        )
        assert response.status_code == 404

    def test_update_empty_rejected(self, client: TestClient) -> None:
        """Update with no changes is rejected."""
        create_response = client.post(
            "/redirects",
            json={"source_path": "/old", "target_path": "/new"},
        )
        redirect_id = create_response.json()["id"]

        response = client.put(f"/redirects/{redirect_id}", json={})
        assert response.status_code == 400


# --- Delete Redirect Tests ---


class TestDeleteRedirect:
    """Test deleting redirects."""

    def test_delete_success(self, client: TestClient) -> None:
        """Delete existing redirect."""
        create_response = client.post(
            "/redirects",
            json={"source_path": "/old", "target_path": "/new"},
        )
        redirect_id = create_response.json()["id"]

        response = client.delete(f"/redirects/{redirect_id}")

        assert response.status_code == 200
        assert response.json()["deleted"] is True

        # Verify deleted
        get_response = client.get(f"/redirects/{redirect_id}")
        assert get_response.status_code == 404

    def test_delete_not_found(self, client: TestClient) -> None:
        """Delete non-existent redirect."""
        response = client.delete(f"/redirects/{uuid4()}")
        assert response.status_code == 404


# --- Resolve Redirect Tests ---


class TestResolveRedirect:
    """Test redirect resolution."""

    def test_resolve_single(self, client: TestClient) -> None:
        """Resolve single redirect."""
        client.post(
            "/redirects",
            json={"source_path": "/old", "target_path": "/new"},
        )

        response = client.get("/redirects/resolve/old")

        assert response.status_code == 200
        data = response.json()
        assert data["target"] == "/new"
        assert data["status_code"] == 301

    def test_resolve_chain(self, client: TestClient) -> None:
        """Resolve redirect chain."""
        client.post(
            "/redirects",
            json={"source_path": "/a", "target_path": "/b"},
        )
        client.post(
            "/redirects",
            json={"source_path": "/b", "target_path": "/c"},
        )

        response = client.get("/redirects/resolve/a")

        assert response.status_code == 200
        data = response.json()
        assert data["target"] == "/c"

    def test_resolve_not_found(self, client: TestClient) -> None:
        """Resolve non-existent redirect."""
        response = client.get("/redirects/resolve/nonexistent")
        assert response.status_code == 404


# --- Validate All Tests ---


class TestValidateAll:
    """Test validating all redirects."""

    def test_validate_all_clean(self, client: TestClient) -> None:
        """All redirects valid."""
        client.post(
            "/redirects",
            json={"source_path": "/a", "target_path": "/b"},
        )
        client.post(
            "/redirects",
            json={"source_path": "/c", "target_path": "/d"},
        )

        response = client.post("/redirects/validate")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["issues"]) == 0
        assert data["total_checked"] == 2

    def test_validate_all_empty(self, client: TestClient) -> None:
        """Validate empty repository."""
        response = client.post("/redirects/validate")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["total_checked"] == 0
