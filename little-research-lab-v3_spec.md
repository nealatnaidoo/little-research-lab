# little-research-lab-v3 — Implementation Spec (v1)

## 0. Intent

### Goals
- Provide a solo-admin publishing platform supporting: **draft → schedule → auto-publish → measure**.
- Support rich-text posts with inline images and SSR rendering (correct OG/Twitter previews).
- Support **PDF Resource** pages with embedded viewer, strong download UX, **stable share URLs**, and **asset versioning** (immutable versions + optional `/latest` alias).
- Provide an in-app **Settings UI** (no redeploy) that updates public SSR metadata.
- Provide hardened, DST-safe scheduling with a calendar UI and **idempotent** publish jobs.
- Provide **privacy-minimal analytics** (first-party, cookie-less by default) with attribution (UTMs + referrer domain) and funnel metrics for page views → outbound clicks → asset downloads.
- Maintain **zero audience PII** collection/storage.

### Non-goals (explicitly out of scope for this iteration)
- Multi-admin collaboration, roles beyond solo admin, approvals.
- Audience accounts, subscriptions, newsletters, comments, DMs.
- Personalization, fingerprinting, visitor IDs, cross-site tracking.
- URL shortener.
- Advanced image optimization pipeline (P2).
- Full export/backup UI (P2).
- Executing Postgres migration (P2); only define an interface/path.

### Success metrics (observable)
- S1: Admin can create/edit/schedule/publish a post or PDF resource end-to-end from the UI.
- S2: Scheduled content publishes within **≤ 2 minutes** of target time in ≥ 99% of runs (excluding host outages), and never publishes early.
- S3: Asset versioning guarantees immutability: served bytes always match stored sha256, and versioned URLs never change content.
- S4: Public pages have correct SSR metadata (title/description/OG/Twitter) and stable canonical URLs.
- S5: Analytics stores **no IP, no full UA, no visitor IDs, no cookies by default**, and still provides campaign/referrer attribution and funnel counts.

## 1. Assumptions & constraints

### Fixed constraints (from brief)
- Primary CTA is content reading + outbound link clicks.
- **Zero audience PII**: no email capture, no stored visitor identifiers.
- Scheduling: calendar view + true auto-publish.
- Content creation: rich text WYSIWYG with basic inline images + upload already-formatted PDFs.
- Analytics: privacy-minimal, attribution via UTMs + referrer, funnel reporting.
- Collaboration: solo admin only.

### Operational assumptions (must be validated)
- A1: Hosting on Fly.io (or similar) container host; supports web + worker process or cron-like trigger.
- A2: Database SQLite now; future Postgres interface compatibility.
- A3: Admin auth exists (email-based login), but must be hardened.
- A4: SSR required for crawlers/social previews.

### Halt vs degrade rules
- HV1 (Halt): If admin auth cannot be secured per rules (sessions, CSRF, rate limits), **do not ship** public admin endpoints; block release until fixed.
- HV2 (Halt): If asset immutability cannot be guaranteed (e.g., storage adapter cannot provide immutable keys), **halt** and require a compliant adapter.
- HV3 (Degrade): If PDF embed fails in client (Safari/iOS), degrade to “open in new tab” + “download” routes; page must remain usable.
- HV4 (Degrade): If analytics ingestion is unavailable, platform remains functional; analytics dashboard shows “data unavailable” and drops events (do not queue raw PII-like logs).
- HV5 (Halt): If drafts/scheduled content can be publicly routed or appears in sitemap/RSS, **halt** until fixed.

## 2. Personas, roles, and authorization

### Roles
- R1: **Admin** (solo operator). Full CRUD on content, settings, assets, redirects, analytics dashboards; view audit logs.
- R2: **Public Visitor**. Read published content; download public assets as referenced by published pages.

### RBAC/ABAC model
- RBAC: `role=admin` vs `role=public`.
- ABAC: content visibility depends on `ContentItem.status == published`.
- ABAC: asset access depends on “referenced by a published page” OR explicitly public by route (versioned asset route is public, but must not expose draft-only assets in a discoverable way—see rules for referential checks).

### Security defaults
- Deny-by-default for any non-public route.
- Admin routes require authenticated session + CSRF protection (for state-changing requests).
- Rate limits for auth and analytics ingestion.

