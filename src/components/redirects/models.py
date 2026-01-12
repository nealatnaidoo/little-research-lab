"""
Redirects component input/output models.

Spec refs: E7.1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

# --- Validation Error ---


@dataclass(frozen=True)
class RedirectValidationError:
    """Redirect validation error."""

    code: str
    message: str
    field: str | None = None


# --- Redirect Model ---


@dataclass(frozen=True)
class Redirect:
    """URL redirect mapping."""

    id: UUID
    source_path: str
    target_path: str
    status_code: int
    enabled: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    notes: str | None = None


# --- Input Models ---


@dataclass(frozen=True)
class CreateRedirectInput:
    """Input for creating a new redirect."""

    source_path: str
    target_path: str
    status_code: int | None = None
    created_by: UUID | None = None
    notes: str | None = None


@dataclass(frozen=True)
class UpdateRedirectInput:
    """Input for updating an existing redirect."""

    redirect_id: UUID
    updates: dict[str, Any]


@dataclass(frozen=True)
class DeleteRedirectInput:
    """Input for deleting a redirect."""

    redirect_id: UUID


@dataclass(frozen=True)
class GetRedirectInput:
    """Input for getting a redirect."""

    redirect_id: UUID | None = None
    source_path: str | None = None


@dataclass(frozen=True)
class ListRedirectsInput:
    """Input for listing all redirects."""

    pass


@dataclass(frozen=True)
class ResolveRedirectInput:
    """Input for resolving a path through redirects."""

    path: str


# --- Output Models ---


@dataclass(frozen=True)
class RedirectOutput:
    """Output containing a single redirect."""

    redirect: Redirect | None
    errors: list[RedirectValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class RedirectListOutput:
    """Output containing a list of redirects."""

    redirects: tuple[Redirect, ...]
    errors: list[RedirectValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class RedirectOperationOutput:
    """Output for redirect operations (create, update, delete)."""

    redirect: Redirect | None = None
    errors: list[RedirectValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class ResolveOutput:
    """Output for resolve operation."""

    final_target: str | None
    status_code: int | None
    errors: list[RedirectValidationError] = field(default_factory=list)
    success: bool = True
