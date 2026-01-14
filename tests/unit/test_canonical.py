"""
Tests for CanonicalService (E7.2).

Test assertions:
- TA-0047: Canonical tags are set correctly after redirects
"""

from __future__ import annotations

import pytest

from src.components.render import (
    CanonicalConfig,
    CanonicalService,
    create_canonical_service,
    normalize_path,
    normalize_url,
)
from src.components.render import (
    build_canonical_url_with_config as build_canonical_url,
)

# --- Mock Redirect Resolver ---


class MockRedirectResolver:
    """Mock redirect resolver for testing."""

    def __init__(self, redirects: dict[str, str] | None = None) -> None:
        self._redirects = redirects or {}

    def resolve(self, path: str) -> tuple[str, int] | None:
        """Resolve redirect."""
        normalized = path.lower().rstrip("/") or "/"
        if normalized in self._redirects:
            return self._redirects[normalized], 301
        return None

    def add_redirect(self, source: str, target: str) -> None:
        """Add a redirect."""
        self._redirects[source.lower().rstrip("/") or "/"] = target


# --- Fixtures ---


@pytest.fixture
def config() -> CanonicalConfig:
    """Default config."""
    return CanonicalConfig(base_url="https://example.com")


@pytest.fixture
def redirect_resolver() -> MockRedirectResolver:
    """Mock resolver."""
    return MockRedirectResolver()


@pytest.fixture
def service(
    redirect_resolver: MockRedirectResolver,
    config: CanonicalConfig,
) -> CanonicalService:
    """Canonical service."""
    return CanonicalService(redirect_resolver=redirect_resolver, config=config)


# --- Path Normalization Tests ---


class TestNormalizePath:
    """Test path normalization."""

    def test_empty_path_becomes_root(self) -> None:
        """Empty path becomes /."""
        assert normalize_path("") == "/"

    def test_adds_leading_slash(self) -> None:
        """Adds leading slash."""
        assert normalize_path("page") == "/page"

    def test_removes_trailing_slash(self) -> None:
        """Removes trailing slash."""
        assert normalize_path("/page/") == "/page"

    def test_root_preserved(self) -> None:
        """Root path preserved."""
        assert normalize_path("/") == "/"

    def test_lowercases(self) -> None:
        """Lowercases path."""
        assert normalize_path("/Page/SubPage") == "/page/subpage"

    def test_strips_index_html(self) -> None:
        """Strips index.html."""
        assert normalize_path("/page/index.html") == "/page"

    def test_strips_index_php(self) -> None:
        """Strips index.php."""
        assert normalize_path("/page/index.php") == "/page"

    def test_root_index_html(self) -> None:
        """Root index.html becomes /."""
        assert normalize_path("/index.html") == "/"

    def test_complex_path(self) -> None:
        """Complex path normalized."""
        assert normalize_path("/Blog/Posts/Hello-World/") == "/blog/posts/hello-world"


class TestNormalizeUrl:
    """Test URL normalization."""

    def test_full_url(self) -> None:
        """Normalizes full URL."""
        result = normalize_url("https://EXAMPLE.COM/Page/")
        assert result == "https://example.com/page"

    def test_enforces_https(self) -> None:
        """HTTP upgraded to HTTPS."""
        result = normalize_url("http://example.com/page")
        assert result == "https://example.com/page"

    def test_strips_query_by_default(self) -> None:
        """Query params stripped by default."""
        result = normalize_url("https://example.com/page?ref=123")
        assert result == "https://example.com/page"

    def test_preserves_query_when_configured(self) -> None:
        """Query preserved when configured."""
        config = CanonicalConfig(preserve_query_params=True)
        result = normalize_url("https://example.com/page?ref=123", config)
        assert "ref=123" in result


class TestBuildCanonicalUrl:
    """Test canonical URL building."""

    def test_simple_path(self) -> None:
        """Build from simple path."""
        config = CanonicalConfig(base_url="https://example.com")
        result = build_canonical_url("/page", config=config)
        assert result == "https://example.com/page"

    def test_with_base_url(self) -> None:
        """Override base URL."""
        config = CanonicalConfig(base_url="https://default.com")
        result = build_canonical_url("/page", base_url="https://custom.com", config=config)
        assert result == "https://custom.com/page"

    def test_normalizes_path(self) -> None:
        """Path is normalized."""
        config = CanonicalConfig(base_url="https://example.com")
        result = build_canonical_url("/Page/SubPage/", config=config)
        assert result == "https://example.com/page/subpage"


# --- TA-0047: Canonical After Redirects Tests ---


