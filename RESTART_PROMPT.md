# Little Research Lab — Restart Prompt

**Date:** 2026-01-12
**Context:** Resume development after QA audit and architectural violation remediation

---

## Prime Directive (Refresh)

Every change must be:
- **Task-scoped** — traceable to a single task from the tasklist
- **Atomic** — smallest meaningful increment
- **Uniform** — component conventions (`src/components/<name>/component.py`, `models.py`, `ports.py`)
- **Rules-driven** — domain behavior from `little-research-lab-v3_rules.yaml`
- **Deterministic** — core has no I/O, globals, or env reads
- **Verifiable** — tests + machine-readable evidence artifacts

**If drift is detected:** HALT → append EV entry → mark task blocked → request BA update.

---

## Required Reading Before Work

```
little-research-lab-v3_spec.md        # What we're building
little-research-lab-v3_tasklist.md    # Task dependency graph (36/50 done)
little-research-lab-v3_rules.yaml     # Domain rules (validation, limits, policies)
little-research-lab-v3_quality_gates.md # Quality requirements
little-research-lab-v3_evolution.md   # Drift history (EV-0001, EV-0002 resolved)
little-research-lab-v3_decisions.md   # Architectural decisions
```

---

## Latest Session Summary (2026-01-12)

### QA Audit Findings (Fixed)

A comprehensive QA audit identified and remediated architectural violations:

| Violation | Components Affected | Resolution |
|-----------|---------------------|------------|
| Global state (`_SESSIONS` dict) | auth | Created `SessionStorePort` + `InMemorySessionStore` adapter |
| Time I/O (`datetime.utcnow()`) | auth, invite, collab, bootstrap | Injected `TimePort` via dependency injection |
| Rules file path mismatch | 31 test files | Updated to use `rules.yaml` |
| `_impl.py` direct imports | 14 external files | Re-exported through `__init__.py`, updated imports |

### _impl.py Remediation Pattern

All 8 `_impl.py` files now have proper re-exports through `__init__.py`:

```python
# src/components/<name>/__init__.py

# Re-exports from _impl for backwards compatibility
from ._impl import (
    ServiceClass,
    ConfigClass,
    # ... other exports
)

__all__ = [
    # Entry points from component.py
    "run",
    "run_*",
    # Models from models.py
    ...
    # Legacy _impl re-exports
    "ServiceClass",
    "ConfigClass",
]
```

**Critical:** When `_impl.py` and `models.py` define the same class name (e.g., `AuditEntry`), import from `_impl.py` FIRST to ensure correct types are used (Enum classes vs Literal types).

---

## Current State

### Quality Gates
| Gate | Status |
|------|--------|
| pytest tests/ | ✅ 1253 passed |
| mypy src/ | ⚠️ 8 pre-existing errors in admin_schedule.py (PublishJob type mismatch) |
| ruff check src/ | ✅ 0 errors |
| Legacy _impl imports | ✅ None in external code |

### Architecture
- **Domain layer:** Fully atomic (`src/components/*/component.py`)
- **Shell layer:** Imports migrated to `src/components/*` (not `_impl` directly)
- **Determinism:** All components use injected Ports for time and storage
- **Legacy services:** Deprecated at `src/core/services/` with DEPRECATED.md

### Known Technical Debt
1. **PublishJob type mismatch:** `src.core.entities.PublishJob` vs `src.components.scheduler.models.PublishJob` — 8 mypy errors in `admin_schedule.py`
2. **Test warnings:** 869 deprecation warnings for `datetime.utcnow()` in test files

---

## Remaining Tasks (14 TODO)

### Backend Tasks (Ready to Start)
| ID | Title | Spec Refs |
|----|-------|-----------|
| T-0017 | Implement /latest alias resolution + admin set_latest | E2.3, TA-0012-0013 |
| T-0021 | Public SSR route for Resource(PDF) + embed/fallback | E3.2, TA-0016-0018 |
| T-0030 | Implement admin schedule calendar API | E5.3, TA-0031 |
| T-0046 | Implement public-only visibility guard | R1 |
| T-0047 | Add privacy schema enforcement check in CI | R4, TA-0035 |
| T-0048 | Implement backups + restore drill script | NFR-R2, TA-0050 |

### UI Tasks (Blocked on Framework Patterns)
| ID | Title | Blocked By |
|----|-------|------------|
| T-0013 | Build admin Settings UI page | Need React/Next.js UI pattern |
| T-0020 | Admin UI for Resource(PDF) create/edit | T-0013 pattern |
| T-0024 | Implement admin rich text editor UI | T-0013 pattern |
| T-0025 | Inline image insert workflow | T-0024 |
| T-0031 | Implement admin calendar UI | T-0030 |
| T-0037 | Implement admin analytics UI | T-0036 |
| T-0022 | PDF viewer embed + iOS/Safari fallback | T-0021 |

