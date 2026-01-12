# Bootstrap Component Contract

## Purpose

The Bootstrap component handles Day 0 system initialization. It creates an initial owner account when the system is first deployed and has no users.

## Entry Points

### `run(bootstrap_input, user_repo, auth_adapter, rules) -> BootstrapOutput`

Main entry point for the bootstrap component.

### `run_bootstrap(bootstrap_input, user_repo, auth_adapter, rules) -> BootstrapOutput`

Execute the bootstrap process with full control over dependencies.

## Input Model

```python
@dataclass(frozen=True)
class BootstrapInput:
    bootstrap_email: str | None
    bootstrap_password: str | None
```

## Output Model

```python
@dataclass(frozen=True)
class BootstrapOutput:
    user: User | None          # Created user, if any
    created: bool              # True if user was created
    skipped_reason: str | None # Reason if skipped
    errors: tuple[BootstrapValidationError, ...]  # Validation errors
    success: bool              # True if operation succeeded (including skips)
```

## Port Dependencies

| Port | Methods | Purpose |
|------|---------|---------|
| `UserRepoPort` | `list_all()`, `save(user)` | User persistence |
| `AuthAdapterPort` | `hash_password(password)` | Password hashing |
| `RulesPort` | `get_bootstrap_config()` | Configuration access |

## Business Logic

1. **Check if bootstrap is enabled**: If `rules.ops.bootstrap_admin.enabled_if_no_users` is `False`, skip with message.

2. **Check for existing users**: If any users exist in the system, skip with message.

3. **Check credentials provided**: If `bootstrap_email` or `bootstrap_password` are not provided, skip with informative message.

4. **Validate input**: Ensure both email and password are valid.

5. **Create owner user**: Hash the password and create a User with:
   - `roles=["owner"]`
   - `status="active"`
   - `display_name="Owner (Bootstrap)"`

## Skip Conditions

The component skips (returns success with no user created) when:

- Bootstrap is disabled in rules
- Users already exist in the system
- Email or password not provided in input

## Error Conditions

The component returns errors when:

- Validation fails (missing required fields)
- User creation fails (propagated from repository)

## Example Usage

```python
from src.components.bootstrap import run, BootstrapInput

result = run(
    bootstrap_input=BootstrapInput(
        bootstrap_email=os.environ.get("LRL_BOOTSTRAP_EMAIL"),
        bootstrap_password=os.environ.get("LRL_BOOTSTRAP_PASSWORD"),
    ),
    user_repo=user_repository,
    auth_adapter=auth_adapter,
    rules=rules_provider,
)

if result.created:
    print(f"Created owner: {result.user.email}")
elif result.skipped_reason:
    print(f"Skipped: {result.skipped_reason}")
elif not result.success:
    for error in result.errors:
        print(f"Error: {error.code} - {error.message}")
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `LRL_BOOTSTRAP_EMAIL` | Email for the owner account |
| `LRL_BOOTSTRAP_PASSWORD` | Password for the owner account |

## Security Considerations

- Password is hashed before storage using the configured hashing algorithm
- Bootstrap only runs when the system has zero users (Day 0 scenario)
- The created user has the `owner` role with full system access
