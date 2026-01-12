"""Bootstrap component port definitions.

Protocol interfaces for external dependencies.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.domain.entities import User
    from src.rules.models import AdminBootstrapRules


class UserRepoPort(Protocol):
    """Repository for user persistence."""

    def list_all(self) -> list[User]:
        """List all users in the system."""
        ...

    def save(self, user: User) -> None:
        """Persist a user to storage."""
        ...


class AuthAdapterPort(Protocol):
    """Authentication operations adapter."""

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password for storage."""
        ...


class RulesPort(Protocol):
    """Access to application rules/configuration."""

    def get_bootstrap_config(self) -> AdminBootstrapRules:
        """Get bootstrap configuration from rules."""
        ...


class TimePort(Protocol):
    """Port for time operations - enables deterministic testing."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...
