# research-lab-bio_spec.md

## Intent

### Goals
- Provide a **Premium, High-Impact** public landing page (“Little Research Lab”) with curated links and rich visual design (Deep Blue/Teal theme).
- Publish **written content** (short posts, longer articles, pages) with **rich blocks** (text, images, charts/graphics) and responsive layout.
- Allow **secure administration** for creating/editing content, uploading assets, and scheduling publication.
- Support **collaboration** with roles and scoped permissions.
- Be built in **Python + Flet** (Web App), utilizing `MainLayout` with Navigation Rail/Drawer and Dark Mode support.

### Non-goals
- Full CMS feature parity (no WYSIWYG complex editor, no multi-site hosting).
- Public user accounts / commenting system (can be future).
- Payments, subscriptions, or analytics dashboards (optional future).

### Success metrics
- M1: Public landing page loads in < 1.5s on typical hosting and is stable under basic load.
- M2: Admin can create a post with blocks (markdown + image + chart) and schedule it; it publishes automatically at the scheduled time.
- M3: Role-based access works (viewer can’t edit; editor can’t publish without permission if rules disallow).
- M4: Content rendering is safe (no script injection via markdown/HTML), uploads are validated/limited.
- M5: UI adheres to "Premium" aesthetics (Consistent Theme, Hover Effects, Responsive Layout, Dark Mode).

---

## Assumptions and constraints

- Tech stack: Python 3.12+, Flet (web target), SQLite initially (file-based), optional Postgres later.
- Hosting: container or VM with persistent volume for DB + uploaded assets.
- External services: none required (email optional for invites; can start with “invite tokens” copied manually).
- File storage: local filesystem under a configured data directory; later can swap to S3-compatible.
- No background worker is assumed. Scheduling must work via:
  - “publish-on-access” (check due scheduled posts on each app start/request cycle), and
  - optional CLI job `publish_due` runnable via cron.

“Halt vs degrade” policy:
- If required secrets/config missing → **halt startup** with actionable error.
- If optional services missing (e.g., email adapter) → **degrade** and disable dependent features.

---

## Personas, roles, RBAC/ABAC

### Personas
- **Owner**: you (primary admin). Full control, can manage users, settings, and content.
- **Editor**: trusted collaborator; can create/edit drafts and assets.
- **Publisher**: can publish/schedule content (may be separate from editor).
- **Viewer (internal)**: can log in and view drafts but cannot modify.
- **Public visitor**: anonymous, read-only access to published content.

### RBAC roles (default)
- `owner`: all permissions.
- `admin`: manage users/roles/settings + all content.
- `publisher`: publish/schedule content; edit content (configurable).
- `editor`: create/edit drafts and assets; cannot publish unless allowed.
- `viewer`: read drafts (internal) only.
- `public`: read published only.

### ABAC rules (scoping)
- Content has `owner_user_id`.
- Editors can edit:
  - content they own, and
  - content where they are explicitly listed as collaborator with `edit` scope.
- Admin/owner can edit all.

---

## Information architecture

### Public routes (read-only)
- `/` : Public landing (“Lab Home”) with avatar, bio, featured links, latest published posts.
- `/l/{slug}` : Public “link redirect” page (optional) or canonical link page.
- `/p/{slug}` : Public post/article page.
- `/page/{slug}` : Public static page (About, Now, Projects).
- `/assets/{asset_id}` : Download/view asset (public if attached to published content or marked public).
- `/tag/{tag}` : Filtered listing.

### Admin routes (auth required)
- `/admin` : Admin dashboard (stats + quick actions).
- `/admin/posts` : List/search/filter posts.
- `/admin/posts/{id}` : Edit post + blocks + preview.
- `/admin/pages` : Manage pages.
- `/admin/links` : Manage landing links / link groups.
- `/admin/assets` : Upload/manage assets.
- `/admin/schedule` : Calendar/list of scheduled content.
- `/admin/users` : User management (owner/admin only).
- `/admin/settings` : Site settings (title, theme, social icons, robots).

---

## Domain model

### Entities

#### User
- `id (uuid)`
- `email (unique)`
- `display_name`
- `password_hash`
- `status`: `active|disabled`
- `created_at`, `updated_at`

#### RoleAssignment
- `id`
- `user_id`
- `role`: `owner|admin|publisher|editor|viewer`
- `created_at`

#### Session
- `id`
- `user_id`
- `token_hash`
- `expires_at`
- `created_at`
- Invariant: expired sessions invalid.

