"""
Admin Audit Log API (E8.1).

Provides endpoints for querying audit logs.

Spec refs: E8.1, TA-0049
Test assertions:
- TA-0049: Audit logs can be queried and viewed
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.components.audit import (
    AuditAction,
    AuditEntry,
    AuditService,
    EntityType,
    InMemoryAuditRepo,
)

router = APIRouter()


# --- Request/Response Models ---


class AuditEntryResponse(BaseModel):
    """Audit entry response model."""

    id: str
    timestamp: str
    action: str
    entity_type: str
    entity_id: str | None
    actor_id: str | None
    actor_name: str | None
    description: str
    metadata: dict[str, Any]
    ip_address: str | None


class AuditQueryResponse(BaseModel):
    """Paginated audit query response."""

    items: list[AuditEntryResponse]
    total: int
    offset: int
    limit: int


class EntityHistoryResponse(BaseModel):
    """Entity history response."""

    entity_type: str
    entity_id: str
    entries: list[AuditEntryResponse]


# --- Dependencies ---


_audit_repo = InMemoryAuditRepo()
_audit_service = AuditService(repo=_audit_repo)


def get_audit_service() -> AuditService:
    """Get audit service dependency."""
    return _audit_service


def reset_audit_service() -> None:
    """Reset audit service (for testing)."""
    global _audit_repo, _audit_service
    _audit_repo = InMemoryAuditRepo()
    _audit_service = AuditService(repo=_audit_repo)


# --- Helper Functions ---


def entry_to_response(entry: AuditEntry) -> AuditEntryResponse:
    """Convert AuditEntry to response model."""
    return AuditEntryResponse(
        id=str(entry.id),
        timestamp=entry.timestamp.isoformat(),
        action=entry.action.value,
        entity_type=entry.entity_type.value,
        entity_id=entry.entity_id,
        actor_id=str(entry.actor_id) if entry.actor_id else None,
        actor_name=entry.actor_name,
        description=entry.description,
        metadata=entry.metadata,
        ip_address=entry.ip_address,
    )


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string to datetime object."""
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {dt_str}",
        ) from e


def parse_action(action_str: str) -> AuditAction:
    """Parse action string to enum."""
    try:
        return AuditAction(action_str.lower())
    except ValueError:
        valid_actions = [a.value for a in AuditAction]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {action_str}. Must be one of: {', '.join(valid_actions)}",
        ) from None


def parse_entity_type(entity_type_str: str) -> EntityType:
    """Parse entity type string to enum."""
    try:
        return EntityType(entity_type_str.lower())
    except ValueError:
        valid_types = [e.value for e in EntityType]
        valid_str = ", ".join(valid_types)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type: {entity_type_str}. Must be one of: {valid_str}",
        ) from None


def parse_uuid(uuid_str: str, param_name: str) -> UUID:
    """Parse UUID string."""
    try:
        return UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID for {param_name}: {uuid_str}",
        ) from None


# --- Routes ---


@router.get("", response_model=AuditQueryResponse)
def query_audit_logs(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: str | None = Query(None, description="Filter by entity ID"),
    actor_id: str | None = Query(None, description="Filter by actor ID"),
    action: str | None = Query(None, description="Filter by action"),
    start: str | None = Query(None, description="Start datetime (ISO format)"),
    end: str | None = Query(None, description="End datetime (ISO format)"),
    limit: int = Query(50, ge=1, le=500, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: AuditService = Depends(get_audit_service),
) -> AuditQueryResponse:
    """
    Query audit logs with filters (TA-0049).

    Returns paginated list of audit entries.
    """
    # Parse filters
    entity_type_enum = parse_entity_type(entity_type) if entity_type else None
    action_enum = parse_action(action) if action else None
    actor_uuid = parse_uuid(actor_id, "actor_id") if actor_id else None
    start_dt = parse_datetime(start) if start else None
    end_dt = parse_datetime(end) if end else None

    # Query
    results = service.query(
        entity_type=entity_type_enum,
        entity_id=entity_id,
        actor_id=actor_uuid,
        action=action_enum,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
        offset=offset,
    )

    # Count total
    total = service.count(
        entity_type=entity_type_enum,
        entity_id=entity_id,
        actor_id=actor_uuid,
        action=action_enum,
        start_time=start_dt,
        end_time=end_dt,
    )

    return AuditQueryResponse(
        items=[entry_to_response(e) for e in results],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/recent", response_model=AuditQueryResponse)
def get_recent_audit_logs(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    limit: int = Query(50, ge=1, le=500, description="Number of results"),
    service: AuditService = Depends(get_audit_service),
) -> AuditQueryResponse:
    """
    Get recent audit logs (TA-0049).

    Returns entries from the last N hours.
    """
    results = service.get_recent(hours=hours, limit=limit)

    return AuditQueryResponse(
        items=[entry_to_response(e) for e in results],
        total=len(results),
        offset=0,
        limit=limit,
    )


@router.get("/entity/{entity_type}/{entity_id}", response_model=EntityHistoryResponse)
def get_entity_history(
    entity_type: str,
    entity_id: str,
    service: AuditService = Depends(get_audit_service),
) -> EntityHistoryResponse:
    """
    Get audit history for a specific entity (TA-0049).

    Returns all audit entries for the entity.
    """
    entity_type_enum = parse_entity_type(entity_type)

    entries = service.get_for_entity(entity_type_enum, entity_id)

    return EntityHistoryResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        entries=[entry_to_response(e) for e in entries],
    )


@router.get("/actor/{actor_id}", response_model=AuditQueryResponse)
def get_actor_activity(
    actor_id: str,
    limit: int = Query(50, ge=1, le=500, description="Number of results"),
    service: AuditService = Depends(get_audit_service),
) -> AuditQueryResponse:
    """
    Get audit logs for a specific actor (TA-0049).

    Returns all actions performed by the actor.
    """
    actor_uuid = parse_uuid(actor_id, "actor_id")

    results = service.get_by_actor(actor_uuid, limit=limit)

    return AuditQueryResponse(
        items=[entry_to_response(e) for e in results],
        total=len(results),
        offset=0,
        limit=limit,
    )


@router.get("/{entry_id}", response_model=AuditEntryResponse)
def get_audit_entry(
    entry_id: str,
    service: AuditService = Depends(get_audit_service),
) -> AuditEntryResponse:
    """
    Get a specific audit entry by ID (TA-0049).

    Returns the audit entry or 404 if not found.
    """
    entry_uuid = parse_uuid(entry_id, "entry_id")

    entry = service.get(entry_uuid)

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit entry not found: {entry_id}",
        )

    return entry_to_response(entry)


@router.get("/stats/summary")
def get_audit_summary(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    service: AuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    """
    Get audit log summary statistics (TA-0049).

    Returns counts by action and entity type.
    """
    start = datetime.now(UTC) - timedelta(hours=hours)

    # Count by action
    action_counts = {}
    for action in AuditAction:
        if action == AuditAction.VIEW:
            continue
        count = service.count(action=action, start_time=start)
        if count > 0:
            action_counts[action.value] = count

    # Count by entity type
    entity_counts = {}
    for entity_type in EntityType:
        count = service.count(entity_type=entity_type, start_time=start)
        if count > 0:
            entity_counts[entity_type.value] = count

    # Total count
    total = service.count(start_time=start)

    return {
        "period_hours": hours,
        "total": total,
        "by_action": action_counts,
        "by_entity_type": entity_counts,
    }
