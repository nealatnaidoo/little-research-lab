"""
Richtext component port definitions.

Spec refs: E4.1, E4.2
"""

from __future__ import annotations

from typing import Any, Protocol


class RulesPort(Protocol):
    """Port for accessing rich text rules configuration."""

    def get_allowed_tags(self) -> frozenset[str]:
        """Get allowed HTML tags."""
        ...

    def get_allowed_attrs(self) -> dict[str, frozenset[str]]:
        """Get allowed attributes per tag."""
        ...

    def get_forbidden_protocols(self) -> frozenset[str]:
        """Get forbidden URL protocols."""
        ...

    def get_max_links(self) -> int:
        """Get maximum links per document."""
        ...

    def get_max_json_bytes(self) -> int:
        """Get maximum JSON document size."""
        ...

    def get_link_rel_config(self) -> dict[str, Any]:
        """Get link rel attribute configuration."""
        ...