## 3. Information architecture

### Public routes (SSR)
- Home: `/`
- Post: `/p/{slug}`
- PDF Resource: `/r/{slug}`
- Static: `/robots.txt`, `/sitemap.xml`, `/rss.xml` (if present)
- Asset bytes:
  - Versioned: `/assets/{asset_id}/v/{asset_version_id}`
  - Alias: `/assets/{asset_id}/latest`
  - Download hint: query `?download=1` (affects Content-Disposition only)

### Admin UI routes
- `/admin/login`
- `/admin` (dashboard)
- `/admin/settings`
- `/admin/content` (list + search)
- `/admin/content/new` (type picker)
- `/admin/content/{id}` (editor)
- `/admin/assets`
- `/admin/schedule` (calendar)
- `/admin/analytics`
- `/admin/redirects`
- `/admin/audit`

### API routes (JSON)
- Auth: `POST /api/admin/login`, `POST /api/admin/logout`, `GET /api/admin/session`
- Settings: `GET/PUT /api/admin/settings`
- Content: `GET/POST/PUT/DELETE /api/admin/content`, `POST /api/admin/content/{id}/publish_now`, `POST /api/admin/content/{id}/schedule`, `POST /api/admin/content/{id}/unschedule`
- Assets: `POST /api/admin/assets/upload`, `POST /api/admin/assets/{asset_id}/set_latest`, `GET /api/admin/assets`
- Redirects: `GET/POST/DELETE /api/admin/redirects`
- Analytics: `GET /api/admin/analytics/*`
- Analytics ingestion (public, minimal): `POST /a/event` (first-party endpoint; strict schema)
- Outbound click redirector (optional for measurement): `GET /o/{link_id}` (or `POST` beacon) — must preserve UTMs

## 4. Domain model

### Entities (E)
- **E1 SiteSettings** (singleton)
- **E2 ContentItem**
- **E3 Asset** (logical)
- **E4 AssetVersion** (immutable)
- **E5 PublishJob**
- **E6 AnalyticsEventAggregate**
- **E7 RedirectRule**
- **E8 AuditLogEvent**

### Invariants (must always hold)
- I1: Exactly one active SiteSettings row; reads always succeed (fallback defaults allowed).
- I2: Only `published` ContentItems are publicly routable or appear in sitemap/RSS.
- I3: AssetVersion bytes are immutable; sha256 stored equals sha256 served.
- I4: `/assets/{asset_id}/latest` resolves to exactly one AssetVersion at a time.
- I5: Publish side effects are at-most-once per idempotency key `(content_id, publish_at_utc)`.
- I6: Analytics storage contains no PII fields (no IP, no full UA, no cookies, no visitor IDs).
- I7: Redirect rules do not create loops and do not allow open redirects (targets must be internal).

### State machines

#### SM1 ContentItem.status
- `draft` → `scheduled` (set `publish_at_utc`)
- `scheduled` → `draft` (unschedule)
- `draft|scheduled` → `published` (publish now OR job-run publish)
- `published` → `draft` (unpublish) *(P0 allowed; must remove from public listing/sitemap immediately)*

Guards:
- G1: publish requires content validation success and all referenced assets resolvable.
- G2: scheduled publish requires `publish_at_utc` set and in future (allow “now + 10s” buffer).
- G3: scheduled content must never publish before target time.

#### SM2 PublishJob.status
- `queued` → `running` → `succeeded`
- `queued|running` → `retry_wait`
- `retry_wait` → `running`
- `running` → `failed` (permanent after max attempts)

Guards:
- J1: Unique constraint on `(content_id, publish_at_utc)` ensures idempotency.
- J2: Worker acquires job via transactional “claim” / compare-and-swap.

## 5. Architecture

### Atomic structure (Functional Core + Imperative Shell)
- Functional Core services implement pure domain logic, driven by `little-research-lab-v3_rules.yaml`.
- Imperative Shell adapters perform I/O: HTTP, DB, object storage, job runner, time conversion, analytics ingestion.

