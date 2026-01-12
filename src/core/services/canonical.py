"""
CanonicalService (E7.2) - Canonical URL management after redirects.

Handles canonical URL generation and validation.

Spec refs: E7.2, TA-0047
Test assertions:
- TA-0047: Canonical tags are set correctly after redirects

Key behaviors:
- Generate canonical URLs for content
- Resolve redirects to final canonical URL
- Normalize URLs (trailing slashes, case)
- Support base URL configuration
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin, urlparse

# --- Configuration ---


@dataclass(frozen=True)
class CanonicalConfig:
    """Canonical URL configuration."""

    base_url: str = "https://example.com"
    enforce_https: bool = True
    lowercase_paths: bool = True
    strip_trailing_slash: bool = True
    strip_index_files: bool = True  # Strip /index.html, /index.php, etc.
    preserve_query_params: bool = False  # Usually strip for canonical


DEFAULT_CONFIG = CanonicalConfig()


# --- Redirect Resolver Protocol ---


class RedirectResolverPort(Protocol):
    """Interface for resolving redirects."""

    def resolve(self, path: str) -> tuple[str, int] | None:
        """Resolve path through redirects. Returns (final_path, status) or None."""
        ...


# --- URL Normalization ---


def normalize_path(
    path: str,
    config: CanonicalConfig = DEFAULT_CONFIG,
) -> str:
    """
    Normalize a URL path.

    - Adds leading slash if missing
    - Lowercases if configured
    - Strips trailing slash (except root)
    - Strips index files
    """
    if not path:
        return "/"

    # Parse if full URL
    parsed = urlparse(path)
    normalized = parsed.path or "/"

    # Ensure leading slash
    if not normalized.startswith("/"):
        normalized = "/" + normalized

    # Lowercase
    if config.lowercase_paths:
        normalized = normalized.lower()

    # Strip index files
    if config.strip_index_files:
        for index in ("/index.html", "/index.htm", "/index.php", "/default.aspx"):
            if normalized.endswith(index):
                normalized = normalized[: -len(index)] or "/"
                break

    # Strip trailing slash (except root)
    if config.strip_trailing_slash and len(normalized) > 1:
        normalized = normalized.rstrip("/")

    return normalized


def normalize_url(
    url: str,
    config: CanonicalConfig = DEFAULT_CONFIG,
) -> str:
    """
    Normalize a full URL.

    - Enforces HTTPS if configured
    - Normalizes path
    - Strips query params if configured
    """
    parsed = urlparse(url)

    # Enforce HTTPS
    scheme = parsed.scheme
    if config.enforce_https and scheme == "http":
        scheme = "https"

    # Normalize path
    path = normalize_path(parsed.path, config)

    # Build URL
    netloc = parsed.netloc.lower() if parsed.netloc else ""

    if config.preserve_query_params and parsed.query:
        return f"{scheme}://{netloc}{path}?{parsed.query}"

    return f"{scheme}://{netloc}{path}"


def build_canonical_url(
    path: str,
    base_url: str | None = None,
    config: CanonicalConfig = DEFAULT_CONFIG,
) -> str:
    """
    Build a canonical URL from a path.

    Combines base URL with normalized path.
    """
    base = base_url or config.base_url

    # Normalize path
    normalized_path = normalize_path(path, config)

    # Join with base
    full_url = urljoin(base.rstrip("/") + "/", normalized_path.lstrip("/"))

    return normalize_url(full_url, config)


# --- Canonical Service ---


class CanonicalService:
    """
    Canonical URL service (E7.2).

    Generates and validates canonical URLs, resolving redirects.
    """

    def __init__(
        self,
        redirect_resolver: RedirectResolverPort | None = None,
        config: CanonicalConfig | None = None,
    ) -> None:
        """Initialize service."""
        self._redirect_resolver = redirect_resolver
        self._config = config or DEFAULT_CONFIG

    def get_canonical(
        self,
        path: str,
        base_url: str | None = None,
    ) -> str:
        """
        Get canonical URL for a path (TA-0047).

        Resolves any redirects before building canonical URL.
        """
        final_path = path

        # Resolve redirects if resolver available
        if self._redirect_resolver:
            result = self._redirect_resolver.resolve(path)
            if result:
                final_path, _ = result

        return build_canonical_url(
            final_path,
            base_url=base_url,
            config=self._config,
        )

    def get_canonical_for_content(
        self,
        slug: str,
        content_type: str = "p",
        base_url: str | None = None,
    ) -> str:
        """
        Get canonical URL for content by slug.

        Builds path from content type and slug.
        """
        # Build content path (e.g., /p/slug or /blog/slug)
        path = f"/{content_type}/{slug}"
        return self.get_canonical(path, base_url)

    def is_canonical(self, url: str, expected_path: str) -> bool:
        """
        Check if a URL is the canonical version.

        Compares the given URL against the canonical URL.
        Returns False if the URL differs (e.g., wrong case, trailing slash).
        """
        canonical = self.get_canonical(expected_path)
        return url == canonical

    def get_redirect_target(
        self,
        current_url: str,
        expected_path: str,
    ) -> str | None:
        """
        Get redirect target if URL is not canonical.

        Returns canonical URL if different, None if already canonical.
        """
        canonical = self.get_canonical(expected_path)

        if current_url != canonical:
            return canonical

        return None

    def build_link_tag(
        self,
        path: str,
        base_url: str | None = None,
    ) -> str:
        """
        Build a canonical link tag.

        Returns HTML for <link rel="canonical" href="...">
        """
        canonical = self.get_canonical(path, base_url)
        return f'<link rel="canonical" href="{canonical}">'

    def normalize_path(self, path: str) -> str:
        """Normalize a path."""
        return normalize_path(path, self._config)

    def normalize_url(self, url: str) -> str:
        """Normalize a URL."""
        return normalize_url(url, self._config)


# --- Factory ---


def create_canonical_service(
    redirect_resolver: RedirectResolverPort | None = None,
    config: CanonicalConfig | None = None,
) -> CanonicalService:
    """Create a CanonicalService."""
    return CanonicalService(
        redirect_resolver=redirect_resolver,
        config=config,
    )
