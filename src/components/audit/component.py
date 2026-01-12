"""
Audit component - Audit logging and querying.

Spec refs: E8.1
Test assertions: TA-0048, TA-0049

Log and query audit trail for admin actions.

Invariants:
- I1: All admin actions logged
- I2: Audit entries are immutable
- I3: Actor identity captured
- I4: Entity type and ID tracked
- I5: Before/after state recorded for updates
"""

from __future__ import annotations

from ._impl import (
    AuditAction as LegacyAuditAction,
)
from ._impl import (
    AuditConfig,
    AuditService,
)
from ._impl import (
    AuditEntry as LegacyEntry,
)
from ._impl import (
    EntityType as LegacyEntityType,
)
from .models import (
    AuditEntry,
    AuditEntryOutput,
    AuditListOutput,
    AuditValidationError,
    GetAuditEntryInput,
    LogAuditInput,
    LogOutput,
    QueryAuditInput,
)
from .ports import AuditRepoPort, TimePort


def _convert_entry(legacy: LegacyEntry | None) -> AuditEntry | None:
    """Convert legacy audit entry to component model."""
    if legacy is None:
        return None
    return AuditEntry(
        id=legacy.id,
        timestamp=legacy.timestamp,
        action=legacy.action.value,
        entity_type=legacy.entity_type.value,
        entity_id=legacy.entity_id,
        actor_id=legacy.actor_id,
        actor_name=legacy.actor_name,
        description=legacy.description,
        metadata=legacy.metadata,
        ip_address=legacy.ip_address,
    )


def _create_service(
    repo: AuditRepoPort,
    time_port: TimePort | None,
) -> AuditService:
    """Create audit service from ports."""
    return AuditService(
        repo=repo,  # type: ignore[arg-type]  # Protocol structural mismatch
        time_port=time_port,
        config=AuditConfig(),
    )


# --- Component Entry Points ---


def run_log(
    inp: LogAuditInput,
    *,
    repo: AuditRepoPort,
    time_port: TimePort | None = None,
) -> LogOutput:
    """
    Log an audit event (TA-0048).

    Args:
        inp: Input containing audit event details.
        repo: Audit repository port.
        time_port: Optional time port.

    Returns:
        LogOutput with created entry or errors.
    """
    service = _create_service(repo, time_port)

    try:
        action = LegacyAuditAction(inp.action)
        entity_type = LegacyEntityType(inp.entity_type)
    except ValueError as e:
        return LogOutput(
            entry=None,
            errors=[
                AuditValidationError(
                    code="invalid_enum",
                    message=str(e),
                )
            ],
            success=False,
        )

    legacy_entry = service.log(
        action=action,
        entity_type=entity_type,
        entity_id=inp.entity_id,
        actor_id=inp.actor_id,
        actor_name=inp.actor_name,
        description=inp.description,
        metadata=inp.metadata,
        ip_address=inp.ip_address,
    )

    entry = _convert_entry(legacy_entry)

    if entry is None:
        return LogOutput(
            entry=None,
            errors=[
                AuditValidationError(
                    code="logging_disabled",
                    message="Audit logging is disabled",
                )
            ],
            success=False,
        )

    return LogOutput(
        entry=entry,
        errors=[],
        success=True,
    )


def run_query(
    inp: QueryAuditInput,
    *,
    repo: AuditRepoPort,
    time_port: TimePort | None = None,
) -> AuditListOutput:
    """
    Query audit logs (TA-0049).

    Args:
        inp: Input containing query filters.
        repo: Audit repository port.
        time_port: Optional time port.

    Returns:
        AuditListOutput with matching entries.
    """
    service = _create_service(repo, time_port)

    # Convert string literals to enums for query
    entity_type = None
    action = None

    if inp.entity_type is not None:
        try:
            entity_type = LegacyEntityType(inp.entity_type)
        except ValueError:
            pass

    if inp.action is not None:
        try:
            action = LegacyAuditAction(inp.action)
        except ValueError:
            pass

    legacy_entries = service.query(
        entity_type=entity_type,
        entity_id=inp.entity_id,
        actor_id=inp.actor_id,
        action=action,
        start_time=inp.start_time,
        end_time=inp.end_time,
        limit=inp.limit,
        offset=inp.offset,
    )

    entries = tuple(_convert_entry(e) for e in legacy_entries if e is not None)

    total = service.count(
        entity_type=entity_type,
        entity_id=inp.entity_id,
        actor_id=inp.actor_id,
        action=action,
        start_time=inp.start_time,
        end_time=inp.end_time,
    )

    return AuditListOutput(
        entries=entries,  # type: ignore[arg-type]
        total=total,
        errors=[],
        success=True,
    )


def run_get(
    inp: GetAuditEntryInput,
    *,
    repo: AuditRepoPort,
    time_port: TimePort | None = None,
) -> AuditEntryOutput:
    """
    Get specific audit entry.

    Args:
        inp: Input containing entry_id.
        repo: Audit repository port.
        time_port: Optional time port.

    Returns:
        AuditEntryOutput with entry or error.
    """
    service = _create_service(repo, time_port)

    legacy_entry = service.get(inp.entry_id)
    entry = _convert_entry(legacy_entry)

    if entry is None:
        return AuditEntryOutput(
            entry=None,
            errors=[
                AuditValidationError(
                    code="not_found",
                    message=f"Audit entry {inp.entry_id} not found",
                )
            ],
            success=False,
        )

    return AuditEntryOutput(
        entry=entry,
        errors=[],
        success=True,
    )


def run(
    inp: LogAuditInput | QueryAuditInput | GetAuditEntryInput,
    *,
    repo: AuditRepoPort,
    time_port: TimePort | None = None,
) -> LogOutput | AuditListOutput | AuditEntryOutput:
    """
    Main entry point for the audit component.

    Dispatches to appropriate handler based on input type.

    Args:
        inp: Input object determining the operation.
        repo: Audit repository port.
        time_port: Optional time port.

    Returns:
        Appropriate output object based on input type.
    """
    if isinstance(inp, LogAuditInput):
        return run_log(inp, repo=repo, time_port=time_port)
    elif isinstance(inp, QueryAuditInput):
        return run_query(inp, repo=repo, time_port=time_port)
    elif isinstance(inp, GetAuditEntryInput):
        return run_get(inp, repo=repo, time_port=time_port)
    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
