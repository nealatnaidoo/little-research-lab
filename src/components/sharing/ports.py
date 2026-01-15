"""
Sharing component port definitions.

Spec refs: E15.2
"""

from __future__ import annotations

from typing import Protocol

from .models import SharingPlatform


class SharingRulesPort(Protocol):
    """Port for sharing rules configuration."""

    def is_enabled(self) -> bool:
        """Check if social sharing is enabled."""
        ...

    def get_platforms(self) -> tuple[SharingPlatform, ...]:
        """Get list of enabled sharing platforms."""
        ...

    def get_utm_medium(self) -> str:
        """Get UTM medium value (default 'social')."""
        ...

    def get_utm_source_for_platform(self, platform: SharingPlatform) -> str:
        """Get UTM source for a specific platform."""
        ...

    def get_utm_campaign_source(self) -> str:
        """Get what to use for UTM campaign ('slug' or 'title')."""
        ...

    def prefer_native_share_on_mobile(self) -> bool:
        """Whether to prefer native share API on mobile devices."""
        ...


class SettingsPort(Protocol):
    """Port for site settings (to get base URL)."""

    def get_base_url(self) -> str:
        """Get the site's canonical base URL."""
        ...