### Components (C)
- C1 ContentService (FC): content validation, state transitions, revisioning hooks.
- C2 RenderService (FC): deterministic SSR rendering from content + settings; OG/Twitter tags builder.
- C3 AssetService (FC+IS): upload validation, version creation, hashing, headers, `/latest` pointer management.
- C4 SchedulerService (FC): publish job creation/claim/retry/idempotency; DST-safe time handling via Time Adapter.
- C5 SettingsService (FC): singleton settings read/write; validation; cache invalidation.
- C6 RedirectService (FC): CRUD redirects; loop detection; canonical resolution.
- C7 AnalyticsService (FC): ingest validation, bot classification, dedupe, aggregation bucketing, dashboard queries.
- C8 AuditLogService (FC): record admin actions.

### Ports/adapters (P)
- P1 DB Adapter: repository interfaces for E1–E8; SQLite impl now; Postgres-ready interface.
- P2 Object Storage Adapter: local disk or S3-like; must support immutable keys for AssetVersions.
- P3 Time/Timezone Adapter: Europe/London conversion; DST-safe; deterministic tests.
- P4 Job Runner Adapter: cron/scheduler trigger + worker execution.
- P5 HTTP/SSR Adapter: public SSR routes + admin API + admin UI.
- P6 Analytics Ingestion Adapter: server log hook + optional JS beacon; both must produce same canonical ingestion shape.

### Rules-first loading
- On startup, load `little-research-lab-v3_rules.yaml`, validate against required schema sections.
- Fail fast if required sections missing/invalid.
- All domain decisions reference rule keys; tests must assert rule-driven behavior.

### Persistence overview
- DB: content, settings, assets, redirects, publish jobs, analytics aggregates, audit logs.
- Asset bytes: object storage keyed by immutable version storage key.
- Analytics: aggregated counts only; optional raw ops logs are outside analytics DB and have strict retention.

## 6. Epics, stories, acceptance criteria, and test assertions

> **Story format:** Each story has Acceptance Criteria (AC) and Test Assertions (TA).  
> **TA IDs** are referenced across tasks and quality gates.

### Epic E1 — Settings (no redeploy)
**E1.1 Site settings CRUD**
- AC:
  - Given an authenticated admin, when they GET settings, then a settings object is returned even if DB row missing (fallback defaults).
  - When admin PUT settings with valid fields, then values persist and updated_at changes.
  - Invalid URL/text sizes return 400 with actionable messages.
- TA: TA-0001 (settings defaults), TA-0002 (settings validation), TA-0003 (public SSR reflects settings)

**E1.2 Default OG + metadata**
- AC: Public SSR pages include correct `<title>`, meta description, canonical URL, OG/Twitter tags derived from settings and content.
- TA: TA-0004 (SSR meta snapshot), TA-0005 (OG image resolution rules)

### Epic E2 — Assets & versioning
**E2.1 Asset upload (image/pdf) with allowlists and size limits**
- AC: Upload rejects disallowed MIME types and oversized files; stores bytes under immutable version key; computes sha256; records metadata.
- TA: TA-0006 (MIME allowlist), TA-0007 (size limits), TA-0008 (sha256 integrity)

**E2.2 Serve asset versions with correct headers**
- AC:
  - Versioned route serves immutable bytes, `ETag`, `Cache-Control`, `Content-Disposition` (inline default; attachment when `?download=1`).
  - Adds `X-Content-SHA256` (or equivalent) header.
- TA: TA-0009 (headers correctness), TA-0010 (ETag stable), TA-0011 (download disposition)

**E2.3 `/latest` alias pointer**
- AC: Alias resolves to configured latest version; pointer changes do not affect versioned URLs; redirect or proxy behavior is consistent per rules.
- TA: TA-0012 (latest resolution), TA-0013 (rollback latest pointer)

### Epic E3 — PDF Resource content type
**E3.1 Create/edit Resource(PDF) draft**
- AC: Admin can create a resource item, upload/select PDF asset, choose pinned policy (pinned version or latest), save draft.
- TA: TA-0014 (resource draft persistence), TA-0015 (pinned policy validation)

**E3.2 Public resource rendering + download UX**
- AC: Published resource page SSR renders embedded viewer and provides “download” + “open in new tab” fallbacks; iOS/Safari degrade path works.
- TA: TA-0016 (resource SSR), TA-0017 (embed fallback), TA-0018 (download route works)

