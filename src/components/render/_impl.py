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


# --- Social Meta Tag Generation (E15.3) ---


@dataclass
class ImageDimensionConfig:
    """Configuration for image dimension validation."""

    min_width: int
    min_height: int


DEFAULT_TWITTER_IMAGE_CONFIG = ImageDimensionConfig(min_width=280, min_height=150)
DEFAULT_FACEBOOK_IMAGE_CONFIG = ImageDimensionConfig(min_width=200, min_height=200)


def validate_image_dimensions(
    width: int | None,
    height: int | None,
    min_width: int,
    min_height: int,
) -> tuple[bool, str | None]:
    """
    Validate image dimensions meet minimum requirements.

    Args:
        width: Image width in pixels (None if unknown)
        height: Image height in pixels (None if unknown)
        min_width: Minimum required width
        min_height: Minimum required height

    Returns:
        Tuple of (is_valid, warning_message)
    """
    if width is None or height is None:
        # Can't validate without dimensions, assume valid
        return True, None

    if width < min_width or height < min_height:
        return False, f"Image dimensions {width}x{height} below minimum {min_width}x{min_height}"

    return True, None


def generate_twitter_card_meta(
    title: str,
    description: str,
    image_url: str | None = None,
    image_alt: str | None = None,
    image_width: int | None = None,
    image_height: int | None = None,
    card_type: str = "summary_large_image",
    min_image_width: int = 280,
    min_image_height: int = 150,
) -> tuple[dict[str, str], list[str]]:
    """
    Generate Twitter Card meta tags (TA-0072).

    Args:
        title: Content title
        description: Content description
        image_url: Optional image URL
        image_alt: Optional image alt text
        image_width: Optional image width for validation
        image_height: Optional image height for validation
        card_type: Twitter card type (summary, summary_large_image)
        min_image_width: Minimum image width (default 280)
        min_image_height: Minimum image height (default 150)

    Returns:
        Tuple of (meta_tags_dict, warnings_list)
    """
    warnings: list[str] = []
    tags: dict[str, str] = {
        "twitter:card": card_type,
        "twitter:title": title[:70] if len(title) > 70 else title,  # Twitter title limit
        "twitter:description": description[:200] if len(description) > 200 else description,
    }

    if image_url:
        # Validate dimensions if provided
        is_valid, warning = validate_image_dimensions(
            image_width, image_height, min_image_width, min_image_height
        )
        if not is_valid and warning:
            warnings.append(f"Twitter: {warning}")
            # Downgrade to summary card if image too small for large image
            if card_type == "summary_large_image":
                tags["twitter:card"] = "summary"
        else:
            tags["twitter:image"] = image_url
            if image_alt:
                tags["twitter:image:alt"] = image_alt

    return tags, warnings


def generate_opengraph_meta(
    title: str,
    description: str,
    url: str,
    site_name: str,
    og_type: str = "article",
    image_url: str | None = None,
    image_alt: str | None = None,
    image_width: int | None = None,
    image_height: int | None = None,
    min_image_width: int = 200,
    min_image_height: int = 200,
) -> tuple[dict[str, str], list[str]]:
    """
    Generate OpenGraph meta tags (TA-0073).

    Args:
        title: Content title
        description: Content description
        url: Canonical URL
        site_name: Site name
        og_type: OG type (article, website)
        image_url: Optional image URL
        image_alt: Optional image alt text
        image_width: Optional image width for validation
        image_height: Optional image height for validation
        min_image_width: Minimum image width (default 200)
        min_image_height: Minimum image height (default 200)

    Returns:
        Tuple of (meta_tags_dict, warnings_list)
    """
    warnings: list[str] = []
    tags: dict[str, str] = {
        "og:type": og_type,
        "og:title": title,
        "og:description": description,
        "og:url": url,
        "og:site_name": site_name,
    }

    if image_url:
        # Validate dimensions if provided
        is_valid, warning = validate_image_dimensions(
            image_width, image_height, min_image_width, min_image_height
        )
        if not is_valid and warning:
            warnings.append(f"OpenGraph: {warning}")
        else:
            tags["og:image"] = image_url
            if image_alt:
                tags["og:image:alt"] = image_alt
            # Include dimensions if known (helps social platforms)
            if image_width:
                tags["og:image:width"] = str(image_width)
            if image_height:
                tags["og:image:height"] = str(image_height)

    return tags, warnings


def generate_social_meta_tags(
    title: str,
    description: str,
    canonical_url: str,
    site_name: str,
    content_type: str = "article",
    image_url: str | None = None,
    image_alt: str | None = None,
    image_width: int | None = None,
    image_height: int | None = None,
    twitter_card_type: str = "summary_large_image",
    og_type: str | None = None,
    min_twitter_width: int = 280,
    min_twitter_height: int = 150,
    min_og_width: int = 200,
    min_og_height: int = 200,
) -> tuple[dict[str, str], list[str]]:
    """
    Generate combined social meta tags for Twitter and OpenGraph (TA-0072, TA-0073).

    This is the main entry point for social meta tag generation.

    Args:
        title: Content title
        description: Content description
        canonical_url: Canonical URL
        site_name: Site name
        content_type: Content type (article, website)
        image_url: Optional image URL
        image_alt: Optional image alt text
        image_width: Optional image width for validation
        image_height: Optional image height for validation
        twitter_card_type: Twitter card type
        og_type: OG type (defaults to content_type)
        min_twitter_width: Min Twitter image width
        min_twitter_height: Min Twitter image height
        min_og_width: Min OG image width
        min_og_height: Min OG image height

    Returns:
        Tuple of (combined_meta_tags_dict, warnings_list)
    """
    all_tags: dict[str, str] = {}
    all_warnings: list[str] = []

    # Generate Twitter Card tags
    twitter_tags, twitter_warnings = generate_twitter_card_meta(
        title=title,
        description=description,
        image_url=image_url,
        image_alt=image_alt,
        image_width=image_width,
        image_height=image_height,
        card_type=twitter_card_type,
        min_image_width=min_twitter_width,
        min_image_height=min_twitter_height,
    )
    all_tags.update(twitter_tags)
    all_warnings.extend(twitter_warnings)

    # Generate OpenGraph tags
    og_tags, og_warnings = generate_opengraph_meta(
        title=title,
        description=description,
        url=canonical_url,
        site_name=site_name,
        og_type=og_type or content_type,
        image_url=image_url,
        image_alt=image_alt,
        image_width=image_width,
        image_height=image_height,
        min_image_width=min_og_width,
        min_image_height=min_og_height,
    )
    all_tags.update(og_tags)
    all_warnings.extend(og_warnings)

    return all_tags, all_warnings