#### ContentItem
- `id (uuid)`
- `type`: `post|page`
- `slug (unique per type)`
- `title`
- `summary`
- `status`: `draft|scheduled|published|archived`
- `publish_at (nullable)`
- `published_at (nullable)`
- `owner_user_id`
- `visibility`: `public|unlisted|private`
- `created_at`, `updated_at`
- Invariants:
  - `published` implies `published_at` not null
  - `scheduled` implies `publish_at` not null and `publish_at > now` at scheduling time
  - `private` content never appears publicly regardless of status

#### ContentBlock
- `id`
- `content_item_id`
- `position (int)`
- `block_type`: `markdown|image|chart|embed|divider`
- `data_json` (validated by rules)
- Invariants:
  - positions contiguous after normalization
  - data_json schema must match block_type schema in rules

#### ContentRevision (audit/versioning)
- `id`
- `content_item_id`
- `revision_no`
- `snapshot_json`
- `created_by_user_id`
- `created_at`

#### LinkItem
- `id`
- `slug (unique)`
- `title`
- `url`
- `icon (optional)`
- `status`: `active|disabled`
- `position`
- `visibility`: `public|unlisted|private`

#### LinkGroup
- `id`
- `title`
- `position`
- `visibility`

#### Asset
- `id (uuid)`
- `filename_original`
- `mime_type`
- `size_bytes`
- `sha256`
- `storage_path`
- `visibility`: `public|unlisted|private`
- `created_by_user_id`
- `created_at`
- Invariants:
  - mime_type must be allowlisted
  - size <= max_upload_bytes

#### CollaborationGrant
- `id`
- `content_item_id`
- `user_id`
- `scope`: `view|edit`
- `created_at`

#### SiteSettings (single row)
- `site_title`
- `site_subtitle`
- `avatar_asset_id (nullable)`
- `theme`: `light|dark|system`
- `social_links_json`
- `updated_at`

#### AuditEvent
- `id`
- `actor_user_id (nullable)`
- `action`
- `target_type`
- `target_id`
- `meta_json`
- `created_at`

---

## State machines

### ContentItem status transitions
- `draft -> scheduled` (if publish_at set and in future)
- `draft -> published` (publish now)
- `scheduled -> published` (when now >= publish_at via scheduler)
- `published -> archived` (remove from public listing)
- `archived -> draft` (optional restore)
Invalid transitions must be rejected by functional core.

---

## Architecture

### Style
- **Atomic components**: small, isolated modules with clear contracts.
- **Functional Core + Imperative Shell**:
  - Core: domain rules, validation, state transitions, queries, command handlers (pure).
  - Shell: Flet UI, DB I/O, filesystem I/O, auth session cookies, time, logging.

### Layout (example)
- `src/`
  - `app_shell/` (Flet routes, adapters)
  - `ui/` (Theme, Layout, Components, Views)
  - `domain/` (entities, commands, policies, state machines)
  - `services/` (use-cases: create/edit/publish/upload)
  - `ports/` (interfaces: repos, clock, file_store, auth, renderer)
  - `adapters/` (sqlite repo, fs filestore, matplotlib renderer, password hasher)
  - `rules/` (rules loader + validator)
  - `manifest/` (component manifest generator/check)
- `tests/`
  - `unit/` (domain pure tests)
  - `integration/` (repo + service + scheduling)
  - `security/` (authz, upload validation, markdown sanitization)
- `artifacts/` (quality gate outputs)

### Rules-first loading
- Load `{project_slug}_rules.yaml` at startup.
- Validate required sections; if invalid/missing → **halt**.
- Expose rules via an immutable `Rules` object used by core validation and services.

### Ports (interfaces)
- `ContentRepoPort`: CRUD for ContentItem/Blocks/Revisions.
- `LinkRepoPort`: CRUD for links/groups.
- `AssetRepoPort`: store metadata.
- `FileStorePort`: save/get/delete binary files.
- `ClockPort`: `now()`.
- `AuthPort`: password verify/hash; session token management.
- `RendererPort`: render chart specs to image bytes (PNG/SVG).

### Canvas / chart rendering
- Provide a reusable “LabCanvas” block:
  - `chart` block stores a **chart spec** (rules-defined JSON schema).
  - Renderer adapter uses matplotlib (or compatible) to generate a PNG.
  - Cache rendered output by `(chart_spec_hash, width, height, dpi)`.

---

## Epics and user stories (with stable IDs)

### Epic E1: Public lab microsite
**E1.1 Landing page**
- AC:
  - Shows site title/subtitle, avatar (if configured), link groups, featured links, latest published posts.
  - Only published + public/unlisted items appear.
- TA:
  - TA-E1.1-1 integration: render landing with seeded data.
  - TA-E1.1-2 security: ensure drafts/private never appear.

