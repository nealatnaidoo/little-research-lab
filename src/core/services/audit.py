"""
AuditLogService (E8.1) - Audit logging and storage.

Handles creation and retrieval of audit log entries.

Spec refs: E8.1, TA-0048, TA-0049
Test assertions:
- TA-0048: Audit log entries are created
- TA-0049: Audit log entries can be queried

Key behaviors:
- Log all admin actions (create, update, delete)
- Capture actor, target, action, metadata
- Query by entity, actor, action, time range
- Immutable log entries (no update/delete)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Protocol
from uuid import UUID, uuid4

# --- Enums ---


class AuditAction(str, Enum):
    """Audit action types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    PUBLISH = "publish"
    UNPUBLISH = "unpublish"
    SCHEDULE = "schedule"
    UNSCHEDULE = "unschedule"
    ENABLE = "enable"
    DISABLE = "disable"
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW = "view"  # For sensitive data access


class EntityType(str, Enum):
    """Entity types that can be audited."""

    SETTINGS = "settings"
    CONTENT = "content"
    ASSET = "asset"
    REDIRECT = "redirect"
    SCHEDULE = "schedule"
    USER = "user"
    SYSTEM = "system"


# --- Configuration ---


@dataclass(frozen=True)
class AuditConfig:
    """Audit logging configuration."""

    enabled: bool = True
    log_views: bool = False  # Whether to log VIEW actions
    retention_days: int = 365  # Days to keep logs
    max_metadata_size: int = 10000  # Max metadata JSON size in bytes


DEFAULT_CONFIG = AuditConfig()


# --- Audit Entry Model ---


@dataclass
class AuditEntry:
    """Immutable audit log entry."""

    id: UUID
    timestamp: datetime
    action: AuditAction
    entity_type: EntityType
    entity_id: str | None  # ID of affected entity
    actor_id: UUID | None  # ID of user performing action
    actor_name: str | None  # Display name for readability
    description: str  # Human-readable description
    metadata: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None  # For login/security events


# --- Query Parameters ---


@dataclass
class AuditQuery:
    """Query parameters for audit log."""

    entity_type: EntityType | None = None
    entity_id: str | None = None
    actor_id: UUID | None = None
    action: AuditAction | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = 100
    offset: int = 0


# --- Repository Protocol ---


class AuditRepoPort(Protocol):
    """Repository interface for audit logs."""

    def save(self, entry: AuditEntry) -> AuditEntry:
        """Save an audit entry."""
        ...

    def get_by_id(self, entry_id: UUID) -> AuditEntry | None:
        """Get entry by ID."""
        ...

    def query(self, query: AuditQuery) -> list[AuditEntry]:
        """Query entries with filters."""
        ...

    def count(self, query: AuditQuery) -> int:
        """Count entries matching query."""
        ...


# --- In-Memory Repository ---


class InMemoryAuditRepo:
    """In-memory audit repository for testing/dev."""

    def __init__(self) -> None:
        self._entries: dict[UUID, AuditEntry] = {}

    def save(self, entry: AuditEntry) -> AuditEntry:
        """Save entry."""
        self._entries[entry.id] = entry
        return entry

    def get_by_id(self, entry_id: UUID) -> AuditEntry | None:
        """Get by ID."""
        return self._entries.get(entry_id)

    def query(self, query: AuditQuery) -> list[AuditEntry]:
        """Query with filters."""
        results = list(self._entries.values())

        # Apply filters
        if query.entity_type:
            results = [e for e in results if e.entity_type == query.entity_type]
        if query.entity_id:
            results = [e for e in results if e.entity_id == query.entity_id]
        if query.actor_id:
            results = [e for e in results if e.actor_id == query.actor_id]
        if query.action:
            results = [e for e in results if e.action == query.action]
        if query.start_time:
            results = [e for e in results if e.timestamp >= query.start_time]
        if query.end_time:
            results = [e for e in results if e.timestamp <= query.end_time]

        # Sort by timestamp descending
        results.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply pagination
        return results[query.offset : query.offset + query.limit]

    def count(self, query: AuditQuery) -> int:
        """Count matching entries."""
        results = list(self._entries.values())

        if query.entity_type:
            results = [e for e in results if e.entity_type == query.entity_type]
        if query.entity_id:
            results = [e for e in results if e.entity_id == query.entity_id]
        if query.actor_id:
            results = [e for e in results if e.actor_id == query.actor_id]
        if query.action:
            results = [e for e in results if e.action == query.action]
        if query.start_time:
            results = [e for e in results if e.timestamp >= query.start_time]
        if query.end_time:
            results = [e for e in results if e.timestamp <= query.end_time]

        return len(results)

    def clear(self) -> None:
        """Clear all entries (for testing)."""
        self._entries.clear()


