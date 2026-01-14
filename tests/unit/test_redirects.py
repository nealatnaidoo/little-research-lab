"""
Tests for RedirectService (E7.1).

Test assertions:
- TA-0043: Loop detection prevents circular redirects
- TA-0044: Open redirect prevention (internal targets only)
- TA-0045: Chain length validation (max 3)
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.components.redirects import (
    Redirect,
    RedirectConfig,
    RedirectService,
    create_redirect_service,
    detect_loop,
    is_absolute_url,
    is_internal_path,
    normalize_path,
    validate_chain_length,
    validate_collision,
    validate_source_path,
    validate_target_path,
)

# --- Mock Repository ---


class MockRedirectRepo:
    """In-memory redirect repository for testing."""

    def __init__(self) -> None:
        self._redirects: dict[UUID, Redirect] = {}
        self._by_source: dict[str, Redirect] = {}

    def get_by_id(self, redirect_id: UUID) -> Redirect | None:
        return self._redirects.get(redirect_id)

    def get_by_source(self, source_path: str) -> Redirect | None:
        return self._by_source.get(source_path.lower())

    def save(self, redirect: Redirect) -> Redirect:
        self._redirects[redirect.id] = redirect
        self._by_source[redirect.source_path.lower()] = redirect
        return redirect

    def delete(self, redirect_id: UUID) -> None:
        redirect = self._redirects.pop(redirect_id, None)
        if redirect:
            self._by_source.pop(redirect.source_path.lower(), None)

    def list_all(self) -> list[Redirect]:
        return list(self._redirects.values())


class MockRouteChecker:
    """Mock route checker for testing."""

    def __init__(self, existing_routes: set[str] | None = None) -> None:
        self._routes = existing_routes or set()

    def route_exists(self, path: str) -> bool:
        return path.lower() in self._routes


# --- Fixtures ---


@pytest.fixture
def repo() -> MockRedirectRepo:
    """Fresh mock repository."""
    return MockRedirectRepo()


@pytest.fixture
def route_checker() -> MockRouteChecker:
    """Route checker with no existing routes."""
    return MockRouteChecker()


@pytest.fixture
def service(repo: MockRedirectRepo, route_checker: MockRouteChecker) -> RedirectService:
    """RedirectService with mock dependencies."""
    return RedirectService(repo=repo, route_checker=route_checker)


# --- Normalize Path Tests ---


class TestNormalizePath:
    """Test path normalization."""

    def test_empty_path_becomes_root(self) -> None:
        assert normalize_path("") == "/"

    def test_adds_leading_slash(self) -> None:
        assert normalize_path("foo") == "/foo"

    def test_removes_trailing_slash(self) -> None:
        assert normalize_path("/foo/") == "/foo"

    def test_root_preserved(self) -> None:
        assert normalize_path("/") == "/"

    def test_lowercases_path(self) -> None:
        assert normalize_path("/FOO/Bar") == "/foo/bar"

    def test_complex_path(self) -> None:
        assert normalize_path("foo/bar/baz/") == "/foo/bar/baz"


# --- URL Detection Tests ---


class TestIsInternalPath:
    """Test internal path detection."""

    def test_simple_path_is_internal(self) -> None:
        assert is_internal_path("/foo") is True

    def test_empty_not_internal(self) -> None:
        assert is_internal_path("") is False

    def test_http_url_not_internal(self) -> None:
        assert is_internal_path("http://example.com") is False

    def test_https_url_not_internal(self) -> None:
        assert is_internal_path("https://example.com/path") is False

    def test_protocol_relative_not_internal(self) -> None:
        assert is_internal_path("//example.com/path") is False

    def test_relative_path_internal(self) -> None:
        assert is_internal_path("relative/path") is True


class TestIsAbsoluteUrl:
    """Test absolute URL detection."""

    def test_http_is_absolute(self) -> None:
        assert is_absolute_url("http://example.com") is True

    def test_https_is_absolute(self) -> None:
        assert is_absolute_url("https://example.com/path") is True

    def test_path_not_absolute(self) -> None:
        assert is_absolute_url("/foo/bar") is False

    def test_protocol_relative_not_absolute(self) -> None:
        # No scheme, so not absolute by urlparse definition
        assert is_absolute_url("//example.com") is False

    def test_ftp_is_absolute(self) -> None:
        assert is_absolute_url("ftp://files.example.com") is True


# --- Source Path Validation Tests ---


class TestValidateSourcePath:
    """Test source path validation."""

    def test_valid_source(self) -> None:
        errors = validate_source_path("/old-page")
        assert len(errors) == 0

    def test_empty_source_rejected(self) -> None:
        errors = validate_source_path("")
        assert len(errors) == 1
        assert errors[0].code == "source_required"

    def test_source_without_slash_rejected(self) -> None:
        errors = validate_source_path("no-slash")
        assert len(errors) == 1
        assert errors[0].code == "source_must_start_with_slash"

    def test_source_url_rejected(self) -> None:
        errors = validate_source_path("https://example.com/page")
        assert any(e.code == "source_cannot_be_url" for e in errors)


# --- Target Path Validation Tests (TA-0044) ---


class TestValidateTargetPath:
    """Test TA-0044: Open redirect prevention."""

    def test_valid_internal_target(self) -> None:
        """Internal paths are allowed."""
        errors = validate_target_path("/new-page")
        assert len(errors) == 0

    def test_empty_target_rejected(self) -> None:
        """Empty target is rejected."""
        errors = validate_target_path("")
        assert len(errors) == 1
        assert errors[0].code == "target_required"

    def test_absolute_url_rejected(self) -> None:
        """TA-0044: External URLs not allowed."""
        errors = validate_target_path("https://evil.com/phish")
        assert len(errors) == 1
        assert errors[0].code == "external_target_not_allowed"

    def test_http_url_rejected(self) -> None:
        """TA-0044: HTTP URLs rejected."""
        errors = validate_target_path("http://example.com")
        assert len(errors) == 1
        assert errors[0].code == "external_target_not_allowed"

    def test_protocol_relative_rejected(self) -> None:
        """TA-0044: Protocol-relative URLs rejected."""
        errors = validate_target_path("//evil.com/path")
        assert len(errors) == 1
        assert errors[0].code == "invalid_target_path"

    def test_external_allowed_when_config_permits(self) -> None:
        """External targets allowed with config override."""
        config = RedirectConfig(require_internal_targets=False)
        errors = validate_target_path("https://example.com", config)
        assert len(errors) == 0

    def test_javascript_url_rejected(self) -> None:
        """TA-0044: JavaScript URLs rejected (not internal path)."""
        # javascript: URLs don't have netloc, so is_absolute_url is False
        # but they're not internal paths either
        errors = validate_target_path("javascript:alert(1)")
        assert len(errors) == 1
        assert errors[0].code == "invalid_target_path"


# --- Loop Detection Tests (TA-0043) ---


class TestDetectLoop:
    """Test TA-0043: Loop detection."""

    def test_no_loop_in_empty_repo(self, repo: MockRedirectRepo) -> None:
        """No loop when repo is empty."""
        errors = detect_loop("/a", "/b", repo)
        assert len(errors) == 0

    def test_direct_loop_detected(self, repo: MockRedirectRepo) -> None:
        """TA-0043: A -> A loop detected."""
        errors = detect_loop("/page", "/page", repo)
        assert len(errors) == 1
        assert errors[0].code == "redirect_loop"
        assert "itself" in errors[0].message

    def test_indirect_loop_detected(self, repo: MockRedirectRepo) -> None:
        """TA-0043: A -> B -> A loop detected."""
        # Create B -> A redirect
        now = datetime.now(UTC)
        redirect = Redirect(
            id=uuid4(),
            source_path="/b",
            target_path="/a",
            status_code=301,
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        repo.save(redirect)

        # Now try to create A -> B (would create A -> B -> A loop)
        errors = detect_loop("/a", "/b", repo)
        assert len(errors) == 1
        assert errors[0].code == "redirect_loop"

    def test_three_step_loop_detected(self, repo: MockRedirectRepo) -> None:
        """TA-0043: A -> B -> C -> A loop detected."""
        now = datetime.now(UTC)

        # Create B -> C
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/b",
                target_path="/c",
                status_code=301,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )

        # Create C -> A
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/c",
                target_path="/a",
                status_code=301,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )

        # Try to create A -> B (would create A -> B -> C -> A loop)
        errors = detect_loop("/a", "/b", repo)
        assert len(errors) == 1
        assert errors[0].code == "redirect_loop"

    def test_loop_detection_case_insensitive(self, repo: MockRedirectRepo) -> None:
        """TA-0043: Loop detection is case insensitive."""
        errors = detect_loop("/PAGE", "/page", repo)
        assert len(errors) == 1
        assert errors[0].code == "redirect_loop"

    def test_no_loop_when_disabled(self, repo: MockRedirectRepo) -> None:
        """Loop detection can be disabled via config."""
        config = RedirectConfig(prevent_loops=False)
        errors = detect_loop("/a", "/a", repo, config)
        assert len(errors) == 0


# --- Chain Length Validation Tests (TA-0045) ---


class TestValidateChainLength:
    """Test TA-0045: Chain length validation."""

    def test_single_redirect_allowed(self, repo: MockRedirectRepo) -> None:
        """Single redirect (chain of 1) is fine."""
        errors = validate_chain_length("/b", repo)
        assert len(errors) == 0

    def test_chain_of_two_allowed(self, repo: MockRedirectRepo) -> None:
        """Chain of 2 is allowed (max is 3)."""
        now = datetime.now(UTC)

        # Create B -> C
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/b",
                target_path="/c",
                status_code=301,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )

        # A -> B would make chain A -> B -> C (length 2)
        errors = validate_chain_length("/b", repo)
        assert len(errors) == 0

    def test_chain_of_three_allowed(self, repo: MockRedirectRepo) -> None:
        """Chain of 3 is allowed (exactly at max)."""
        now = datetime.now(UTC)

        # B -> C -> D chain
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/b",
                target_path="/c",
                status_code=301,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/c",
                target_path="/d",
                status_code=301,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )

        # A -> B would create A -> B -> C -> D (length 3)
        errors = validate_chain_length("/b", repo)
        assert len(errors) == 0

    def test_chain_of_four_rejected(self, repo: MockRedirectRepo) -> None:
        """TA-0045: Chain of 4 exceeds max of 3."""
        now = datetime.now(UTC)

        # B -> C -> D -> E chain (3 redirects)
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/b",
                target_path="/c",
                status_code=301,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/c",
                target_path="/d",
                status_code=301,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/d",
                target_path="/e",
                status_code=301,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )

        # A -> B would create A -> B -> C -> D -> E (length 4)
        errors = validate_chain_length("/b", repo)
        assert len(errors) == 1
        assert errors[0].code == "chain_too_long"

    def test_custom_max_chain_length(self, repo: MockRedirectRepo) -> None:
        """Custom max chain length is respected."""
        now = datetime.now(UTC)

        # B -> C
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/b",
                target_path="/c",
                status_code=301,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )

        # With max_chain_length=1, A -> B would exceed
        config = RedirectConfig(max_chain_length=1)
        errors = validate_chain_length("/b", repo, config)
        assert len(errors) == 1
        assert errors[0].code == "chain_too_long"


# --- Collision Validation Tests ---


class TestValidateCollision:
    """Test route collision detection."""

    def test_no_collision_when_route_not_exists(self) -> None:
        """No collision when route doesn't exist."""
        checker = MockRouteChecker()
        errors = validate_collision("/new-page", checker)
        assert len(errors) == 0

    def test_collision_detected(self) -> None:
        """Collision detected with existing route."""
        checker = MockRouteChecker({"/api/users"})
        errors = validate_collision("/api/users", checker)
        assert len(errors) == 1
        assert errors[0].code == "route_collision"

    def test_no_checker_means_no_validation(self) -> None:
        """Without route checker, no collision check."""
        errors = validate_collision("/api/users", None)
        assert len(errors) == 0

    def test_collision_check_disabled_in_config(self) -> None:
        """Collision check can be disabled."""
        checker = MockRouteChecker({"/api/users"})
        config = RedirectConfig(prevent_collisions_with_routes=False)
        errors = validate_collision("/api/users", checker, config)
        assert len(errors) == 0


