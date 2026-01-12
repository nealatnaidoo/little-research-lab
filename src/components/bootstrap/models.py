"""Bootstrap component data models.

Frozen dataclasses for inputs, outputs, and validation errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities import User


@dataclass(frozen=True)
class BootstrapInput:
    """Input parameters for bootstrap operation."""

    bootstrap_email: str | None
    bootstrap_password: str | None


@dataclass(frozen=True)
class BootstrapValidationError:
    """Validation error details."""

    code: str
    message: str
    field: str


@dataclass(frozen=True)
class BootstrapOutput:
    """Result of bootstrap operation."""

    user: User | None
    created: bool
    skipped_reason: str | None
    errors: tuple[BootstrapValidationError, ...]
    success: bool

    @classmethod
    def skipped(cls, reason: str) -> BootstrapOutput:
        """Create a skipped result."""
        return cls(
            user=None,
            created=False,
            skipped_reason=reason,
            errors=(),
            success=True,
        )

    @classmethod
    def created_user(cls, user: User) -> BootstrapOutput:
        """Create a success result with user."""
        return cls(
            user=user,
            created=True,
            skipped_reason=None,
            errors=(),
            success=True,
        )

    @classmethod
    def failed(cls, errors: tuple[BootstrapValidationError, ...]) -> BootstrapOutput:
        """Create a failure result."""
        return cls(
            user=None,
            created=False,
            skipped_reason=None,
            errors=errors,
            success=False,
        )