### Epic E4 — Rich text posts + inline images
**E4.1 Rich text editor model + schema validation**
- AC: Editor stores canonical rich-text JSON; server validates against allowlisted schema; derived blocks may be produced for renderer compatibility.
- TA: TA-0019 (schema validation), TA-0020 (roundtrip save/load)

**E4.2 Safe paste + sanitization**
- AC: Pasted content is sanitized; no scripts/unsafe attributes survive; links get rel protections (noopener/noreferrer) as per rules.
- TA: TA-0021 (stored XSS prevention), TA-0022 (reflected XSS prevention)

**E4.3 Inline images**
- AC: Admin can insert uploaded images inline; publish is blocked if referenced assets missing; drafts can be saved with warnings.
- TA: TA-0023 (inline image reference), TA-0024 (publish blocks missing assets)

**E4.4 Preview parity**
- AC: Admin preview rendering matches public SSR for same content/settings.
- TA: TA-0025 (preview parity snapshot)

### Epic E5 — Scheduling + calendar UI
**E5.1 Schedule content with Europe/London picker**
- AC: Admin sets publish_at in Europe/London; system stores publish_at_utc; UI displays local time consistently.
- TA: TA-0026 (timezone conversion), TA-0027 (DST boundary cases)

**E5.2 Idempotent auto-publish jobs**
- AC: Worker publishes content at/after target time exactly once; retries do not double-publish; records actual publish time.
- TA: TA-0028 (idempotency), TA-0029 (retry no double publish), TA-0030 (never publish early)

**E5.3 Calendar view + status**
- AC: Admin calendar shows drafts/scheduled/published with statuses; can reschedule/cancel/publish now.
- TA: TA-0031 (calendar API), TA: TA-0032 (reschedule/cancel), TA-0033 (publish now)

### Epic E6 — Analytics v1 (privacy-minimal)
**E6.1 Ingestion endpoint schema + privacy enforcement**
- AC:
  - Ingestion accepts only allowed event types and fields; rejects payloads containing disallowed fields.
  - No cookies required; ignores IP; does not store full UA.
- TA: TA-0034 (schema allowlist), TA-0035 (privacy schema enforcement)

**E6.2 Attribution (UTM + referrer domain)**
- AC: UTMs parsed from URL and stored as dimensions; referrer domain stored; redirects preserve UTMs.
- TA: TA-0036 (utm parse), TA-0037 (referrer domain), TA-0038 (utm preserved across redirects)

**E6.3 Dedupe + bot classification**
- AC: Dedupe prevents double-counting SSR+hydration; bot traffic classified/labeled and excluded from “real” counts by default.
- TA: TA-0039 (dedupe key), TA-0040 (bot classification)

**E6.4 Funnel dashboards**
- AC: Admin can view trends and funnel (page_view → outbound_click → asset_download) by content and campaign dims.
- TA: TA-0041 (dashboard queries), TA-0042 (funnel correctness)

### Epic E7 — Redirect manager + trust gate
**E7.1 CRUD redirects and validations**
- AC: Admin can create 301 redirects; system rejects loops, collisions, chains beyond N, and targets that are not internal routes.
- TA: TA-0043 (loop detection), TA-0044 (no open redirects), TA-0045 (chain limit)

**E7.2 Public resolution + canonicalization**
- AC: Requests to old path return 301 to canonical target; canonical tags match final destination.
- TA: TA-0046 (301 behavior), TA-0047 (canonical tags)

### Epic E8 — Audit logging
**E8.1 Admin action audit trail**
- AC: Admin actions (settings change, publish, upload, redirect change, schedule changes) create audit entries with actor, action, entity refs, timestamp.
- TA: TA-0048 (audit append-only), TA-0049 (audit coverage)

## 7. Non-functional requirements (NFR)

### Security
- NFR-S1: Rate limit auth and analytics ingestion endpoints per rules.
- NFR-S2: Secure sessions (HttpOnly, Secure, SameSite) and CSRF for state changes.
- NFR-S3: Rich text sanitization and output escaping; link rel protections.
- NFR-S4: Upload validation with allowlist + size limits; serve with safe headers (X-Content-Type-Options, etc.).
- NFR-S5: Redirects validated to prevent loops and open redirects.

