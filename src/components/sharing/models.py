"""
Sharing component input/output models.

Spec refs: E15.2
Test assertions: TA-0070, TA-0071
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# --- Types ---

SharingPlatform = Literal["twitter", "linkedin", "facebook", "native"]


# --- Validation Error ---


@dataclass(frozen=True)
class SharingValidationError:
    """Sharing validation error."""

    code: str
    message: str
    field_name: str | None = None


# --- Input Models ---


@dataclass(frozen=True)
class GenerateShareUrlInput:
    """
    Input for generating a share URL with UTM params.

    TA-0070: Share URLs include platform-specific UTM params.
    """

    content_slug: str
    platform: SharingPlatform
    base_url: str  # e.g., "https://example.com"
    content_path_prefix: str = "/p"  # Default to posts prefix
    title: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class AddUtmParamsInput:
    """
    Input for adding UTM params to an existing URL.

    TA-0071: UTM params follow standard format.
    """

    url: str
    utm_source: str
    utm_medium: str = "social"
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None


# --- Output Models ---


@dataclass(frozen=True)
class GenerateShareUrlOutput:
    """Output from share URL generation."""

    share_url: str | None
    platform: SharingPlatform
    utm_source: str
    utm_medium: str
    utm_campaign: str
    errors: list[SharingValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class AddUtmParamsOutput:
    """Output from adding UTM params."""

    url: str | None
    errors: list[SharingValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class PlatformShareConfig:
    """Configuration for a specific sharing platform."""

    platform: SharingPlatform
    share_url_template: str  # e.g., "https://twitter.com/intent/tweet?url={url}&text={title}"
    utm_source: str
    supports_title: bool = True
    supports_description: bool = False


@dataclass(frozen=True)
class SharingConfig:
    """Complete sharing configuration from rules."""

    enabled: bool
    platforms: tuple[SharingPlatform, ...]
    utm_medium: str
    utm_source_map: dict[SharingPlatform, str]
    utm_campaign_source: str  # "slug" or "title"
