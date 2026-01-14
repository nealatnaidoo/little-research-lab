"""
Links component - Port interfaces.

Spec refs: Link management
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.entities import LinkItem


class LinkRepoPort(Protocol):
    """Repository interface for links."""

    def save(self, link: LinkItem) -> LinkItem:
        """Save or update link."""
        ...

    def get_all(self) -> list[LinkItem]:
        """List all links."""
        ...

    def delete(self, link_id: UUID) -> None:
        """Delete link."""
        ...