class TestCanonicalAfterRedirects:
    """Test TA-0047: Canonical tags after redirects."""

    def test_canonical_without_redirect(
        self,
        service: CanonicalService,
    ) -> None:
        """Canonical for path without redirect."""
        result = service.get_canonical("/page")
        assert result == "https://example.com/page"

    def test_canonical_resolves_redirect(
        self,
        service: CanonicalService,
        redirect_resolver: MockRedirectResolver,
    ) -> None:
        """TA-0047: Canonical resolves redirect to final URL."""
        redirect_resolver.add_redirect("/old-page", "/new-page")

        result = service.get_canonical("/old-page")

        assert result == "https://example.com/new-page"

    def test_canonical_resolves_chain(
        self,
        service: CanonicalService,
        redirect_resolver: MockRedirectResolver,
    ) -> None:
        """TA-0047: Canonical resolves redirect chain."""
        # Setup: /a -> /b (resolver already follows chain)
        redirect_resolver.add_redirect("/a", "/b")

        result = service.get_canonical("/a")

        assert result == "https://example.com/b"

    def test_canonical_normalizes_final_path(
        self,
        service: CanonicalService,
        redirect_resolver: MockRedirectResolver,
    ) -> None:
        """TA-0047: Final path is normalized."""
        redirect_resolver.add_redirect("/old", "/New-Page/")

        result = service.get_canonical("/old")

        assert result == "https://example.com/new-page"


class TestCanonicalService:
    """Test CanonicalService methods."""

    def test_get_canonical_for_content(
        self,
        service: CanonicalService,
    ) -> None:
        """Get canonical for content slug."""
        result = service.get_canonical_for_content("hello-world", "p")
        assert result == "https://example.com/p/hello-world"

    def test_get_canonical_for_blog(
        self,
        service: CanonicalService,
    ) -> None:
        """Get canonical for blog content."""
        result = service.get_canonical_for_content("my-post", "blog")
        assert result == "https://example.com/blog/my-post"

    def test_is_canonical_true(self, service: CanonicalService) -> None:
        """URL is canonical."""
        assert (
            service.is_canonical(
                "https://example.com/page",
                "/page",
            )
            is True
        )

    def test_is_canonical_false_different_case(
        self,
        service: CanonicalService,
    ) -> None:
        """URL differs from canonical (case)."""
        assert (
            service.is_canonical(
                "https://example.com/PAGE",
                "/page",
            )
            is False
        )

    def test_is_canonical_false_trailing_slash(
        self,
        service: CanonicalService,
    ) -> None:
        """URL differs from canonical (trailing slash)."""
        assert (
            service.is_canonical(
                "https://example.com/page/",
                "/page",
            )
            is False
        )

    def test_get_redirect_target_needed(
        self,
        service: CanonicalService,
    ) -> None:
        """Redirect needed to canonical."""
        result = service.get_redirect_target(
            "https://example.com/PAGE/",
            "/page",
        )
        assert result == "https://example.com/page"

    def test_get_redirect_target_not_needed(
        self,
        service: CanonicalService,
    ) -> None:
        """No redirect needed."""
        result = service.get_redirect_target(
            "https://example.com/page",
            "/page",
        )
        assert result is None

    def test_build_link_tag(self, service: CanonicalService) -> None:
        """Build canonical link tag."""
        result = service.build_link_tag("/page")
        assert result == '<link rel="canonical" href="https://example.com/page">'

    def test_normalize_path_method(self, service: CanonicalService) -> None:
        """Service normalize_path method."""
        assert service.normalize_path("/Page/") == "/page"

    def test_normalize_url_method(self, service: CanonicalService) -> None:
        """Service normalize_url method."""
        result = service.normalize_url("http://example.com/Page/")
        assert result == "https://example.com/page"


class TestCanonicalWithoutResolver:
    """Test service without redirect resolver."""

    def test_get_canonical_no_resolver(self) -> None:
        """Works without redirect resolver."""
        config = CanonicalConfig(base_url="https://example.com")
        service = CanonicalService(config=config)

        result = service.get_canonical("/page")

        assert result == "https://example.com/page"


# --- Config Tests ---


class TestCanonicalConfig:
    """Test configuration options."""

    def test_disable_https_enforcement(self) -> None:
        """Disable HTTPS enforcement."""
        config = CanonicalConfig(
            base_url="http://example.com",
            enforce_https=False,
        )
        result = build_canonical_url("/page", config=config)
        assert result.startswith("http://")

    def test_disable_lowercase(self) -> None:
        """Disable lowercase normalization."""
        config = CanonicalConfig(
            base_url="https://example.com",
            lowercase_paths=False,
        )
        result = normalize_path("/Page", config)
        assert result == "/Page"

    def test_keep_trailing_slash(self) -> None:
        """Keep trailing slash."""
        config = CanonicalConfig(
            base_url="https://example.com",
            strip_trailing_slash=False,
        )
        result = normalize_path("/page/", config)
        assert result == "/page/"


# --- Factory Tests ---


class TestFactory:
    """Test factory function."""

    def test_create_service(self) -> None:
        """Factory creates service."""
        service = create_canonical_service()
        assert isinstance(service, CanonicalService)

    def test_create_with_resolver(
        self,
        redirect_resolver: MockRedirectResolver,
    ) -> None:
        """Factory accepts resolver."""
        service = create_canonical_service(redirect_resolver=redirect_resolver)
        assert isinstance(service, CanonicalService)

    def test_create_with_config(self, config: CanonicalConfig) -> None:
        """Factory accepts config."""
        service = create_canonical_service(config=config)
        assert isinstance(service, CanonicalService)
