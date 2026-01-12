"""
Audit component port definitions.

Spec refs: E8.1
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID


class AuditRepoPort(Protocol):
    """Repository interface for audit logs."""

    def save(self, entry: object) -> object:
        """Save an audit entry."""
        ...

    def get_by_id(self, entry_id: UUID) -> object | None:
        """Get entry by ID."""
        ...

    def query(self, query: object) -> list[object]:
        """Query entries with filters."""
        ...

    def count(self, query: object) -> int:
        """Count entries matching query."""
        ...


class TimePort(Protocol):
    """Time provider interface."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...
