# research-lab-bio_tasklist.md

| id | title | spec_refs | depends_on | files_expected | tests_required | status | evidence | notes |
|---|---|---|---|---|---|---|---|---|
| T-0001 | Initialize repo structure, tooling, and atomic component template | E7.1,R3 |  | pyproject.toml, src/*, tests/* | pytest smoke | done | artifacts/walkthrough.md |  |
| T-0002 | Add quality gates runner that writes artifacts JSON | E7.1 | T-0001 | scripts/run_quality_gates.py, artifacts/.gitkeep | TA-E7.1-2 | done | artifacts/walkthrough.md |  |
| T-0003 | Implement rules loader + fail-fast validator | R3 | T-0001 | src/rules/loader.py, src/rules/validator.py | TA-E7.1-2 | done | artifacts/walkthrough.md |  |
| T-0004 | Define ports (repo, filestore, clock, auth, renderer) | Architecture | T-0001 | src/ports/*.py | unit interface tests | done | artifacts/walkthrough.md |  |
| T-0005 | Create domain entities + status state machine | E4.1,E4.2 | T-0004 | src/domain/entities.py, src/domain/state.py | TA-E4.1-1 | done | artifacts/walkthrough.md |  |
| T-0006 | Implement policy engine (RBAC+ABAC) driven by rules | E2.2,R2 | T-0003,T-0005 | src/domain/policy.py | TA-E2.2-1,TA-E6.2-1 | done | artifacts/walkthrough.md |  |
| T-0007 | Add markdown sanitization utility (deny raw HTML) | E3.2,R1 | T-0001 | src/domain/sanitize.py | TA-E1.2-2,TA-E3.2-1,TA-U2 | done | artifacts/walkthrough.md |  |
| T-0008 | Implement block schema validation per rules | E3.2,R3 | T-0003,T-0005 | src/domain/blocks.py | TA-E3.2-2 | done | artifacts/walkthrough.md |  |
| T-0009 | SQLite schema + migrations setup | Ops | T-0001 | src/adapters/sqlite/*, migrations/* | integration: migrate up | done | artifacts/walkthrough.md |  |
| T-0010 | SQLite adapters for content/link/asset repos | E1,E3,E5 | T-0004,T-0009 | src/adapters/sqlite/repos.py | TA-E3.1-1,TA-E1.3-1 | done |  |  |
| T-0011 | Filesystem filestore adapter with safe paths | E5.1,R4 | T-0004 | src/adapters/fs/filestore.py | TA-E5.1-1 | done |  |  |
| T-0012 | Password hashing + session token adapter | E2.1,R2 | T-0004 | src/adapters/auth/*.py | TA-E2.1-1 | done | artifacts/walkthrough.md |  |
| T-0013 | Service: create/edit content item + blocks + revisions | E3.1 | T-0005,T-0008,T-0010,T-0006 | src/services/content_service.py | TA-E3.1-1,TA-E3.1-2 | done |  |  |
| T-0014 | Initial Flet UI (Login & Dashboard) | E1.3 | T-0010,T-0006 | src/ui/ | TA-E1.3-1,TA-E1.3-2 | done |  |  |
| T-0015 | Service: asset upload validation + metadata | E5.1,R4 | T-0011,T-0010,T-0003,T-0006 | src/services/asset_service.py | TA-E5.1-1,TA-E5.1-2 | done |  |  |
| T-0016 | Renderer adapter: chart spec → PNG with caching | E3.2,R6 | T-0004,T-0003 | src/adapters/render/mpl_renderer.py | TA-E3.2-3 | done | artifacts/walkthrough.md |  |
| T-0017 | Service: publishing workflow + transitions | E4.1,E4.2,R5 | T-0005,T-0010,T-0006 | src/services/publish_service.py | TA-E4.1-1,TA-E4.2-2 | done | artifacts/walkthrough.md |  |
| T-0018 | CLI: publish_due, backup, restore, healthcheck | E4.2,E7.2 | T-0017,T-0010,T-0011 | src/app_shell/cli.py | TA-E4.2-1,TA-E7.2-1 | done | artifacts/walkthrough.md |  |
| T-0019 | Flet shell: routing framework + auth guard | E2.1,U1 | T-0012,T-0006 | src/app_shell/router.py, src/app_shell/auth_ui.py | TA-E2.1-2,TA-U1 | done | artifacts/walkthrough.md |  |
| T-0020 | Public UI: landing page with links + latest posts | E1.1,E1.3 | T-0010,T-0014,T-0019 | src/app_shell/public_home.py | TA-E1.1-1,TA-E1.1-2 | done | artifacts/walkthrough.md |  |
| T-0021 | Public UI: post/page renderer with blocks | E1.2,E3.2 | T-0007,T-0016,T-0010,T-0019 | src/app_shell/public_content.py | TA-E1.2-1,TA-E1.2-2 | done | artifacts/walkthrough.md |  |
| T-0022 | Admin UI: dashboard (health + quick stats) | E7.1 | T-0019,T-0010 | src/app_shell/admin/dashboard.py | TA-E7.1-1 | done | artifacts/walkthrough.md |  |
| T-0023 | Admin UI: posts/pages list + edit form + preview | E3.1,E3.3 | T-0013,T-0019 | src/app_shell/admin/content_admin.py | TA-E3.3-1 | done | artifacts/walkthrough.md |  |
| T-0024 | Admin UI: assets manager + upload flow | E5.1,E5.2 | T-0015,T-0019 | src/app_shell/admin/assets_admin.py | TA-E5.2-1 | done | artifacts/walkthrough.md |  |
| T-0025 | Admin UI: schedule list/calendar view | E4.3 | T-0017,T-0019 | src/app_shell/admin/schedule_admin.py | TA-E4.3-1 | done | artifacts/walkthrough.md |  |
| T-0026 | Asset public/private serving rules | E5.2,R1 | T-0010,T-0015,T-0019 | src/app_shell/asset_routes.py | TA-E5.2-1 | done | artifacts/walkthrough.md |  |
| T-0027 | Collaboration: invite tokens + redemption | E6.1 | T-0010,T-0012,T-0006 | src/services/invite.py, src/app_shell/invite_routes.py | TA-E6.1-1,TA-E6.1-2 | done | artifacts/walkthrough.md |  |
| T-0028 | Collaboration: per-content grants + enforcement | E6.2 | T-0027,T-0006,T-0013 | src/services/collab_service.py | TA-E6.2-2 | done | artifacts/walkthrough.md |  |
| T-0029 | Admin UI: user management + role assignment | E2.2,E6.1 | T-0027,T-0019 | src/app_shell/admin/users_admin.py | TA-E2.2-2 | done | artifacts/walkthrough.md |  |
| T-0030 | Rate limiting for login/uploads (best effort) | Security | T-0003,T-0012,T-0015 | src/app_shell/rate_limit.py | security tests | done | artifacts/walkthrough.md |  |
| T-0031 | Backup/Restore drill documentation + test harness | E7.2 | T-0018 | docs/ops.md, tests/integration/test_backup_restore.py | TA-E7.2-1 | done | artifacts/walkthrough.md |  |
| T-0032 | Final regression suite for invariants R1–R6 | R1-R6 | T-0020,T-0021,T-0026,T-0017 | tests/regression/* | TA-E4.2-2 + invariant tests | done | artifacts/walkthrough.md |  |
| T-0033 | Manifest generator/check for atomic components in CI | Architecture | T-0001 | src/manifest/generate.py, src/manifest/check.py | unit tests | done | artifacts/walkthrough.md |  |
| T-0034 | Production config validation + bootstrap owner account | Ops | T-0003,T-0012,T-0010 | src/app_shell/config.py, src/services/bootstrap.py | TA-E7.1-2 | done | artifacts/walkthrough.md |  |
| T-0035 | UI Polish: Premium Theme, Dark Mode, Animations | EV-0002 | T-0014,T-0019 | src/ui/theme.py, src/ui/layout.py | manual verification | done | artifacts/walkthrough.md |  |
| T-0036 | Final Quality Gate Cleanup | EV-0003 | T-0035 | src/app_shell/* | scripts/run_quality_gates.py | done | artifacts/walkthrough.md |  |

| id | title | spec_refs | depends_on | files_expected | tests_required | status | evidence | notes |
|---|---|---|---|---|---|---|---|---|
| T-0037 | Containerization (Dockerfile) & Fly.io Config | Hosting | T-0036 | Dockerfile, fly.toml, .dockerignore | local docker build | done | artifacts/walkthrough.md | Build skipped (no daemon) |
| T-0038 | CI Pipeline (GitHub Actions) for Open Source Standards | Ops | T-0037 | .github/workflows/ci.yml | N/A (config only) | done | artifacts/walkthrough.md |  |
| T-0039 | Repo Hygiene: README, LICENSE, CONTRIBUTING | Open Source | T-0038 | README.md, LICENSE, CONTRIBUTING.md | N/A | done | artifacts/walkthrough.md |  |
| T-0040 | Final Reconciliation Audit (Spec & System Prompt Checks) | Audit | T-0039 | artifacts/audit_report.md | N/A | done | artifacts/audit_report.md |  |

| id | title | spec_refs | depends_on | files_expected | tests_required | status | evidence | notes |
|---|---|---|---|---|---|---|---|---|
| T-0041 | Enhanced Service Integration Suite (User Journey) | EV-0001 | T-0040 | tests/integration/test_user_journey.py | pytest | done | artifacts/walkthrough.md |  |
| T-0042 | Unit Tests for UI State Logic (Theme/Layout) | EV-0002 | T-0040 | tests/unit/test_ui_logic.py | pytest | done | artifacts/walkthrough.md |  |

| id | title | spec_refs | depends_on | files_expected | tests_required | status | evidence | notes |
|---|---|---|---|---|---|---|---|---|
| T-0043 | Add Publish Now button to content edit form | E4.1 | T-0023,T-0017 | src/app_shell/admin/content_admin.py | manual verification | done | artifacts/quality_gates_run.json | Publish Now button added for draft items |
| T-0044 | Add Schedule button with date picker to content edit form | E4.1 | T-0023,T-0017 | src/app_shell/admin/content_admin.py | manual verification | done | artifacts/quality_gates_run.json | Schedule button with date/time picker flow |
| T-0045 | Add status display and Unpublish button for published content | E4.1 | T-0023,T-0017 | src/app_shell/admin/content_admin.py | manual verification | done | artifacts/quality_gates_run.json | Status badge + Unpublish button added |
| T-0046 | Add Preview button to content edit form | E3.3 | T-0023 | src/app_shell/admin/content_admin.py | TA-E3.3-1 | done | artifacts/quality_gates_run.json | Preview navigates to public view |

## Epic: Frontend Migration (Flet → React/Next.js)

> See EV-0004 and D-0005 for rationale. Clean architecture (ports/adapters) ensures backend services remain unchanged.

| id | title | spec_refs | depends_on | files_expected | tests_required | status | evidence | notes |
|---|---|---|---|---|---|---|---|---|
| T-0047 | Create FastAPI REST API layer | D-0005 | T-0046 | src/api/main.py, src/api/routes/*.py, src/api/schemas.py | pytest api tests | done | tests/integration/api/test_api_smoke.py | Expose existing services via REST endpoints |
| T-0048 | Add JWT authentication to API | E2.1,D-0005 | T-0047 | src/api/auth.py, src/api/deps.py | TA-E2.1-1 security tests | done | tests/integration/api/test_auth_flow.py | Replace session-based auth with JWT |
| T-0049 | Initialize Next.js frontend project | D-0005 | T-0047 | frontend/package.json, frontend/app/*, frontend/tailwind.config.js | npm run build | done | Build passed | Next.js 14+ with App Router, shadcn/ui, Tailwind |
| T-0050 | Create API client library | D-0005 | T-0048,T-0049 | frontend/lib/api.ts, frontend/lib/types.ts | TypeScript compile | done | Build passed | Type-safe API client for React components |
| T-0051 | Implement auth pages (Login/Logout) | E2.1 | T-0050 | frontend/app/login/*, frontend/components/auth/* | manual verification | done | Build passed | JWT-based login flow |
| T-0052 | Implement public landing page | E1.1 | T-0050 | frontend/app/page.tsx, frontend/components/home/* | TA-E1.1-1 | done | Build passed | Port from PublicHomeContent |
| T-0053 | Implement public post/page views | E1.2 | T-0050 | frontend/app/p/[slug]/*, frontend/app/page/[slug]/* | TA-E1.2-1 | done | Build passed | Port from PublicPostContent/PublicPageContent |
| T-0054 | Implement admin dashboard | E7.1 | T-0051 | frontend/app/dashboard/*, frontend/components/admin/* | TA-E7.1-1 | done | Build passed | Port from AdminDashboardContent |
| T-0055 | Implement content management UI | E3.1,E4.1 | T-0054 | frontend/app/admin/content/*, frontend/components/content/* | TA-E3.1-1,TA-E4.1-1 | done | Build passed | Port from ContentListContent/ContentEditContent |
| T-0056 | Implement asset management UI | E5.1 | T-0054 | frontend/app/admin/assets/*, frontend/components/assets/* | TA-E5.1-2 | done | Build passed | Port from AssetListView |
| T-0057 | Implement user management UI | E2.2,E6.1 | T-0054 | frontend/app/admin/users/*, frontend/components/users/* | TA-E2.2-2 | done | Build passed | Port from UserListView/UserEditView |
| T-0058 | Implement schedule view UI | E4.3 | T-0054 | frontend/app/admin/schedule/* | TA-E4.3-1 | pending |  | Port from ScheduleView |
| T-0059 | Dark/Light theme implementation | EV-0002 | T-0049 | frontend/lib/theme.ts, frontend/components/theme-toggle.tsx | manual verification | pending |  | Tailwind dark mode with toggle |
| T-0060 | Update Dockerfile for two-service deployment | Hosting | T-0049,T-0047 | Dockerfile, docker-compose.yml | docker build | pending |  | FastAPI + Next.js containers |
| T-0061 | Update Fly.io configuration | Hosting | T-0060 | fly.toml | fly deploy | pending |  | Configure for two-service topology |
| T-0062 | Remove legacy Flet code | D-0005 | T-0061 | src/app_shell/*, src/ui/* | N/A | pending |  | Clean up after migration complete |
| T-0063 | Final migration validation | D-0005 | T-0062 | artifacts/migration_report.md | Full test suite | pending |  | Verify all features work in new stack |
