"""Bootstrap component implementation.

Handles Day 0 system bootstrapping: creates an owner account if the system
is empty and bootstrap is enabled via configuration.
"""

from __future__ import annotations

from uuid import uuid4

from src.domain.entities import User

from .models import BootstrapInput, BootstrapOutput, BootstrapValidationError
from .ports import AuthAdapterPort, RulesPort, TimePort, UserRepoPort


def _validate_input(
    bootstrap_input: BootstrapInput,
) -> tuple[BootstrapValidationError, ...]:
    """Validate bootstrap input parameters."""
    errors: list[BootstrapValidationError] = []

    if not bootstrap_input.bootstrap_email:
        errors.append(
            BootstrapValidationError(
                code="MISSING_EMAIL",
                message="Bootstrap email is required",
                field="bootstrap_email",
            )
        )

    if not bootstrap_input.bootstrap_password:
        errors.append(
            BootstrapValidationError(
                code="MISSING_PASSWORD",
                message="Bootstrap password is required",
                field="bootstrap_password",
            )
        )

    return tuple(errors)


def run_bootstrap(
    bootstrap_input: BootstrapInput,
    user_repo: UserRepoPort,
    auth_adapter: AuthAdapterPort,
    rules: RulesPort,
    time: TimePort,
) -> BootstrapOutput:
    """Execute the bootstrap process.

    Checks if bootstrap is enabled, if users exist, and creates an owner
    user if all conditions are met.

    Args:
        bootstrap_input: Email and password for the owner account.
        user_repo: Repository for user operations.
        auth_adapter: Adapter for password hashing.
        rules: Configuration rules provider.
        time: Time provider for deterministic timestamps.

    Returns:
        BootstrapOutput with the result of the operation.
    """
    # 1. Check if bootstrap is enabled in rules
    bootstrap_config = rules.get_bootstrap_config()
    if not bootstrap_config.enabled_if_no_users:
        return BootstrapOutput.skipped("Bootstrap is not enabled in rules")

    # 2. Check if users already exist
    existing_users = user_repo.list_all()
    if len(existing_users) > 0:
        return BootstrapOutput.skipped("Users already exist in the system")

    # 3. Check if email/password are provided
    if not bootstrap_input.bootstrap_email or not bootstrap_input.bootstrap_password:
        return BootstrapOutput.skipped(
            "Bootstrap email and/or password not provided. "
            "Set LRL_BOOTSTRAP_EMAIL and LRL_BOOTSTRAP_PASSWORD environment variables."
        )

    # 4. Validate input
    validation_errors = _validate_input(bootstrap_input)
    if validation_errors:
        return BootstrapOutput.failed(validation_errors)

    # 5. Create owner user
    password_hash = auth_adapter.hash_password(bootstrap_input.bootstrap_password)
    now = time.now_utc()

    owner = User(
        id=uuid4(),
        email=bootstrap_input.bootstrap_email,
        display_name="Owner (Bootstrap)",
        password_hash=password_hash,
        roles=["owner"],
        status="active",
        created_at=now,
        updated_at=now,
    )

    user_repo.save(owner)

    return BootstrapOutput.created_user(owner)


def run(
    bootstrap_input: BootstrapInput,
    user_repo: UserRepoPort,
    auth_adapter: AuthAdapterPort,
    rules: RulesPort,
    time: TimePort,
) -> BootstrapOutput:
    """Main entry point for the bootstrap component.

    Args:
        bootstrap_input: Email and password for the owner account.
        user_repo: Repository for user operations.
        auth_adapter: Adapter for password hashing.
        rules: Configuration rules provider.
        time: Time provider for deterministic timestamps.

    Returns:
        BootstrapOutput with the result of the operation.
    """
    return run_bootstrap(bootstrap_input, user_repo, auth_adapter, rules, time)
