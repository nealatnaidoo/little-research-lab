"""
Render component input/output models.

Spec refs: E1.2
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.entities import ContentItem, SiteSettings

# --- Validation Error ---


@dataclass(frozen=True)
class RenderValidationError:
    """Render validation error."""

    code: str
    message: str
    field: str | None = None


# --- Input Models ---


@dataclass(frozen=True)
class RenderPageMetadataInput:
    """Input for rendering page metadata."""

    settings: SiteSettings
    content: ContentItem | None = None
    path: str = "/"
    page_title: str | None = None
    page_description: str | None = None
    og_image_url: str | None = None


@dataclass(frozen=True)
class RenderContentMetadataInput:
    """Input for rendering content-specific metadata."""

    settings: SiteSettings
    content: ContentItem
    og_image_url: str | None = None


@dataclass(frozen=True)
class RenderHomepageMetadataInput:
    """Input for rendering homepage metadata."""

    settings: SiteSettings
    og_image_url: str | None = None


# --- Output Models ---


@dataclass(frozen=True)
class MetaTag:
    """HTML meta tag representation."""

    name: str | None = None
    property: str | None = None
    content: str = ""


@dataclass(frozen=True)
class PageMetadata:
    """Complete page metadata for SSR rendering."""

    title: str
    description: str
    canonical_url: str
    robots: str = "index, follow"
    og_title: str = ""
    og_description: str = ""
    og_type: str = "website"
    og_url: str = ""
    og_image: str = ""
    og_image_alt: str = ""
    og_site_name: str = ""
    twitter_card: str = "summary_large_image"
    twitter_title: str = ""
    twitter_description: str = ""
    twitter_image: str = ""
    twitter_image_alt: str = ""
    extra_meta: tuple[MetaTag, ...] = ()


@dataclass(frozen=True)
class RenderOutput:
    """Output containing rendered page metadata."""

    metadata: PageMetadata | None
    errors: list[RenderValidationError] = field(default_factory=list)
    success: bool = True


# --- Social Meta Tag Models (E15.3) ---


@dataclass(frozen=True)
class ImageDimensions:
    """Image dimensions for validation."""

    width: int
    height: int


@dataclass(frozen=True)
class SocialMetaInput:
    """
    Input for generating social meta tags (TA-0072, TA-0073).

    Used to generate Twitter Card and OpenGraph tags for content sharing.
    """

    title: str
    description: str
    canonical_url: str
    site_name: str
    content_type: str = "article"  # "article" for content, "website" for homepage
    image_url: str | None = None
    image_alt: str | None = None
    image_dimensions: ImageDimensions | None = None  # For validation


@dataclass(frozen=True)
class TwitterCardMeta:
    """
    Twitter Card meta tags (TA-0072).

    Generates twitter:card, twitter:title, twitter:description, twitter:image tags.
    """

    card_type: str  # "summary" or "summary_large_image"
    title: str
    description: str
    image_url: str | None = None
    image_alt: str | None = None
    image_valid: bool = True  # False if image doesn't meet min dimensions


@dataclass(frozen=True)
class OpenGraphMeta:
    """
    OpenGraph meta tags (TA-0073).

    Generates og:type, og:title, og:description, og:image, og:url tags.
    """

    og_type: str  # "article" or "website"
    title: str
    description: str
    url: str
    site_name: str
    image_url: str | None = None
    image_alt: str | None = None
    image_valid: bool = True  # False if image doesn't meet min dimensions


@dataclass(frozen=True)
class SocialMetaOutput:
    """Output containing generated social meta tags."""

    twitter: TwitterCardMeta
    og: OpenGraphMeta
    warnings: list[str] = field(default_factory=list)  # e.g., "Image too small for Twitter"
    errors: list[RenderValidationError] = field(default_factory=list)
    success: bool = True
