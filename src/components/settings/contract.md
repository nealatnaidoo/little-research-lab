## COMPONENT_ID
C5-settings

## PURPOSE
Manage site settings with validation and fallback defaults.
Provides singleton settings read/write with cache invalidation for SSR coordination.

## INPUTS
- `GetSettingsInput`: Retrieve current settings (empty input)
- `UpdateSettingsInput`: Update settings with dictionary of field updates
- `ResetSettingsInput`: Reset settings to defaults (empty input)

## OUTPUTS
- `GetSettingsOutput`: Current settings (with defaults fallback)
- `UpdateSettingsOutput`: Updated settings with validation errors if any
- `ResetSettingsOutput`: Default settings after reset

## DEPENDENCIES (PORTS)
- `SettingsRepoPort`: Database access for settings persistence
- `CacheInvalidatorPort`: Optional cache invalidation for SSR (R6)
- `TimePort`: Optional time source for timestamps

## SIDE EFFECTS
- Database write on update/reset (via SettingsRepoPort)
- Cache invalidation on update/reset (via CacheInvalidatorPort)

## INVARIANTS
- I1: GET always returns settings (fallback to defaults if DB row missing)
- I2: Exactly one settings row exists in database
- I3: Validation applied before save
- I4: site_title is required and 1-100 characters
- I5: site_subtitle max 200 characters
- I6: theme must be one of: light, dark, system
- I7: social_links_json URLs must be valid http/https

## ERROR SEMANTICS
- Returns validation errors in output object, does not throw
- Empty updates dictionary is valid (no-op)
- Invalid field types caught by Pydantic and converted to ValidationError

## TESTS
- `tests/unit/test_settings.py`: TA-0001, TA-0002 (30 tests)
  - TA-0001: Settings defaults work when DB row missing
  - TA-0002: Settings validation returns actionable error messages

## EVIDENCE
- `artifacts/pytest-settings-report.json`
