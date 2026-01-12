# little-research-lab-v3 — Decisions (D-IDs)

## D-0001 — Slug uniqueness policy
- Context: Routing and redirect simplicity; brief recommends global unique slugs.
- Options:
  1) Global unique across all content types
  2) Unique per type (posts/resources separate)
- Decision: **Global unique**
- Rationale: Simplifies routing, avoids collisions, reduces redirect complexity.
- Implications: Admin UI must validate global uniqueness; migration tooling must account.
- Rollback: Switch to per-type uniqueness in rules.yaml and update router + validations.
- Needs confirmation: No.

## D-0002 — Resource URL namespace
- Context: Avoid collisions and clarify PDF resources.
- Options: `/p/{slug}`, `/r/{slug}`, `/resources/{slug}`
- Decision: **`/r/{slug}`**
- Rationale: Clarity and fewer collisions.
- Rollback: Change routing namespaces in rules.yaml and add redirects.
- Needs confirmation: No.

## D-0003 — Rich text canonical storage
- Context: Brief suggests canonical rich-text JSON with derived blocks for renderer compatibility.
- Options: blocks only / rich-text only / both (rich-text + derived blocks)
- Decision: **Both** (`rich_text_json_plus_derived_blocks`)
- Rationale: Best migration path; enables WYSIWYG while preserving deterministic SSR.
- Rollback: Store only rich-text JSON and rework renderer to consume it directly.
- Needs confirmation: No.

## D-0004 — `/assets/{asset_id}/latest` behavior
- Context: Alias must be cache-friendly and unambiguous.
- Options:
  1) 302 redirect to versioned URL
  2) Proxy bytes directly from alias route
- Decision: **302 redirect to versioned URL**
- Rationale: Ensures caches converge on immutable versioned resource and keeps headers consistent.
- Rollback: Switch to proxy_bytes in rules.yaml.
- Needs confirmation: No.

## D-0005 — Analytics ingestion model
- Context: Need cookie-less analytics with attribution and dedupe; brief recommends hybrid.
- Options: server-only / client-only / hybrid
- Decision: **Hybrid allowed**, but server-side is source-of-truth for page_view when SSR; client beacon for outbound_click.
- Rationale: Better coverage without visitor IDs.
- Implications: Dedupe must avoid identifiers; enforce short-lived TTL.
- Rollback: Restrict to server-only.
- Needs confirmation: Partial (implementation depends on framework capabilities).

## D-0006 — Blocking open questions policy
- Context: OQ1–OQ3 are blocking for production readiness.
- Decision: Implement ports/adapters with dev defaults, but **mark production deployment blocked** until OQs resolved.
- Rationale: Allows local progress without unsafe assumptions.
- Rollback: None.
- Needs confirmation: No.

## D-0007 — Evidence artifact locations
- Context: Need objective "done" outputs.
- Decision: Use `artifacts/pytest-report.json`, `artifacts/quality_gates_run.json`, `artifacts/coverage.json` (if enforced).
- Rationale: Consistent evidence across tasks.
- Rollback: Change in quality gates doc + tasks.
- Needs confirmation: No.

## D-0008 — Stack continuation (OQ1 resolution)
- Context: OQ1 asks about current stack + routing + SSR implementation.
- Options:
  1) Rewrite to different framework
  2) Continue FastAPI + Next.js with restructure
- Decision: **Continue FastAPI + Next.js stack with Atomic Component restructure**
- Rationale: Proven stack already deployed (v2), SSR working via Next.js server components, JWT auth functional. Restructure to atomic components provides better modularity without framework change.
- Structure: `src/components/` for atomic components, `src/adapters/` for I/O, `src/ports/` for interfaces, `src/api/` as thin shell.
- Rollback: Revert to v2 structure.
- Needs confirmation: No.
- Resolves: OQ1

## D-0009 — Asset storage adapter (OQ2 resolution)
- Context: OQ2 asks about asset storage reality (local disk vs object storage).
- Options:
  1) Local filesystem only
  2) S3 only
  3) Local filesystem with S3-compatible port interface
- Decision: **Local filesystem with S3-compatible port interface**
- Rationale: v2 uses local filesystem (`/data/filestore/`) with Fly.io mounted volume. Works for solo-admin scale. Port interface allows future S3 migration without code changes.
- Constraints: Single volume not horizontally scalable; sufficient for use case.
- Rollback: Implement S3 adapter when scaling needed.
- Needs confirmation: No.
- Resolves: OQ2

## D-0010 — Job runner strategy (OQ3 resolution)
- Context: OQ3 asks about job runner capability for scheduled publishing.
- Options:
  1) Fly.io Machines scheduled task
  2) In-process APScheduler
  3) DB-polled on request
  4) Cron endpoint + external trigger
- Decision: **Cron-triggered idempotent publish endpoint via Fly.io scheduled machines**
- Rationale: Idempotent by design (spec requirement), works with auto-stop machines, no in-process state to lose, SQLite transaction provides claim/lock semantics, meets ≤2 min SLA.
- Implementation: `POST /api/internal/publish-due` triggered every 2 minutes by Fly.io scheduled machine or cron.
- Rollback: Switch to in-process scheduler if latency unacceptable.
- Needs confirmation: No.
- Resolves: OQ3