# --- RedirectService Tests ---


class TestRedirectServiceCreate:
    """Test redirect creation."""

    def test_create_success(self, service: RedirectService) -> None:
        """Successfully create a redirect."""
        redirect, errors = service.create("/old", "/new")

        assert redirect is not None
        assert len(errors) == 0
        assert redirect.source_path == "/old"
        assert redirect.target_path == "/new"
        assert redirect.status_code == 301
        assert redirect.enabled is True

    def test_create_with_custom_status(self, service: RedirectService) -> None:
        """Create redirect with custom status code."""
        redirect, errors = service.create("/old", "/new", status_code=302)

        assert redirect is not None
        assert redirect.status_code == 302

    def test_create_with_notes(self, service: RedirectService) -> None:
        """Create redirect with notes."""
        redirect, errors = service.create("/old", "/new", notes="Migration")

        assert redirect is not None
        assert redirect.notes == "Migration"

    def test_create_duplicate_source_rejected(self, service: RedirectService) -> None:
        """Cannot create duplicate source."""
        service.create("/old", "/new1")
        redirect, errors = service.create("/old", "/new2")

        assert redirect is None
        assert len(errors) == 1
        assert errors[0].code == "source_exists"

    def test_create_validates_source(self, service: RedirectService) -> None:
        """Source path validated on create."""
        redirect, errors = service.create("no-slash", "/new")

        assert redirect is None
        assert any(e.code == "source_must_start_with_slash" for e in errors)

    def test_create_validates_target(self, service: RedirectService) -> None:
        """TA-0044: Target path validated on create."""
        redirect, errors = service.create("/old", "https://evil.com")

        assert redirect is None
        assert any(e.code == "external_target_not_allowed" for e in errors)

    def test_create_prevents_loop(
        self,
        service: RedirectService,
        repo: MockRedirectRepo,
    ) -> None:
        """TA-0043: Loop prevented on create."""
        now = datetime.now(UTC)
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/b",
                target_path="/a",
                status_code=301,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )

        redirect, errors = service.create("/a", "/b")

        assert redirect is None
        assert any(e.code == "redirect_loop" for e in errors)

    def test_create_validates_chain_length(
        self,
        service: RedirectService,
        repo: MockRedirectRepo,
    ) -> None:
        """TA-0045: Chain length validated on create."""
        now = datetime.now(UTC)

        # Create long chain: B -> C -> D -> E
        for src, tgt in [("/b", "/c"), ("/c", "/d"), ("/d", "/e")]:
            repo.save(
                Redirect(
                    id=uuid4(),
                    source_path=src,
                    target_path=tgt,
                    status_code=301,
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                )
            )

        redirect, errors = service.create("/a", "/b")

        assert redirect is None
        assert any(e.code == "chain_too_long" for e in errors)


