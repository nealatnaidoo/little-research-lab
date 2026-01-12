"""
Audit component - Audit logging and querying.

Spec refs: E8.1
"""

# Re-exports from _impl for backwards compatibility
# Note: AuditAction, EntityType, and AuditEntry from _impl override the Literal types from models
# because the API routes expect Enum classes
from ._impl import (
    AuditAction,
    AuditEntry,
    AuditService,
    EntityType,
    InMemoryAuditRepo,
)
from .component import (
    run,
    run_get,
    run_log,
    run_query,
)
from .models import (
    AuditEntryOutput,
    AuditListOutput,
    AuditValidationError,
    GetAuditEntryInput,
    LogAuditInput,
    LogOutput,
    QueryAuditInput,
)
from .ports import AuditRepoPort, TimePort

__all__ = [
    # Entry points
    "run",
    "run_get",
    "run_log",
    "run_query",
    # Input models
    "GetAuditEntryInput",
    "LogAuditInput",
    "QueryAuditInput",
    # Output models
    "AuditAction",
    "AuditEntry",
    "AuditEntryOutput",
    "AuditListOutput",
    "AuditValidationError",
    "EntityType",
    "LogOutput",
    # Ports
    "AuditRepoPort",
    "TimePort",
    # Legacy _impl re-exports
    "AuditService",
    "InMemoryAuditRepo",
]
