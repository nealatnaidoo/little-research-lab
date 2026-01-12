"""
Redirects component port definitions.

Spec refs: E7.1
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class RedirectRepoPort(Protocol):
    """Repository interface for redirects."""

    def get_by_id(self, redirect_id: UUID) -> object | None:
        """Get redirect by ID."""
        ...

    def get_by_source(self, source_path: str) -> object | None:
        """Get redirect by source path."""
        ...

    def save(self, redirect: object) -> object:
        """Save or update redirect."""
        ...

    def delete(self, redirect_id: UUID) -> None:
        """Delete redirect."""
        ...

    def list_all(self) -> list[object]:
        """List all redirects."""
        ...


class RouteCheckerPort(Protocol):
    """Interface for checking existing routes."""

    def route_exists(self, path: str) -> bool:
        """Check if a path matches an existing route."""
        ...


class RulesPort(Protocol):
    """Port for redirect rules configuration."""

    def is_enabled(self) -> bool:
        """Check if redirects are enabled."""
        ...

    def get_default_status_code(self) -> int:
        """Get default HTTP status code for redirects."""
        ...

    def get_max_chain_length(self) -> int:
        """Get maximum redirect chain length."""
        ...

    def require_internal_targets(self) -> bool:
        """Check if external targets are blocked."""
        ...

    def get_prevent_loops(self) -> bool:
        """Check if loop prevention is enabled."""
        ...

    def get_preserve_utm_params(self) -> bool:
        """Check if UTM params should be preserved."""
        ...
