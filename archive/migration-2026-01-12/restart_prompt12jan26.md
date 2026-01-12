# Restart Prompt: Little Research Lab - Shell Layer Migration

**Use this prompt to continue the atomic component migration work.**

---

## Prompt for Claude Code Agent

```
I need you to continue the atomic component migration for the Little Research Lab project.

## Current State

The project is at 68% compliance with the Atomic Component Standard v3. The domain layer (16 components in src/components/) is complete, but the shell layer has NOT been migrated and still imports from legacy services.

## Critical Issue: Split-Brain Architecture

- 36 files still import from `src/core/services/` (legacy class-based services)
- 17 legacy service files in `src/core/services/` have NO deprecation notice
- Shell layer expects class-based `ServiceContext` with service instances
- 61 mypy errors, 58 ruff errors

## Read These Files First

1. **QA Review (full details):**
   /Users/naidooone/Documents/little research lab/QA_REVIEW_2026-01-12.md

2. **Evolution Log (EV-0002 is the open issue):**
   /Users/naidooone/Documents/little research lab/little-research-lab-v3_evolution.md

3. **Previous Retrospectives:**
   /Users/naidooone/Documents/little research lab/RETROSPECTIVE_2026-01-12.md
   /Users/naidooone/Documents/little research lab/RETROSPECTIVE_2026-01-12_FOLLOWUP.md

4. **Coding Standards:**
   /Users/naidooone/Documents/development prompts/system-prompts/universal_coding_agent_system_prompt_v3_atomic.md
   /Users/naidooone/Documents/development prompts/devlessons.md

## What Needs To Be Done

### Phase 1: Deprecate Legacy Services (1 hour)
- Create `src/core/services/DEPRECATED.md` with migration map
- Add deprecation warning to `src/core/services/__init__.py`

### Phase 2: Fix Component Internal Imports (2-4 hours)
These components import from legacy - fix them to use ports:
- src/components/render/component.py
- src/components/scheduler/component.py
- src/components/redirects/component.py
- src/components/audit/component.py
- src/components/richtext/component.py
- src/components/render_posts/component.py
- src/components/analytics/component.py

### Phase 3: Migrate Shell Layer (2-3 days)
Update all files importing from `src/core/services/` to use atomic components:
- src/api/routes/admin_*.py
- src/api/routes/public_*.py
- src/api/routes/analytics_ingest.py
- src/shell/hooks/audit_hooks.py

Pattern change:
```python
# BEFORE (wrong)
from src.core.services.settings import SettingsService
result = SettingsService(repo).get_settings()

# AFTER (correct)
from src.components.settings import run, GetSettingsInput
result = run(GetSettingsInput(), repo=repo)
```

### Phase 4: Clean Up (1-2 hours)
- Remove duplicate `src/components/asset/` directory
- Fix remaining ruff warnings: `ruff check --fix src/`
- Verify mypy passes: `python -m mypy src/`
- Run quality gates: `python scripts/quality_gates.py`

## Verification Commands

```bash
cd "/Users/naidooone/Documents/little research lab"

# Check legacy import count (target: 0)
grep -r "from src.core.services" src/ --include="*.py" | wc -l

# Check mypy errors (target: 0)
python -m mypy src/ 2>&1 | grep -c "error:"

# Check ruff errors (target: 0)
ruff check src/ 2>&1 | grep -c "error"

# Run full quality gates
python scripts/quality_gates.py
```

## Definition of Done

- [ ] `src/core/services/DEPRECATED.md` exists
- [ ] `grep -r "from src.core.services" src/components/` returns 0
- [ ] `grep -r "from src.core.services" src/api/` returns 0
- [ ] `grep -r "from src.core.services" src/shell/` returns 0
- [ ] `python -m mypy src/` returns 0 errors
- [ ] `ruff check src/` returns 0 errors
- [ ] `pytest` passes all tests
- [ ] `python scripts/quality_gates.py` shows ALL PASS
- [ ] Duplicate `src/components/asset/` removed
- [ ] EV-0002 marked as resolved in evolution log

## Important Notes

- Use the lessons-advisor agent before making architectural decisions
- Use the qa-reviewer agent after completing each phase
- Update devlessons.md with any new lessons learned
- Create EV entries for any scope changes discovered
- Run quality gates after each phase

Please start by reading QA_REVIEW_2026-01-12.md to understand the full context, then proceed with Phase 1.
```

---

## File References

### Project Files
| File | Purpose |
|------|---------|
| `QA_REVIEW_2026-01-12.md` | Full QA review with remediation plan |
| `little-research-lab-v3_evolution.md` | EV-0002 tracks this issue |
| `RETROSPECTIVE_2026-01-12.md` | Initial remediation history |
| `RETROSPECTIVE_2026-01-12_FOLLOWUP.md` | Follow-up remediation history |
| `REMEDIATION_PLAN.md` | Original migration plan |
| `manifests/component_manifest.json` | Component registry |
| `little-research-lab-v3_tasklist.md` | Task tracking |
| `little-research-lab-v3_spec.md` | Project specification |

### Standards & Lessons
| File | Purpose |
|------|---------|
| `devlessons.md` | 19 rules learned from this project |
| `universal_coding_agent_system_prompt_v3_atomic.md` | Atomic component standard |
| `universal_coding_agent_playbook.md` | Implementation guide |

### Deprecated (Reference Only)
| File | Purpose |
|------|---------|
| `src/services/DEPRECATED.md` | Already deprecated |
| `src/core/services/` | Needs deprecation (17 files) |

---

## Statistics at Time of Pause

| Metric | Value | Target |
|--------|-------|--------|
| Overall Compliance | 68% | 100% |
| Components in src/components/ | 16 | 17 (remove duplicate) |
| Legacy imports | 36 files | 0 |
| mypy errors | 61 | 0 |
| ruff errors | 58 | 0 |
| Tests passing | 1,265 | 1,265+ |

---

## Agents Available

| Agent | When to Use |
|-------|-------------|
| `lessons-advisor` | Before architectural decisions |
| `qa-reviewer` | After completing each phase |
| `business-analyst` | If spec/tasklist needs updating |
| `Explore` | To find files and understand codebase |

---

**Last Updated:** 2026-01-12
**Status:** EV-0002 Open - Shell layer migration pending
