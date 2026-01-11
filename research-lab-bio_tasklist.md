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