**E1.2 Public post/page view**
- AC:
  - `/p/{slug}` and `/page/{slug}` render blocks in order.
  - 404 for missing, 403 for private.
- TA:
  - TA-E1.2-1 unit: block ordering normalization.
  - TA-E1.2-2 security: markdown sanitization test cases.

**E1.3 Link items**
- AC:
  - Admin-configured links appear on landing ordered by group/position.
  - Disabled links are hidden.
- TA:
  - TA-E1.3-1 integration: link ordering.
  - TA-E1.3-2 unit: visibility filtering.

---

### Epic E2: Authentication and secure administration
**E2.1 Login/logout**
- AC:
  - Admin routes require auth; unauthenticated users redirected to login.
  - Sessions expire; logout revokes session.
- TA:
  - TA-E2.1-1 security: session fixation prevention, token hashing.
  - TA-E2.1-2 integration: login flow works end-to-end.

**E2.2 Role-based access control**
- AC:
  - Permissions enforced on each admin action (create/edit/publish/upload/manage users).
  - Owner/admin can manage roles; others cannot.
- TA:
  - TA-E2.2-1 unit: policy matrix tests from rules.
  - TA-E2.2-2 security: forbidden actions return safe errors (no data leaks).

---

### Epic E3: Content authoring and blocks
**E3.1 Create/edit drafts**
- AC:
  - Editor can create a draft post/page with title/slug/summary and blocks.
  - Auto-save updates updated_at; revision created on explicit “Save revision”.
- TA:
  - TA-E3.1-1 integration: create/edit persists and reloads.
  - TA-E3.1-2 unit: slug validation and uniqueness.

**E3.2 Block types**
- AC:
  - `markdown` supports basic formatting; sanitized output.
  - `image` references an Asset and supports caption + max width.
  - `chart` references chart spec and renders via renderer port.
  - `embed` supports allowlisted iframe providers (rules).
- TA:
  - TA-E3.2-1 security: markdown sanitization denies scripts/unsafe links.
  - TA-E3.2-2 unit: block schema validation per rules.
  - TA-E3.2-3 integration: chart render caching works.

**E3.3 Preview**
- AC:
  - Admin preview shows how the post will look publicly without publishing.
- TA:
  - TA-E3.3-1 integration: preview route renders drafts only for authorized users.

---

### Epic E4: Scheduling and publishing workflow
**E4.1 Schedule a post**
- AC:
  - Publisher/admin can set publish_at in the future; status becomes scheduled.
  - Scheduled posts are not public until published.
- TA:
  - TA-E4.1-1 unit: scheduling constraints and transitions.
  - TA-E4.1-2 integration: scheduled post not visible publicly.

**E4.2 Automatic publish**
- AC:
  - When `now >= publish_at`, system transitions scheduled → published and sets `published_at`.
  - Works via:
    - startup/run loop checks, and
    - CLI `publish_due`.
- TA:
  - TA-E4.2-1 integration: with fake clock, scheduled publishes.
  - TA-E4.2-2 regression: idempotent publish_due.

**E4.3 Calendar/list view**
- AC:
  - Admin can view upcoming scheduled items, filter by date/type/status.
- TA:
  - TA-E4.3-1 integration: list correctness and sorting.

---

### Epic E5: Assets and documents
**E5.1 Upload assets**
- AC:
  - Upload allowlisted types only; enforce max size; compute sha256.
  - Store on disk with stable internal name; metadata in DB.
- TA:
  - TA-E5.1-1 security: reject disallowed MIME/extension mismatches.
  - TA-E5.1-2 integration: upload then render image block.

**E5.2 Asset access control**
- AC:
  - Public can fetch only assets that are public OR referenced by published public content.
  - Private assets require auth and authorization.
- TA:
  - TA-E5.2-1 security: direct URL access blocked when unauthorized.

---

### Epic E6: Collaboration
**E6.1 Invite collaborator**
- AC:
  - Owner/admin can create an invite token with role; token can be redeemed once to create/activate user.
  - If email adapter absent, token is shown for manual sharing.
- TA:
  - TA-E6.1-1 integration: token redemption and single-use.
  - TA-E6.1-2 security: token hashing/expiry.

**E6.2 Content-scoped collaboration**
- AC:
  - Owner/admin/editor can grant a user view/edit on a content item.
- TA:
  - TA-E6.2-1 unit: ABAC checks on content actions.
  - TA-E6.2-2 integration: collaborator can edit allowed item only.

---

### Epic E7: Observability, reliability, and ops
**E7.1 Health and diagnostics**
- AC:
  - `/admin` shows DB connectivity status, rules version hash, storage free space check (best effort).
  - Log key actions and failures (structured logs).
