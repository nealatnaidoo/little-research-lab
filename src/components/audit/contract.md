## COMPONENT_ID
C8-audit

## PURPOSE
Log and query audit trail for admin actions.
Provides accountability for content and settings changes.

## INPUTS
- `LogAuditInput`: Log an audit event
- `QueryAuditInput`: Query audit logs with filters
- `GetAuditEntryInput`: Get specific audit entry

## OUTPUTS
- `LogOutput`: Log result with entry ID
- `AuditListOutput`: List of audit entries with pagination
- `AuditEntryOutput`: Single audit entry

## DEPENDENCIES (PORTS)
- `AuditRepoPort`: Database access for audit logs
- `TimePort`: Time source for timestamps

## SIDE EFFECTS
- Database write for new audit entries
- Audit logs are append-only

## INVARIANTS
- I1: All admin actions logged (TA-0049)
- I2: Audit entries are immutable
- I3: Actor identity captured
- I4: Entity type and ID tracked
- I5: Before/after state recorded for updates

## ERROR SEMANTICS
- Log failures should not break main operation
- Async logging where possible
- Graceful degradation on storage errors

## TESTS
- `tests/unit/test_audit.py`: TA-0049 (tests)
  - Audit logging for all admin actions
  - Query filters
  - Immutability enforcement

## EVIDENCE
- `artifacts/pytest-audit-report.json`
