"""
Audit component input/output models.

Spec refs: E8.1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

# --- Validation Error ---


@dataclass(frozen=True)
class AuditValidationError:
    """Audit validation error."""

    code: str
    message: str
    field: str | None = None


# --- Enums ---


AuditAction = Literal[
    "create",
    "update",
    "delete",
    "publish",
    "unpublish",
    "schedule",
    "unschedule",
    "enable",
    "disable",
    "login",
    "logout",
    "view",
]

EntityType = Literal[
    "settings",
    "content",
    "asset",
    "redirect",
    "schedule",
    "user",
    "system",
]


# --- Audit Entry Model ---


@dataclass(frozen=True)
class AuditEntry:
    """Immutable audit log entry."""

    id: UUID
    timestamp: datetime
    action: AuditAction
    entity_type: EntityType
    entity_id: str | None
    actor_id: UUID | None
    actor_name: str | None
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None


# --- Input Models ---


@dataclass(frozen=True)
class LogAuditInput:
    """Input for logging an audit event."""

    action: AuditAction
    entity_type: EntityType
    entity_id: str | None = None
    actor_id: UUID | None = None
    actor_name: str | None = None
    description: str = ""
    metadata: dict[str, Any] | None = None
    ip_address: str | None = None


@dataclass(frozen=True)
class QueryAuditInput:
    """Input for querying audit logs."""

    entity_type: EntityType | None = None
    entity_id: str | None = None
    actor_id: UUID | None = None
    action: AuditAction | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetAuditEntryInput:
    """Input for getting specific audit entry."""

    entry_id: UUID


# --- Output Models ---


@dataclass(frozen=True)
class LogOutput:
    """Output for log operation."""

    entry: AuditEntry | None
    errors: list[AuditValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class AuditListOutput:
    """Output for audit query."""

    entries: tuple[AuditEntry, ...]
    total: int
    errors: list[AuditValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class AuditEntryOutput:
    """Output for single audit entry."""

    entry: AuditEntry | None
    errors: list[AuditValidationError] = field(default_factory=list)
    success: bool = True
