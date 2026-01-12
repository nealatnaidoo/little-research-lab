"""
Render posts component port definitions.

Spec refs: E4.4
"""

from __future__ import annotations

from typing import Any, Protocol


class RichTextPort(Protocol):
    """Port for rich text component operations."""

    def validate(self, document: dict[str, Any]) -> bool:
        """Validate a rich text document."""
        ...

    def sanitize(self, document: dict[str, Any]) -> dict[str, Any]:
        """Sanitize a rich text document."""
        ...


class RulesPort(Protocol):
    """Port for accessing render rules configuration."""

    def get_code_block_class(self) -> str:
        """Get CSS class for code blocks."""
        ...

    def get_image_loading(self) -> str:
        """Get image loading strategy (lazy/eager)."""
        ...

    def get_link_rel_config(self) -> dict[str, Any]:
        """Get link rel attribute configuration."""
        ...
