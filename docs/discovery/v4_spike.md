# V4 Discovery Spike: Architecture Reality Check

**Task**: T-0006
**Date**: 2026-01-13
**Spec refs**: Assumptions section (lines 21-26)
**Test assertion**: TA-E2.3-01

## Purpose

Validate that the three medium-risk assumptions from the v4 spec match the actual codebase reality. If any mismatch is found, record an EV entry and halt.

## Assumptions Validated

### Assumption 1: Next.js App Router
**Spec claim**: "Next.js App Router (Medium risk)"
**Status**: CONFIRMED

**Evidence**:
- Directory `frontend/app/` exists with App Router page structure
- Root layout: `frontend/app/layout.tsx`
- Root page: `frontend/app/page.tsx`
- Dynamic routes: `frontend/app/p/[slug]/page.tsx`
- Admin routes: `frontend/app/admin/**/*.tsx`
- No `pages/` directory (would indicate Pages Router)
- 19 route files following App Router conventions

**Files verified**:
```
frontend/app/layout.tsx
frontend/app/page.tsx
frontend/app/p/[slug]/page.tsx
frontend/app/admin/page.tsx
frontend/app/admin/layout.tsx
frontend/app/admin/content/page.tsx
frontend/app/admin/content/[id]/page.tsx
frontend/app/admin/content/new/page.tsx
... and 11 more admin routes
```

### Assumption 2: Object Storage Available via Adapter
**Spec claim**: "Object storage available (S3/R2/etc.) via adapter (Medium risk)"
**Status**: CONFIRMED

**Evidence**:
- Port defined: `src/core/ports/storage.py`
  - `StoragePort` protocol with `put`, `get`, `get_stream`, `exists`, `delete`, `get_metadata`, `get_public_url`
  - `StoredObject` dataclass for metadata
  - Error types: `KeyExistsError`, `KeyNotFoundError`, `IntegrityError`
- Adapter implemented: `src/adapters/local_storage.py`
  - `LocalFileStorage` class implementing the port
  - Immutability guarantee (raises `KeyExistsError` on duplicate key)
  - SHA256 integrity verification on read
  - Factory function `create_local_storage()`
- Architecture: Port-based design supports future S3/R2 adapters without changing consumers

**Key invariant preserved**: "I3: AssetVersion bytes are immutable; sha256 stored equals sha256 served"

### Assumption 3: Jobs Executed via Worker Process
**Spec claim**: "Jobs executed via a small worker process (Medium risk)"
**Status**: CONFIRMED

**Evidence**:
- Port defined: `src/core/ports/jobs.py`
  - `JobExecutorPort` - single job execution
  - `JobRunnerPort` - job claiming and batch processing
  - `JobSchedulerPort` - trigger mechanism abstraction
  - `JobStatus` enum, `JobResult` and `BatchResult` dataclasses
- Adapter implemented: `src/adapters/dev_jobs.py`
  - `DevJobExecutor` - executes publish via callback
  - `DevJobRunner` - DB polling with atomic claims
  - `DevJobScheduler` - background thread with configurable poll interval
- Service layer: `src/core/services/scheduler.py`
  - `SchedulerService` with idempotency, retry, and backoff
  - `SchedulerConfig` with tunable parameters
  - DST-safe scheduling via `TimePort`

**Key behaviors confirmed**:
- Atomic job claiming via DB transactions
- Idempotent execution (same result on retry)
- Exponential backoff: (5, 15, 60, 300, 900, 1800) seconds
- Max attempts: 10
- Production note: Fly.io scheduled machines (documented in comments)

## Conclusion

All three medium-risk assumptions are **CONFIRMED**. No mismatches detected.

**Action**: Proceed with v4 implementation. No EV entry required.

## Evidence Trail

| Assumption | Port File | Adapter File | Status |
|------------|-----------|--------------|--------|
| App Router | N/A | frontend/app/**/*.tsx | CONFIRMED |
| Object Storage | src/core/ports/storage.py | src/adapters/local_storage.py | CONFIRMED |
| Job Worker | src/core/ports/jobs.py | src/adapters/dev_jobs.py | CONFIRMED |

---
*Discovery spike completed without evolution variance.*
