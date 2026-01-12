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
