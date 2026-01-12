# DEPRECATED - Legacy Core Services

**Status:** DEPRECATED as of 2026-01-12
**Reason:** Migrated to atomic component pattern in `src/components/`
**Sunset Date:** After shell layer migration is complete

## Migration Map

| Legacy Service | New Component | Notes |
|----------------|---------------|-------|
| `analytics_aggregate.py` | `src/components/analytics/` | Use `run()` with aggregate inputs |
| `analytics_attrib.py` | `src/components/analytics/` | Use `run()` with attribution inputs |
| `analytics_dedupe.py` | `src/components/analytics/` | Use `run()` with dedupe inputs |
| `analytics_ingest.py` | `src/components/analytics/` | Use `run()` with ingest inputs |
| `assets.py` | `src/components/assets/` | Use `run()` with asset inputs |
| `audit.py` | `src/components/audit/` | Use `run()` with audit inputs |
| `canonical.py` | `src/components/render/` | Canonical URL logic moved to render |
| `content.py` | `src/components/content/` | Use `run()` with content inputs |
| `redirects.py` | `src/components/redirects/` | Use `run()` with redirect inputs |
| `render_posts.py` | `src/components/render_posts/` | Use `run()` with render post inputs |
| `render.py` | `src/components/render/` | Use `run()` with render inputs |
| `resource_pdf.py` | `src/components/render/` | PDF rendering moved to render |
| `richtext.py` | `src/components/richtext/` | Use `run()` with richtext inputs |
| `rules.py` | `src/components/rules/` | Use `run()` with rules inputs |
| `scheduler.py` | `src/components/scheduler/` | Use `run()` with scheduler inputs |
| `settings.py` | `src/components/settings/` | Use `run()` with settings inputs |

## DO NOT

- Do not add new code to this directory
- Do not import from these files in new code
- Do not modify these files except to add deprecation warnings

## Migration Pattern

Legacy services used class-based patterns:
```python
# BEFORE (deprecated)
from src.core.services.settings import SettingsService
settings_service = SettingsService(repo)
result = settings_service.get_settings()
```

New atomic components use functional patterns:
```python
# AFTER (correct)
from src.components.settings import run, GetSettingsInput
result = run(GetSettingsInput(), repo=repo)
```

## Removal Timeline

These files will be removed once:
1. All shell layer code (src/api/, src/shell/) imports from `src/components/`
2. All component internal imports use ports, not legacy services
3. All tests use new component patterns
4. `grep -r "from src.core.services" src/` returns 0 results

## References

- EV-0002: Shell layer migration (open)
- QA_REVIEW_2026-01-12.md: Full compliance assessment
- RETROSPECTIVE_2026-01-12_FOLLOWUP.md: Previous remediation details