- TA:
  - TA-E7.1-1 integration: health report generation.
  - TA-E7.1-2 regression: startup fails fast on missing config.

**E7.2 Backups and restore drill**
- AC:
  - Provide CLI `backup` (copies DB + assets manifest) and `restore` (from backup).
  - Document restore steps.
- TA:
  - TA-E7.2-1 integration: backup then restore yields same content counts and hashes.

---

## Non-functional requirements

### Security & privacy
- Server-side auth; password hashing (argon2/bcrypt).
- Session tokens stored hashed; secure cookie flags where applicable.
- Markdown sanitization + link protocol allowlist (`https`, `mailto` optional) from rules.
- Upload validation: allowlist MIME, extension, magic bytes if available; size limits.
- Rate limits (best effort) on login attempts and upload requests (rules-defined).
- Least privilege for roles and collaboration grants.
- Audit log for admin actions.

### Performance
- Landing page and post render should avoid unnecessary DB roundtrips (use query methods that fetch blocks in one call).
- Chart render caching.

### Reliability
- App start validates rules and DB schema; if mismatch → halt with message.
- Idempotent publish job.

### Maintainability
- Ports/adapters; unit tests for core; integration tests for repo/services.

---

## Hosting / deployment topology

- Single service: Flet server process.
- Persistent volume:
  - `DATA_DIR/db.sqlite3`
  - `DATA_DIR/assets/` (binary files)
  - `DATA_DIR/backups/`
- Env vars:
  - `LAB_SECRET_KEY` (required)
  - `LAB_DATA_DIR` (required)
  - `LAB_BASE_URL` (required for generating absolute links, invites)
  - `LAB_ADMIN_BOOTSTRAP_EMAIL` + `LAB_ADMIN_BOOTSTRAP_PASSWORD` (required only if no users exist)
- Optional:
  - `LAB_EMAIL_ENABLED=false|true`

Backups/restore drill:
- Weekly backup via cron calling `python -m lab.cli backup`.
- Quarterly restore drill in staging.

---

## Observability

- Structured logs: JSON lines with `event`, `actor`, `target`, `request_id`.
- Health: simple internal “health report” view on admin dashboard plus CLI `healthcheck`.

---

## Abuse/safety controls
- Upload quota and size/type allowlists (rules).
- Embed block provider allowlist (rules) and sanitize embed URLs.
- Slug validation to prevent path traversal.
- No arbitrary HTML blocks; markdown sanitized.
- Prevent open redirects: link redirects must validate scheme and optionally enforce domain allowlist.

---

## Regression invariants

- **R1**: Draft/scheduled/private content is never visible to public routes.
- **R2**: Every admin action enforces authz from rules; unauthorized requests never mutate state.
- **R3**: Rules file validation is fail-fast; no silent defaults for required sections.
- **R4**: Upload validation prevents disallowed types and oversize files.
- **R5**: Scheduled publishing is idempotent and monotonic (cannot unpublish without explicit action).
- **R6**: Chart rendering is deterministic for same spec + dimensions (within tolerance) and cached.

---

## Task derivation rules
- Implement vertical slices: public read → auth → authoring → blocks → scheduling → assets → collaboration.
- Each slice must include:
  - domain rules + services (core),
  - adapter (repo/file/render) as needed,
  - UI route,
  - tests (unit + integration + security as applicable).
- No task exceeds ~120 minutes; split by component or test layer.

---

## Unknown-unknowns checklist
- U1: Flet routing limitations for deep links → Control: central router adapter + integration test. TA-U1.
- U2: Markdown renderer safety gaps → Control: sanitize before render; deny raw HTML. TA-U2.
- U3: File MIME spoofing → Control: validate by magic bytes when possible + allowlist. TA-U3.
- U4: Hosting restarts impacting scheduling → Control: publish_due job + check-on-startup. TA-U4.
- U5: SQLite concurrency under load → Control: single-writer pattern + short transactions; port allows swap to Postgres. TA-U5.

---

## Escape hatch registry
- EH1: If block schema validation in YAML becomes too complex, allow a minimal “schema module” escape hatch:
  - `domain/block_schema.py` with strict tests mirroring rules, plus migration plan to JSONSchema later.
  - Must be recorded in decisions and tasks if invoked.

---

## Risks
- Flet web session/auth integration complexity.
- Asset access scoping bugs (must be tested).
- Chart rendering performance if many charts on landing.

---

## Decision summary
- Use rules-first YAML for permissions, limits, and block schemas.
- Use SQLite initially; abstract behind repo ports.
- Provide both “publish-on-access” and CLI publish job for scheduling robustness.