### Final Task
| ID | Title | Blocked By |
|----|-------|------------|
| T-0050 | End-to-end regression suite | T-0013, T-0037, T-0040, T-0045, T-0049 |

---

## Lessons Learned (This Session)

### 1. Re-export _impl.py classes through __init__.py
External code should never import from `_impl.py` directly. Always re-export through `__init__.py` for:
- Clean import paths (`from src.components.audit import AuditService`)
- Version control over what's public
- Future refactoring flexibility

### 2. Type consistency when re-exporting
When both `models.py` and `_impl.py` define the same class name:
- Import `_impl.py` FIRST
- Remove duplicates from `models.py` import
- Ensures type consistency (e.g., Enum vs Literal types)

### 3. Deterministic core means NO time I/O
`datetime.utcnow()` and `datetime.now()` violate determinism. Always:
- Create a `TimePort` protocol
- Inject time adapter via dependency injection
- Use `time.now_utc()` in components

### 4. Global state violates determinism
Module-level dicts (like `_SESSIONS = {}`) are global state. Instead:
- Create a `StoragePort` protocol
- Inject storage adapter via dependency injection
- Adapters can use in-memory dicts, Redis, etc.

### 5. Ruff import ordering can expose conflicts
When `ruff check --fix` reorders imports:
- `_impl` imports may come before `models` imports
- This causes "redefinition" errors
- Solution: Remove duplicate names from `models` import

---

## Component Structure Standard

```
src/components/<component_name>/
  __init__.py          # Re-exports (including from _impl.py)
  component.py         # run_*() entry points (pure functions)
  models.py            # Input/Output dataclasses
  ports.py             # Protocol definitions (TimePort, StoragePort, etc.)
  _impl.py             # Legacy service code (re-exported, not imported directly)
```

Entry points are `run_*()` functions that:
- Accept input dataclass + injected ports
- Return output dataclass
- Have NO I/O, globals, or env reads

---

## Task Discipline Reminder

1. **Select ONE task** with satisfied dependencies
2. **Mark it `in_progress`** in tasklist
3. **Confirm spec_refs and tests_required**
4. **Write tests first** (TDD red-green-refactor)
5. **Run quality gates** after completion
6. **Mark task `done`** with evidence paths
7. **If drift detected:** HALT → EV entry → block task

---

## Session Statistics (2026-01-12 QA Audit)

### Remediation Metrics
| Category | Count |
|----------|-------|
| Architectural violations identified | 4 types |
| Components with time I/O fixed | 4 (auth, invite, collab, bootstrap) |
| `datetime.utcnow/now()` calls removed | 13 |
| Global state violations fixed | 1 (_SESSIONS dict) |
| `_impl.py` files with re-exports added | 8 |
| External files updated (imports) | 14 |
| Type conflicts resolved | 3 (audit, redirects, render) |

### Quality Gate Results
| Gate | Before | After |
|------|--------|-------|
| pytest | 1253 pass | 1253 pass |
| mypy src/ | 61+ errors | 8 errors (pre-existing) |
| ruff check | 58 violations | 0 violations |
| Legacy _impl imports | 14 files | 0 files |

### Files Modified
| Category | Files |
|----------|-------|
| Component `__init__.py` (re-exports) | 8 |
| Component `ports.py` (new ports) | 4 |
| Component `component.py` (DI updates) | 4 |
| API routes (import updates) | 9 |
| Shell hooks (import updates) | 1 |
| Adapters created | 1 (InMemorySessionStore) |
| Test files (rules path fix) | 31 |

### Knowledge Base Updates
| Artifact | Changes |
|----------|---------|
| RESTART_PROMPT.md | Complete rewrite |
| devlessons.md | +2 sections, +4 rules (22→26) |
| New lessons documented | 5 |

### Time Investment
- QA audit identification: ~10 min
- Architectural violation fixes: ~30 min
- _impl.py re-export pattern: ~20 min
- Type conflict resolution: ~15 min
- Documentation & lessons: ~15 min

---

## Instructions

**To resume work:**
1. Read the required artifacts (spec, tasklist, rules, evolution)
2. Select a task from "Backend Tasks (Ready to Start)" or discuss priority with user
3. Follow task discipline strictly
4. Run quality gates after each task: `pytest tests/` + `mypy src/` + `ruff check src/`

**If you encounter:**
- Missing spec coverage → HALT, create EV entry
- Test failures unrelated to current task → Note in task, continue if isolated
- Architectural ambiguity → Ask user before proceeding
- Need to import from `_impl.py` → Re-export through `__init__.py` instead