# --- Time Port Protocol ---


class TimePort(Protocol):
    """Time provider interface."""

    def now_utc(self) -> datetime:
        """Get current UTC time."""
        ...


class DefaultTimePort:
    """Default time provider."""

    def now_utc(self) -> datetime:
        return datetime.now(UTC)


# --- Audit Service ---


class AuditService:
    """
    Audit logging service (E8.1).

    Records and queries audit log entries.
    """

    def __init__(
        self,
        repo: AuditRepoPort,
        time_port: TimePort | None = None,
        config: AuditConfig | None = None,
    ) -> None:
        """Initialize service."""
        self._repo = repo
        self._time = time_port or DefaultTimePort()
        self._config = config or DEFAULT_CONFIG

    def log(
        self,
        action: AuditAction,
        entity_type: EntityType,
        entity_id: str | None = None,
        actor_id: UUID | None = None,
        actor_name: str | None = None,
        description: str = "",
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditEntry | None:
        """
        Create an audit log entry (TA-0048).

        Returns None if logging is disabled or filtered.
        """
        if not self._config.enabled:
            return None

        # Skip VIEW actions if not enabled
        if action == AuditAction.VIEW and not self._config.log_views:
            return None

        # Build entry
        entry = AuditEntry(
            id=uuid4(),
            timestamp=self._time.now_utc(),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_name=actor_name,
            description=description
            or self._generate_description(
                action,
                entity_type,
                entity_id,
            ),
            metadata=metadata or {},
            ip_address=ip_address,
        )

        return self._repo.save(entry)

    def _generate_description(
        self,
        action: AuditAction,
        entity_type: EntityType,
        entity_id: str | None,
    ) -> str:
        """Generate default description."""
        entity_ref = f"{entity_type.value}"
        if entity_id:
            entity_ref += f" {entity_id}"
        return f"{action.value.title()} {entity_ref}"

    def log_create(
        self,
        entity_type: EntityType,
        entity_id: str,
        actor_id: UUID | None = None,
        actor_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry | None:
        """Log a create action."""
        return self.log(
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_name=actor_name,
            metadata=metadata,
        )

    def log_update(
        self,
        entity_type: EntityType,
        entity_id: str,
        actor_id: UUID | None = None,
        actor_name: str | None = None,
        changes: dict[str, Any] | None = None,
    ) -> AuditEntry | None:
        """Log an update action with changes."""
        return self.log(
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_name=actor_name,
            metadata={"changes": changes} if changes else None,
        )

    def log_delete(
        self,
        entity_type: EntityType,
        entity_id: str,
        actor_id: UUID | None = None,
        actor_name: str | None = None,
    ) -> AuditEntry | None:
        """Log a delete action."""
        return self.log(
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_name=actor_name,
        )

    def get(self, entry_id: UUID) -> AuditEntry | None:
        """Get entry by ID."""
        return self._repo.get_by_id(entry_id)

    def query(
        self,
        entity_type: EntityType | None = None,
        entity_id: str | None = None,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """
        Query audit entries (TA-0049).

        Returns entries matching the filters.
        """
        query = AuditQuery(
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            action=action,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        return self._repo.query(query)

    def count(
        self,
        entity_type: EntityType | None = None,
        entity_id: str | None = None,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> int:
        """Count entries matching filters."""
        query = AuditQuery(
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            action=action,
            start_time=start_time,
            end_time=end_time,
        )
        return self._repo.count(query)

    def get_for_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
        limit: int = 50,
    ) -> list[AuditEntry]:
        """Get audit trail for a specific entity."""
        return self.query(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
        )

    def get_by_actor(
        self,
        actor_id: UUID,
        limit: int = 50,
    ) -> list[AuditEntry]:
        """Get recent actions by an actor."""
        return self.query(actor_id=actor_id, limit=limit)

    def get_recent(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Get recent audit entries."""
        start_time = self._time.now_utc() - timedelta(hours=hours)
        return self.query(start_time=start_time, limit=limit)


# --- Factory ---


def create_audit_service(
    repo: AuditRepoPort | None = None,
    time_port: TimePort | None = None,
    config: AuditConfig | None = None,
) -> AuditService:
    """Create an AuditService."""
    return AuditService(
        repo=repo or InMemoryAuditRepo(),
        time_port=time_port,
        config=config,
    )
