## COMPONENT_ID
C6-redirects

## PURPOSE
Manage URL redirects for content that has moved or been renamed.
Supports permanent (301) and temporary (302) redirects with conflict detection.

## INPUTS
- `CreateRedirectInput`: Create new redirect (source, target, status_code)
- `UpdateRedirectInput`: Update existing redirect
- `DeleteRedirectInput`: Remove redirect
- `GetRedirectInput`: Get redirect by source path
- `ListRedirectsInput`: List all redirects

## OUTPUTS
- `RedirectOutput`: Single redirect with metadata
- `RedirectListOutput`: List of redirects
- `RedirectOperationOutput`: Operation result with errors

## DEPENDENCIES (PORTS)
- `RedirectRepoPort`: Database access for redirects
- `RulesPort`: Redirect rules (enabled, status codes, constraints)

## SIDE EFFECTS
- Database write on create/update/delete

## INVARIANTS
- I1: Source path must be unique
- I2: No circular redirects
- I3: Status code must be 301 or 302
- I4: Target must be valid URL or relative path
- I5: Cannot redirect to self

## ERROR SEMANTICS
- Returns errors for validation failures
- Conflict detection for duplicate sources

## TESTS
- `tests/unit/test_redirects.py`: (tests)
  - Redirect CRUD operations
  - Circular redirect detection
  - Path validation

## EVIDENCE
- `artifacts/pytest-redirects-report.json`
