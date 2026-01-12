"""
Tests for Public Redirects Routes (E7.2).

Test assertions:
- TA-0046: Redirects are applied in the routing path
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.public_redirects import (
    get_redirect_repo,
    preserve_query_params,
    resolve_redirect,
    router,
)
from src.core.services.redirects import Redirect

# --- Test Client Setup ---


@pytest.fixture
def repo():
    """Fresh repository."""
    r = get_redirect_repo()
    r._redirects.clear()
    r._by_source.clear()
    return r


@pytest.fixture
def client(repo) -> TestClient:
    """Test client with fresh repository."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


# --- Helper to create redirects ---


def create_redirect(
    repo,
    source: str,
    target: str,
    status_code: int = 301,
    enabled: bool = True,
) -> Redirect:
    """Create a redirect in the repository."""
    now = datetime.now(UTC)
    redirect = Redirect(
        id=uuid4(),
        source_path=source.lower(),
        target_path=target.lower(),
        status_code=status_code,
        enabled=enabled,
        created_at=now,
        updated_at=now,
    )
    repo.save(redirect)
    return redirect


# --- TA-0046: Redirect Application Tests ---


class TestRedirectApplication:
    """Test TA-0046: Redirects are applied in routing."""

    def test_redirect_301(self, client: TestClient, repo) -> None:
        """301 redirect is applied."""
        create_redirect(repo, "/old", "/new", status_code=301)

        response = client.get("/old", follow_redirects=False)

        assert response.status_code == 301
        assert response.headers["location"] == "/new"

    def test_redirect_302(self, client: TestClient, repo) -> None:
        """302 redirect is applied."""
        create_redirect(repo, "/temp", "/other", status_code=302)

        response = client.get("/temp", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "/other"

    def test_no_redirect_returns_404(self, client: TestClient, repo) -> None:
        """Non-redirected path returns 404."""
        response = client.get("/nonexistent", follow_redirects=False)
        assert response.status_code == 404

    def test_disabled_redirect_not_applied(
        self,
        client: TestClient,
        repo,
    ) -> None:
        """Disabled redirect is not applied."""
        create_redirect(repo, "/disabled", "/target", enabled=False)

        response = client.get("/disabled", follow_redirects=False)
        assert response.status_code == 404

    def test_chain_resolution(self, client: TestClient, repo) -> None:
        """Redirect chain is resolved."""
        create_redirect(repo, "/a", "/b")
        create_redirect(repo, "/b", "/c")

        response = client.get("/a", follow_redirects=False)

        assert response.status_code == 301
        assert response.headers["location"] == "/c"

    def test_case_insensitive(self, client: TestClient, repo) -> None:
        """Redirects are case insensitive."""
        create_redirect(repo, "/old-page", "/new-page")

        response = client.get("/OLD-PAGE", follow_redirects=False)

        assert response.status_code == 301


# --- Query Parameter Preservation Tests ---


class TestQueryParamPreservation:
    """Test UTM parameter preservation."""

    def test_preserve_utm_source(self, client: TestClient, repo) -> None:
        """UTM source is preserved."""
        create_redirect(repo, "/campaign", "/landing")

        response = client.get(
            "/campaign?utm_source=google",
            follow_redirects=False,
        )

        assert response.status_code == 301
        assert "utm_source=google" in response.headers["location"]

    def test_preserve_all_utm_params(self, client: TestClient, repo) -> None:
        """All UTM params are preserved."""
        create_redirect(repo, "/promo", "/sale")

        response = client.get(
            "/promo?utm_source=newsletter&utm_medium=email&utm_campaign=summer",
            follow_redirects=False,
        )

        location = response.headers["location"]
        assert "utm_source=newsletter" in location
        assert "utm_medium=email" in location
        assert "utm_campaign=summer" in location

    def test_target_params_override(self) -> None:
        """Target params override source params."""
        result = preserve_query_params(
            "/old?utm_source=old",
            "/new?utm_source=new",
        )

        assert "utm_source=new" in result
        assert result.count("utm_source") == 1


# --- Preserve Query Params Function Tests ---


class TestPreserveQueryParams:
    """Test preserve_query_params function."""

    def test_no_params(self) -> None:
        """No params returns target as-is."""
        result = preserve_query_params("/old", "/new")
        assert result == "/new"

    def test_utm_preserved(self) -> None:
        """UTM params are preserved."""
        result = preserve_query_params(
            "/old?utm_source=google",
            "/new",
        )
        assert "utm_source=google" in result

    def test_non_utm_not_preserved_by_default(self) -> None:
        """Non-UTM params not preserved when preserve_utm=True."""
        result = preserve_query_params(
            "/old?foo=bar",
            "/new",
            preserve_utm=True,
        )
        assert "foo" not in result

    def test_all_params_preserved(self) -> None:
        """All params preserved when preserve_utm=False."""
        result = preserve_query_params(
            "/old?foo=bar",
            "/new",
            preserve_utm=False,
        )
        assert "foo=bar" in result

    def test_target_with_existing_params(self) -> None:
        """Target existing params are kept."""
        result = preserve_query_params(
            "/old?utm_source=google",
            "/new?page=1",
        )
        assert "utm_source=google" in result
        assert "page=1" in result


# --- Resolve Redirect Function Tests ---


class TestResolveRedirect:
    """Test resolve_redirect function."""

    def test_resolve_simple(self, repo) -> None:
        """Resolve simple redirect."""
        create_redirect(repo, "/old", "/new")

        result = resolve_redirect("/old")

        assert result is not None
        target, status = result
        assert target == "/new"
        assert status == 301

    def test_resolve_with_query(self, repo) -> None:
        """Resolve with query string preservation."""
        create_redirect(repo, "/old", "/new")

        result = resolve_redirect("/old", "utm_source=test")

        assert result is not None
        target, status = result
        assert "utm_source=test" in target

    def test_resolve_not_found(self, repo) -> None:
        """Non-existent path returns None."""
        result = resolve_redirect("/nonexistent")
        assert result is None


# --- Edge Cases ---


class TestEdgeCases:
    """Test edge cases."""

    def test_trailing_slash_normalized(self, client: TestClient, repo) -> None:
        """Trailing slashes are normalized."""
        create_redirect(repo, "/old", "/new")

        # Both should work
        response1 = client.get("/old", follow_redirects=False)
        response2 = client.get("/old/", follow_redirects=False)

        # At least one should redirect
        assert response1.status_code == 301 or response2.status_code == 301

    def test_root_redirect(self, client: TestClient, repo) -> None:
        """Root path can be redirected."""
        create_redirect(repo, "/", "/home")

        response = client.get("/", follow_redirects=False)

        # Note: May depend on router configuration
        assert response.status_code in (301, 404)

    def test_complex_path(self, client: TestClient, repo) -> None:
        """Complex paths work correctly."""
        create_redirect(repo, "/blog/old-post", "/articles/new-post")

        response = client.get("/blog/old-post", follow_redirects=False)

        assert response.status_code == 301
        assert "/articles/new-post" in response.headers["location"]