class TestRedirectServiceGet:
    """Test redirect retrieval."""

    def test_get_by_id(self, service: RedirectService) -> None:
        """Get redirect by ID."""
        created, _ = service.create("/old", "/new")
        assert created is not None

        fetched = service.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_by_id_not_found(self, service: RedirectService) -> None:
        """Get non-existent redirect returns None."""
        fetched = service.get(uuid4())
        assert fetched is None

    def test_get_by_source(self, service: RedirectService) -> None:
        """Get redirect by source path."""
        service.create("/old", "/new")

        fetched = service.get_by_source("/old")
        assert fetched is not None
        assert fetched.target_path == "/new"

    def test_get_by_source_normalized(self, service: RedirectService) -> None:
        """Source path lookup is normalized."""
        service.create("/old", "/new")

        fetched = service.get_by_source("/OLD/")
        assert fetched is not None


class TestRedirectServiceUpdate:
    """Test redirect updates."""

    def test_update_target(self, service: RedirectService) -> None:
        """Update redirect target."""
        created, _ = service.create("/old", "/new")
        assert created is not None

        updated, errors = service.update(created.id, {"target_path": "/newer"})

        assert len(errors) == 0
        assert updated is not None
        assert updated.target_path == "/newer"

    def test_update_source(self, service: RedirectService) -> None:
        """Update redirect source."""
        created, _ = service.create("/old", "/new")
        assert created is not None

        updated, errors = service.update(created.id, {"source_path": "/older"})

        assert len(errors) == 0
        assert updated is not None
        assert updated.source_path == "/older"

    def test_update_not_found(self, service: RedirectService) -> None:
        """Update non-existent redirect fails."""
        updated, errors = service.update(uuid4(), {"target_path": "/new"})

        assert len(errors) == 1
        assert errors[0].code == "not_found"

    def test_update_validates_target(self, service: RedirectService) -> None:
        """TA-0044: Target validated on update."""
        created, _ = service.create("/old", "/new")
        assert created is not None

        updated, errors = service.update(
            created.id,
            {"target_path": "https://evil.com"},
        )

        assert any(e.code == "external_target_not_allowed" for e in errors)

    def test_update_prevents_loop(
        self,
        service: RedirectService,
        repo: MockRedirectRepo,
    ) -> None:
        """TA-0043: Loop prevented on update."""
        now = datetime.now(UTC)

        # Create A -> B
        redirect_a, _ = service.create("/a", "/b")
        assert redirect_a is not None

        # Create B -> C manually
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/c",
                target_path="/a",
                status_code=301,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )

        # Try to update A -> C (would create A -> C -> A loop)
        updated, errors = service.update(redirect_a.id, {"target_path": "/c"})

        assert any(e.code == "redirect_loop" for e in errors)


