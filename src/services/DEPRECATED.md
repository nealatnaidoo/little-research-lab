# DEPRECATED - Legacy Services

**Status:** DEPRECATED as of 2026-01-12
**Reason:** Migrated to atomic component pattern in `src/components/`

## Migration Map

| Legacy Service | New Component |
|----------------|---------------|
| `auth.py` | `src/components/auth/` |
| `collab.py` | `src/components/collab/` |
| `invite.py` | `src/components/invite/` |
| `publish.py` | `src/components/publish/` |
| `bootstrap.py` | `src/components/bootstrap/` |
| `content.py` | `src/components/content/` |
| `asset.py` | `src/components/assets/` |

## DO NOT

- Do not add new code to this directory
- Do not import from these files in new code
- Do not modify these files except to add deprecation warnings

## Migration Notes

These legacy services used class-based patterns:
```python
class AuthService:
    def __init__(self, user_repo, auth_adapter, policy):
        ...
```

The new atomic components use functional patterns:
```python
def run(inp: LoginInput, *, user_repo: UserRepoPort, ...) -> LoginOutput:
    ...
```

## Removal Timeline

These files will be removed once:
1. All shell layer code has been updated to use `src/components/`
2. All tests have been updated to use new components
3. No import references remain to this directory

## References

- EV-0001: Architectural drift remediation
- RETROSPECTIVE_2026-01-12.md: Full remediation details
- REMEDIATION_PLAN.md: Migration phases
