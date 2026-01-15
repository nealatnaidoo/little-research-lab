"""
Render component port definitions.

Spec refs: E1.2
"""

from __future__ import annotations

from typing import Any, Protocol


class SettingsPort(Protocol):
    """Port for accessing site settings configuration."""

    def get_base_url(self) -> str:
        """Get site base URL."""
        ...

    def get_default_og_image_url(self) -> str | None:
        """Get default OG image URL."""
        ...


class RulesPort(Protocol):
    """Port for accessing render rules configuration."""

    def get_routing_config(self) -> dict[str, Any]:
        """Get routing configuration."""
        ...

    def get_sanitization_config(self) -> dict[str, Any]:
        """Get HTML sanitization configuration."""
        ...


class SocialMetaRulesPort(Protocol):
    """Port for accessing social meta tag rules configuration (E15.3)."""

    def get_twitter_card_type(self) -> str:
        """Get Twitter card type (summary, summary_large_image)."""
        ...

    def get_og_type(self) -> str:
        """Get OG type for articles (article, website)."""
        ...

    def get_min_image_width_twitter(self) -> int:
        """Get minimum image width for Twitter (default 280)."""
        ...

    def get_min_image_height_twitter(self) -> int:
        """Get minimum image height for Twitter (default 150)."""
        ...

    def get_min_image_width_facebook(self) -> int:
        """Get minimum image width for Facebook/OG (default 200)."""
        ...

    def get_min_image_height_facebook(self) -> int:
        """Get minimum image height for Facebook/OG (default 200)."""
        ...