class TestRedirectServiceDelete:
    """Test redirect deletion."""

    def test_delete_success(self, service: RedirectService) -> None:
        """Delete existing redirect."""
        created, _ = service.create("/old", "/new")
        assert created is not None

        result = service.delete(created.id)
        assert result is True

        fetched = service.get(created.id)
        assert fetched is None

    def test_delete_not_found(self, service: RedirectService) -> None:
        """Delete non-existent redirect returns False."""
        result = service.delete(uuid4())
        assert result is False


class TestRedirectServiceResolve:
    """Test redirect resolution."""

    def test_resolve_single_redirect(self, service: RedirectService) -> None:
        """Resolve single redirect."""
        service.create("/old", "/new")

        result = service.resolve("/old")

        assert result is not None
        assert result[0] == "/new"
        assert result[1] == 301

    def test_resolve_chain(self, service: RedirectService) -> None:
        """Resolve redirect chain."""
        service.create("/a", "/b")
        service.create("/b", "/c")

        result = service.resolve("/a")

        assert result is not None
        assert result[0] == "/c"

    def test_resolve_no_redirect(self, service: RedirectService) -> None:
        """No redirect returns None."""
        result = service.resolve("/not-found")
        assert result is None

    def test_resolve_disabled_redirect(
        self,
        service: RedirectService,
        repo: MockRedirectRepo,
    ) -> None:
        """Disabled redirect not resolved."""
        now = datetime.now(UTC)
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/old",
                target_path="/new",
                status_code=301,
                enabled=False,
                created_at=now,
                updated_at=now,
            )
        )

        result = service.resolve("/old")
        assert result is None


