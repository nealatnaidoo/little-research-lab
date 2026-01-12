"""
RenderService (E1.2) - SSR metadata builder.

Builds deterministic page metadata from content + settings for public SSR pages.
Implements C2 from the spec.

Spec refs: E1.2, TA-0004, TA-0005, R6
Test assertions:
- TA-0004: SSR meta snapshot (title, description, canonical, OG, Twitter)
- TA-0005: OG image resolution rules (content > settings > default)

Key behaviors:
- Builds <title>, meta description, canonical URL
- Generates OG and Twitter Card meta tags
- Resolves OG image with fallback chain
- Pure function: same inputs always produce same outputs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.entities import ContentItem, SiteSettings

# --- Metadata Models ---


@dataclass
class MetaTag:
    """HTML meta tag representation."""

    name: str | None = None
    property: str | None = None  # For OG tags
    content: str = ""


@dataclass
class PageMetadata:
    """
    Complete page metadata for SSR rendering.

    Contains all data needed to render <head> content.
    """

    title: str
    description: str
    canonical_url: str
    robots: str = "index, follow"

    # OpenGraph tags
    og_title: str = ""
    og_description: str = ""
    og_type: str = "website"
    og_url: str = ""
    og_image: str = ""
    og_image_alt: str = ""
    og_site_name: str = ""

    # Twitter Card tags
    twitter_card: str = "summary_large_image"
    twitter_title: str = ""
    twitter_description: str = ""
    twitter_image: str = ""
    twitter_image_alt: str = ""

    # Additional meta tags
    extra_meta: list[MetaTag] = field(default_factory=list)

    def to_meta_tags(self) -> list[MetaTag]:
        """Convert to list of MetaTag objects for rendering."""
        tags = [
            MetaTag(name="description", content=self.description),
            MetaTag(name="robots", content=self.robots),
            MetaTag(property="og:title", content=self.og_title or self.title),
            MetaTag(property="og:description", content=self.og_description or self.description),
            MetaTag(property="og:type", content=self.og_type),
            MetaTag(property="og:url", content=self.og_url or self.canonical_url),
        ]

        if self.og_image:
            tags.append(MetaTag(property="og:image", content=self.og_image))
            if self.og_image_alt:
                tags.append(MetaTag(property="og:image:alt", content=self.og_image_alt))

        if self.og_site_name:
            tags.append(MetaTag(property="og:site_name", content=self.og_site_name))

        # Twitter Card
        tags.extend(
            [
                MetaTag(name="twitter:card", content=self.twitter_card),
                MetaTag(
                    name="twitter:title", content=self.twitter_title or self.og_title or self.title
                ),
                MetaTag(
                    name="twitter:description",
                    content=self.twitter_description or self.og_description or self.description,
                ),
            ]
        )

        if self.twitter_image or self.og_image:
            tags.append(MetaTag(name="twitter:image", content=self.twitter_image or self.og_image))
            alt = self.twitter_image_alt or self.og_image_alt
            if alt:
                tags.append(MetaTag(name="twitter:image:alt", content=alt))

        tags.extend(self.extra_meta)
        return tags


# --- Image Resolution ---


@dataclass
class ImageInfo:
    """Resolved image information."""

    url: str
    alt: str = ""


def resolve_og_image(
    content_image_url: str | None,
    settings_og_image_url: str | None,
    default_image_url: str | None = None,
) -> ImageInfo | None:
    """
    Resolve OG image using fallback chain (TA-0005).

    Resolution order:
    1. Content-specific image (highest priority)
    2. Site settings OG image
    3. Default image (lowest priority)

    Returns None if no image available.
    """
    if content_image_url:
        return ImageInfo(url=content_image_url)
    if settings_og_image_url:
        return ImageInfo(url=settings_og_image_url)
    if default_image_url:
        return ImageInfo(url=default_image_url)
    return None


# --- Canonical URL Building ---


def build_canonical_url(base_url: str, path: str) -> str:
    """
    Build canonical URL from base URL and path.

    Ensures proper URL formatting.
    """
    # Remove trailing slash from base, ensure path starts with /
    base = base_url.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path

    return f"{base}{path}"


def get_content_path(content: ContentItem, routing_config: dict[str, Any]) -> str:
    """
    Get the URL path for a content item based on routing config.

    Uses namespace prefixes from rules.routing.
    """
    posts_prefix = routing_config.get("posts_prefix", "/p")
    resources_prefix = routing_config.get("resources_prefix", "/r")

    if content.type == "post":
        return f"{posts_prefix}/{content.slug}"
    else:
        # resource_pdf or other types
        return f"{resources_prefix}/{content.slug}"


# --- Description Truncation ---


def truncate_description(text: str, max_length: int = 160) -> str:
    """
    Truncate description to fit meta description limits.

    Breaks at word boundary if possible.
    """
    if len(text) <= max_length:
        return text

    # Find last space before limit
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")

    if last_space > max_length * 0.6:  # At least 60% of the text
        truncated = truncated[:last_space]

    return truncated.rstrip() + "..."


# --- Main Render Service ---


class RenderService:
    """
    SSR metadata builder service (C2).

    Provides deterministic page metadata generation from content and settings.
    Pure functions: same inputs always produce same outputs.
    """

    def __init__(
        self,
        base_url: str,
        default_og_image_url: str | None = None,
        routing_config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize render service.

        Args:
            base_url: Site base URL for canonical URLs
            default_og_image_url: Default OG image if none specified
            routing_config: Routing configuration from rules
        """
        self._base_url = base_url.rstrip("/")
        self._default_og_image = default_og_image_url
        self._routing = routing_config or {}

    def build_page_metadata(
        self,
        settings: SiteSettings,
        content: ContentItem | None = None,
        path: str = "/",
        page_title: str | None = None,
        page_description: str | None = None,
        og_image_url: str | None = None,
    ) -> PageMetadata:
        """
        Build complete page metadata (TA-0004).

        Args:
            settings: Site settings for defaults
            content: Optional content item for content pages
            path: URL path (used if content not provided)
            page_title: Override title
            page_description: Override description
            og_image_url: Override OG image

        Returns:
            PageMetadata with all required fields
        """
        # Determine title
        if page_title:
            title = page_title
        elif content:
            title = f"{content.title} | {settings.site_title}"
        else:
            title = settings.site_title

        # Determine description
        if page_description:
            description = truncate_description(page_description)
        elif content and content.summary:
            description = truncate_description(content.summary)
        else:
            description = truncate_description(settings.site_subtitle)

        # Determine canonical URL
        if content:
            content_path = get_content_path(content, self._routing)
            canonical = build_canonical_url(self._base_url, content_path)
        else:
            canonical = build_canonical_url(self._base_url, path)

        # Resolve OG image (TA-0005)
        # Get settings OG image if available (from social_links_json or avatar)
        settings_og_image = self._get_settings_og_image(settings)
        image = resolve_og_image(og_image_url, settings_og_image, self._default_og_image)

        return PageMetadata(
            title=title,
            description=description,
            canonical_url=canonical,
            og_title=content.title if content else settings.site_title,
            og_description=description,
            og_type="article" if content else "website",
            og_url=canonical,
            og_image=image.url if image else "",
            og_image_alt=image.alt if image else "",
            og_site_name=settings.site_title,
            twitter_card="summary_large_image" if image else "summary",
        )

    def build_content_metadata(
        self,
        settings: SiteSettings,
        content: ContentItem,
        og_image_url: str | None = None,
    ) -> PageMetadata:
        """
        Build metadata for a content page.

        Convenience method for content-specific pages.
        """
        return self.build_page_metadata(
            settings=settings,
            content=content,
            og_image_url=og_image_url,
        )

    def build_homepage_metadata(
        self,
        settings: SiteSettings,
        og_image_url: str | None = None,
    ) -> PageMetadata:
        """
        Build metadata for the homepage.

        Convenience method for the site homepage.
        """
        return self.build_page_metadata(
            settings=settings,
            path="/",
            page_title=settings.site_title,
            page_description=settings.site_subtitle,
            og_image_url=og_image_url,
        )

    def _get_settings_og_image(self, settings: SiteSettings) -> str | None:
        """Get OG image URL from settings."""
        # Check social_links_json for og_image
        if settings.social_links_json:
            og_image = settings.social_links_json.get("og_image")
            if og_image:
                return og_image

        # Could also use avatar if it's an image asset
        # This would require asset URL resolution, handled by caller
        return None


# --- Factory ---


def create_render_service(
    base_url: str,
    default_og_image_url: str | None = None,
    routing_config: dict[str, Any] | None = None,
) -> RenderService:
    """
    Create a render service.

    Args:
        base_url: Site base URL
        default_og_image_url: Default OG image
        routing_config: Routing configuration

    Returns:
        Configured RenderService
    """
    return RenderService(base_url, default_og_image_url, routing_config)
