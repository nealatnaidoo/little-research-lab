# Little Research Lab - Remediation Plan

**Created:** 2026-01-12
**Last Updated:** 2026-01-12 (QA Review #2)
**Based On:** QA Review Assessment
**Target:** Full compliance with Atomic Component Standard v3

---

## Executive Summary

The project has significant compliance gaps with the atomic component standard. While functional (1,004 tests, excellent coverage), it deviates from required architectural patterns and lacks proper governance artifacts.

**Current Grade:** C+ (36% Compliant)
**Target Grade:** A (95%+ Compliant)

### Current Status

| Category | Status | Score |
|----------|--------|-------|
| TDD Adherence | PARTIAL | 70% |
| Quality Gates | **FAIL** | 30% |
| Task Discipline | FAIL | 40% |
| Architecture | **FAIL** | 20% |
| Drift Governance | **FAIL** | 0% |
| Rules-First | PASS | 90% |
| Contracts/Manifest | **FAIL** | 0% |

### What's Working Well
- 1,004 tests passing (0 failures)
- Excellent ports/adapters architecture (15 Protocol definitions)
- Comprehensive rules.yaml (217 lines)
- Complete BA artifacts (spec, tasklist, rules, quality gates, decisions)
- 43 tasks completed

---

## Phase 1: Immediate Fixes (BLOCKING)

**Duration:** 2-4 hours
**Priority:** CRITICAL - Must complete before any other work

### Task 1.0: Fix Lint Error (NEW)

**File:** `src/core/services/analytics_aggregate.py`

| Line | Issue | Fix |
|------|-------|-----|
| 19 | Unused import `field` | Remove `field` from import: `from dataclasses import dataclass` |

```bash
# Quick fix
ruff check --fix src/core/services/analytics_aggregate.py
```

### Task 1.1: Fix render_posts.py Type Errors

**File:** `src/core/services/render_posts.py`

| Line | Issue | Fix |
|------|-------|-----|
| 322 | Returns `Any` instead of `str` | Add explicit `-> str` return type |
| 401 | `headings` lacks type annotation | Change to `headings: list[dict[str, Any]] = []` |

### Task 1.2: Fix resource_pdf.py Type Errors

**File:** `src/core/services/resource_pdf.py`

| Line | Issue | Fix |
|------|-------|-----|
| 75 | `'resource_pdf'` not in `ContentType` | Extend `ContentType` in `src/domain/entities.py` |
| 79 | `status` field typed as `str` | Change to `status: ContentStatus` |

**Required change in `src/domain/entities.py`:**
```python
# Before
ContentType = Literal["post", "page"]

# After
ContentType = Literal["post", "page", "resource_pdf"]
```

### Task 1.3: Fix admin_assets.py MockStorage Interface

**File:** `src/api/routes/admin_assets.py`

**Issue (Line 177):** `MockStorage.put()` signature doesn't match `StoragePort`

**Fix:** Update `MockStorage` class (lines 145-162):
```python
class MockStorage:
    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}

    def put(
        self,
        key: str,
        data: bytes | BinaryIO,
        content_type: str,
        *,
        expected_sha256: str | None = None,
    ) -> StoredObject:
        data_bytes = data if isinstance(data, bytes) else data.read()
        self._data[key] = data_bytes
        import hashlib
        sha256 = hashlib.sha256(data_bytes).hexdigest()
        return StoredObject(
            key=key,
            size_bytes=len(data_bytes),
            content_type=content_type,
            sha256=sha256,
            etag=sha256[:16],
        )
```

### Phase 1 Quality Gate
```bash
cd "/Users/naidooone/Documents/little research lab"
ruff check src/            # Must return 0 errors
python -m mypy src/        # Must return 0 errors
pytest                     # All 1,004 tests must pass
```

### Phase 1 Checklist
- [ ] Task 1.0: Remove unused `field` import from `analytics_aggregate.py:19`
- [ ] Task 1.1: Fix type annotations in `render_posts.py:322,401`
- [ ] Task 1.2: Extend `ContentType` in `entities.py`, fix `resource_pdf.py:75,79`
- [ ] Task 1.3: Fix `MockStorage` interface in `admin_assets.py:177`
- [ ] Verify: `ruff check src/` passes
- [ ] Verify: `mypy src/` passes
- [ ] Verify: All 1,004 tests pass

---

## Phase 2: Architectural Refactor

**Duration:** 3-5 days
**Priority:** HIGH

### Phase 2A: Create Component Structure (Day 1-2)

#### Component Mapping

| Current Service | New Component Path | ID |
|-----------------|-------------------|-----|
| `src/core/services/rules.py` | `src/components/rules/` | C0 |
| `src/core/services/settings.py` | `src/components/settings/` | C5 |
| `src/core/services/content.py` | `src/components/content/` | C1 |
| `src/core/services/assets.py` | `src/components/assets/` | C3 |
| `src/core/services/richtext.py` | `src/components/richtext/` | C1-sub |
| `src/core/services/render.py` | `src/components/render/` | C2 |
| `src/core/services/render_posts.py` | `src/components/render_posts/` | C2-sub |
| `src/core/services/scheduler.py` | `src/components/scheduler/` | C4 |
| `src/core/services/resource_pdf.py` | `src/components/resource_pdf/` | C1-sub |

#### Required Structure per Component
```
src/components/{component_name}/
  __init__.py
  component.py      # Main run() function
  models.py         # Input/Output models
  ports.py          # Protocol definitions
  contract.md       # Component contract
  adapters/         # Optional
  tests/
    __init__.py
    test_unit.py
    test_properties.py  # Optional
```

### Phase 2B: Migration Pattern (Day 2-4)

#### Example: Settings Component Migration

**1. Create `src/components/settings/models.py`:**
```python
from dataclasses import dataclass
from src.domain.entities import SiteSettings, ValidationError

@dataclass(frozen=True)
class GetSettingsInput:
    pass

@dataclass(frozen=True)
class GetSettingsOutput:
    settings: SiteSettings

@dataclass(frozen=True)
class UpdateSettingsInput:
    site_title: str | None = None
    site_subtitle: str | None = None
    # ... other fields

@dataclass(frozen=True)
class UpdateSettingsOutput:
    settings: SiteSettings
    errors: list[ValidationError]
```

**2. Create `src/components/settings/ports.py`:**
```python
from typing import Protocol
from src.domain.entities import SiteSettings

class SettingsRepoPort(Protocol):
    def get(self) -> SiteSettings | None: ...
    def save(self, settings: SiteSettings) -> SiteSettings: ...
```

**3. Create `src/components/settings/component.py`:**
```python
from .models import GetSettingsInput, GetSettingsOutput, UpdateSettingsInput, UpdateSettingsOutput
from .ports import SettingsRepoPort

def run(
    inp: GetSettingsInput | UpdateSettingsInput,
    *,
    repo: SettingsRepoPort,
    rules: Rules,
) -> GetSettingsOutput | UpdateSettingsOutput:
    """Pure functional entry point - no I/O, deterministic."""
    if isinstance(inp, GetSettingsInput):
        return _handle_get(repo, rules)
    return _handle_update(inp, repo, rules)
```

**4. Create `src/components/settings/contract.md`:**
```markdown
## COMPONENT_ID
C5-settings

## PURPOSE
Manage site settings with validation.

## INPUTS
- GetSettingsInput: Retrieve current settings
- UpdateSettingsInput: Update settings fields

## OUTPUTS
- GetSettingsOutput: Current settings
- UpdateSettingsOutput: Updated settings with validation errors

## DEPENDENCIES (PORTS)
- SettingsRepoPort: Database access
- Rules: Validation configuration

## SIDE EFFECTS
- Database write on update

## INVARIANTS
- Exactly one settings row exists
- Validation applied before save

## ERROR SEMANTICS
- Returns validation errors in output, does not throw

## TESTS
- test_unit.py: TA-0001, TA-0002

## EVIDENCE
- artifacts/pytest-settings-component-report.json
```

#### Migration Order (by dependency)
1. `rules/` (no dependencies)
2. `settings/` (depends on rules, db)
3. `content/` (depends on rules, db)
4. `assets/` (depends on rules, db, storage)
5. `richtext/` (depends on rules)
6. `render/` (depends on settings)
7. `render_posts/` (depends on richtext)
8. `scheduler/` (depends on content, time, jobs)
9. `resource_pdf/` (depends on content, assets)

### Phase 2C: Update Shell Layer (Day 4-5)

Update API routes in `src/api/routes/` to:
1. Import from `src/components/` instead of `src/core/services/`
2. Construct input models
3. Call `run()` functions
4. Convert output to response models

**Files to update (14 import occurrences):**
- `src/api/routes/admin_*.py`
- `src/api/routes/public_*.py`
- `src/api/deps.py`

### Phase 2D: Create All 8 Component Contracts

Required contracts:
- [ ] `src/components/content/contract.md`
- [ ] `src/components/render/contract.md`
- [ ] `src/components/assets/contract.md`
- [ ] `src/components/scheduler/contract.md`
- [ ] `src/components/settings/contract.md`
- [ ] `src/components/redirects/contract.md`
- [ ] `src/components/analytics/contract.md`
- [ ] `src/components/audit/contract.md`

### Phase 2 Quality Gate
```bash
python -m mypy src/           # 0 errors
pytest                        # All tests pass
find src/components -name "contract.md" | wc -l  # Should be 8+
```

### Phase 2 Checklist
- [ ] Create component directory skeleton for all 9 components
- [ ] Migrate `rules/` component (no dependencies)
- [ ] Migrate `settings/` component
- [ ] Migrate `content/` component
- [ ] Migrate `assets/` component
- [ ] Migrate `richtext/` component
- [ ] Migrate `render/` component
- [ ] Migrate `render_posts/` component
- [ ] Migrate `scheduler/` component
- [ ] Migrate `resource_pdf/` component
- [ ] Update shell layer imports
- [ ] Create all 8 component contracts
- [ ] Verify all 1,004 tests still pass

---

## Phase 3: Process Improvements

**Duration:** 1-2 days
**Priority:** MEDIUM

### Task 3.1: Populate Evolution Log

**File:** `little-research-lab-v3_evolution.md`

Add EV-0001 entry (should be added IMMEDIATELY, before Phase 2):
```markdown
## Open

- EV-0001
  - date: 2026-01-12
  - trigger: AC-TA mismatch / architectural deviation
  - description: Implementation used class-based services in src/core/services/
    instead of atomic components in src/components/ with run() entry points.
  - impact:
    - affected_spec_ids: E0, all component specs
    - affected_tasks: T-0001 through T-0043
  - proposed_change: Refactor to atomic component structure per remediation plan
  - decision_refs: D-0011 (to be created)
  - status: open
```

### Task 3.2: Update Manifest

**File:** `manifests/component_manifest.json`

After Phase 2:
1. Change `"status": "planned"` → `"status": "implemented"`
2. Update paths to `src/components/` structure
3. Update contract paths to actual locations
4. Set `generated_at` timestamp

### Task 3.3: Establish Git Standards

For future commits:
- Prefix with task ID: `T-0XXX: <description>`
- Reference TA IDs in commit body
- Never commit without passing quality gates

Example workflow:
```bash
# TDD commit pattern
git commit -m "T-0044: Add failing test for TA-0101"
# ... implement ...
git commit -m "T-0044: Implement feature for TA-0101"
git commit -m "T-0044: Add evidence artifacts"
```

### Task 3.4: Quality Gates Runner ✅ ALREADY IMPLEMENTED

**File:** `scripts/run_quality_gates.py`

The quality gates runner already exists and produces:
- `artifacts/quality_gates_run.json`

**Action:** Update tasklist to mark T-0003 as done.

### Task 3.5: Document TDD Pattern

For future work:
1. Commit failing test: `T-0XXX: Add failing test for <feature>`
2. Commit implementation: `T-0XXX: Implement <feature>`
3. Commit evidence: `T-0XXX: Add evidence artifacts`

### Task 3.6: Complete Pending Tasks

**17 TODO tasks remaining** (mostly UI components):
- T-0003: Quality gates runner → Mark as DONE (already exists)
- T-0004: CI integration → Create `.github/workflows/quality_gates.yml`
- UI tasks (T-0005 through T-0060) → Continue as planned

---

## Dependency Graph

```
Phase 1 (Immediate Fixes) ────────────────────────────────────────┐
  ├── 1.0: analytics_aggregate.py (lint)                          │
  ├── 1.1: render_posts.py (types)                                │
  ├── 1.2: resource_pdf.py + entities.py (types)                  │
  └── 1.3: admin_assets.py (types)                                │
                                                                  ▼
Phase 2 (Architecture) ───────────────────────────────────────────┐
  ├── 2A: Create component skeletons                              │
  │     └── 2B: Migrate components (in dependency order)          │
  │           ├── 2B.1: rules                                     │
  │           ├── 2B.2: settings                                  │
  │           ├── 2B.3: content                                   │
  │           ├── 2B.4: assets                                    │
  │           ├── 2B.5: richtext                                  │
  │           ├── 2B.6: render                                    │
  │           ├── 2B.7: render_posts                              │
  │           ├── 2B.8: scheduler                                 │
  │           └── 2B.9: resource_pdf                              │
  ├── 2C: Update shell layer (depends on 2B)                      │
  └── 2D: Create contracts (parallel with 2B/2C)                  │
                                                                  ▼
Phase 3 (Process) ────────────────────────────────────────────────┘
  ├── 3.1: Evolution log entry (DO FIRST)
  ├── 3.2: Update manifest
  ├── 3.3: Git standards
  ├── 3.4: Quality gates runner ✅ DONE
  ├── 3.5: TDD documentation
  └── 3.6: Complete pending tasks
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking functionality during refactor | Run full test suite after each step; keep old services as deprecated aliases |
| Scope creep | Strict task discipline; create EV entries for discovered issues |
| Incomplete contracts | Use template consistently; automate validation in CI |
| Test regression | Run all 1,004 tests after each component migration |

---

## Success Criteria

### Phase 1 Complete ✅
- [x] `ruff check src/` returns 0 errors
- [x] `mypy src/` returns 0 errors
- [x] All 1,265 tests pass

### Phase 2 Complete ✅
- [x] `src/components/` contains 11 component directories
- [x] 11 `contract.md` files created (rules, settings, content, assets, render, render_posts, richtext, scheduler, redirects, analytics, audit)
- [x] All 11 components: Full atomic pattern (`run()` entry point, models.py, ports.py, component.py)
- [x] All quality gates pass (lint, types, tests)
- [x] All tests still pass

### Phase 3 Pending
- [ ] Evolution log has EV-0001 entry
- [ ] Manifest status fields accurate
- [x] Quality gates runner produces artifacts ✅
- [ ] Git workflow documented
- [ ] T-0003 marked as done

---

## Quick Start Commands

```bash
# Phase 1: Fix immediate issues
cd "/Users/naidooone/Documents/little research lab"

# Fix lint error
ruff check --fix src/core/services/analytics_aggregate.py

# Check current type errors
python -m mypy src/

# After fixing all issues, verify:
ruff check src/ && python -m mypy src/ && pytest

# Phase 2: Create component skeleton (example)
mkdir -p src/components/settings/{adapters,tests}
touch src/components/settings/{__init__.py,component.py,models.py,ports.py,contract.md}
touch src/components/settings/tests/{__init__.py,test_unit.py}

# Phase 3: Validate
find src/components -name "contract.md" | wc -l
python scripts/run_quality_gates.py
```

---

## Appendix: Current Quality Gate Output

```
=== Little Research Lab: Quality Gates Runner ===
[lint]  PASS
[types] PASS
[tests] PASS - 1,265 tests passed

Overall: SUCCESS - All quality gates passed.
```

---

## Change Log

| Date | Change |
|------|--------|
| 2026-01-12 | Initial plan created |
| 2026-01-12 | Updated after QA Review #2: Added Task 1.0 (lint error), updated test count to 1,004, marked Task 3.4 as done |
| 2026-01-12 | Phase 1 COMPLETE: All type/lint errors fixed |
| 2026-01-12 | Phase 2 PARTIAL: Created 11 component directories with contracts; rules and settings components fully migrated to atomic pattern |
| 2026-01-12 | Phase 2 COMPLETE: All 11 components migrated to atomic pattern with run() entry points, models, and ports |