class TestRedirectServiceListAll:
    """Test listing all redirects."""

    def test_list_all_empty(self, service: RedirectService) -> None:
        """List all on empty repo."""
        redirects = service.list_all()
        assert redirects == []

    def test_list_all_with_redirects(self, service: RedirectService) -> None:
        """List all redirects."""
        service.create("/a", "/b")
        service.create("/c", "/d")

        redirects = service.list_all()
        assert len(redirects) == 2


class TestRedirectServiceValidateAll:
    """Test validating all redirects."""

    def test_validate_all_clean(self, service: RedirectService) -> None:
        """All valid redirects."""
        service.create("/a", "/b")
        service.create("/c", "/d")

        results = service.validate_all()
        assert results == []

    def test_validate_all_finds_issues(
        self,
        service: RedirectService,
        repo: MockRedirectRepo,
    ) -> None:
        """Finds validation issues in existing redirects."""
        now = datetime.now(UTC)

        # Manually insert a loop
        repo.save(
            Redirect(
                id=uuid4(),
                source_path="/loop",
                target_path="/loop",
                status_code=301,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )

        results = service.validate_all()
        assert len(results) == 1
        redirect, errors = results[0]
        assert redirect.source_path == "/loop"
        assert any(e.code == "redirect_loop" for e in errors)


# --- Factory Tests ---


class TestFactory:
    """Test factory function."""

    def test_create_redirect_service(self, repo: MockRedirectRepo) -> None:
        """Factory creates service."""
        service = create_redirect_service(repo)
        assert isinstance(service, RedirectService)

    def test_create_with_route_checker(
        self,
        repo: MockRedirectRepo,
        route_checker: MockRouteChecker,
    ) -> None:
        """Factory accepts route checker."""
        service = create_redirect_service(repo, route_checker)
        assert isinstance(service, RedirectService)

    def test_create_with_custom_config(self, repo: MockRedirectRepo) -> None:
        """Factory accepts custom config."""
        config = RedirectConfig(max_chain_length=5)
        service = create_redirect_service(repo, config=config)
        assert isinstance(service, RedirectService)