### Privacy
- NFR-P1: Analytics DB schema must not include IP, email, visitor IDs, cookies, full UA.
- NFR-P2: No audience PII collection; no identifiers.
- NFR-P3: Raw ops logs (if any) have strict retention and are not used for analytics reporting.

### Performance
- NFR-F1: Public SSR pages p95 TTFB ≤ 800ms on modest host; cache SSR where safe (honor settings updated_at).
- NFR-F2: Asset serving supports range requests if feasible; otherwise full downloads must be reliable.

### Reliability
- NFR-R1: Scheduling publishes at/after target time; idempotent.
- NFR-R2: Backups: nightly DB snapshot; restore drill documented and tested.
- NFR-R3: Health endpoints for web and worker.

### Maintainability
- NFR-M1: Rules-first behavior; rule keys referenced in tests.
- NFR-M2: Ports/adapters boundaries enforced; minimal coupling.

## 8. Hosting/deploy topology
- Single container image with:
  - Web process (SSR + admin UI + API + asset serving + analytics ingestion)
  - Worker process (publish job runner) OR web process with safe internal cron trigger per host capability (must satisfy idempotency).
- Environments: dev/staging/prod with separate secrets and storage.

## 9. Backups & restore drill
- DB snapshot nightly to secure storage.
- Asset storage is append-only for versions; ensure bucket/disk backup strategy.
- Restore drill (quarterly): restore DB snapshot to staging; verify:
  - settings readable
  - published content routable
  - asset sha256 matches
  - scheduler resumes without double publish

TA: TA-0050 (restore drill checklist automated where possible)

## 10. Observability
- Logs: structured JSON, no PII.
- Metrics:
  - publish job lag, success rate, retry counts, failures by reason
  - asset 404s, download errors
  - redirect hits, invalid redirect attempts
  - analytics ingestion accepted/rejected counts, drops by reason
- Health: `/healthz` (web), `/healthz/worker` (if separate)

## 11. Abuse & safety controls
- Upload limits and MIME allowlists; reject content-type spoofing (sniff bytes where feasible).
- Analytics ingestion rate limits; drop invalid payloads; optional HMAC token for same-origin beacons (no identifiers).
- Outbound links: add rel protections; optional allowlist/denylist per rules.

## 12. Regression invariants (must-never-break)
- R1: Draft/scheduled content is never publicly accessible or indexed.
- R2: AssetVersion bytes are immutable and sha256 matches served bytes.
- R3: Scheduler never publishes before target time; publishes at most once per idempotency key.
- R4: Analytics DB stores no PII/identifiers; schema checks enforce.
- R5: Redirect manager prevents loops and open redirects; canonical tags correct.
- R6: Settings changes reflect on public SSR within cache TTL; no redeploy required.

## 13. Task derivation rules (for tasklist)
- Prefer vertical slices per epic, but enforce shared foundations first:
  1) rules schema + validator + manifest + quality gates
  2) settings + SSR metadata plumbing
  3) assets versioning + headers
  4) PDF resource
  5) rich text editor + sanitizer + renderer
  6) scheduler + calendar
  7) analytics
  8) redirects + audit polish
- Each task targets 30–120 minutes and produces specific files and tests.

## 14. Unknown-unknowns checklist (risk → control → TA)
- UU1: Host cron reliability → idempotent jobs + claim/lock semantics → TA-0028/29/30
- UU2: SQLite concurrency under worker+web → serialized transactions + bounded retries → TA-0028
- UU3: PDF embed variability → fallback UX + tested “open/download” paths → TA-0017/18
- UU4: Bot traffic inflating analytics → bot classifier + exclude-by-default → TA-0040
- UU5: Cache invalidation for settings/OG → settings updated_at + ETag/TTL strategy → TA-0003/0004

## 15. Open questions (blocking)
- OQ1: Current stack + routing model (framework/runtime) and how SSR is implemented in v2.
- OQ2: Asset storage reality (local disk vs object storage) and constraints.
- OQ3: Job runner capability (existing worker/scheduler vs introduce).

Each OQ must be resolved before production release. Coding agent may implement an adapter interface with dev defaults, but must not assume production without recording decision entries.
