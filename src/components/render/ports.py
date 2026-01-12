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
