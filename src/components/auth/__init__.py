"""
Auth component - Authentication and user management.

Handles login, session management, and user administration.
"""

from .component import (
    run,
    run_create_session,
    run_create_user,
    run_list_users,
    run_login,
    run_update_user,
    run_verify_session,
)
from .models import (
    AuthOutput,
    # AuthValidationError, # Removed
    CreateSessionInput,
    CreateUserInput,
    ListUsersInput,
    LoginInput,
    UpdateUserInput,
    UserListOutput,
    UserOutput,
    VerifySessionInput,
)
from .ports import (
    AuthAdapterPort,
    # PolicyPort? models.py doesn't use it. component uses PolicyEngine (from src.domain.policy).
    # Init usually exports Ports for consumers to mock.
    # Let's keep common ports if they exist.
    # models.py doesn't have AuthValidationError.
)

__all__ = [
    # Entry points
    "run",
    "run_create_session",
    "run_create_user",
    "run_verify_session",
    "run_list_users",
    "run_login",
    "run_update_user",
    # Models
    "AuthOutput",
    "CreateSessionInput",
    "CreateUserInput",
    "ListUsersInput",
    "LoginInput",
    "UpdateUserInput",
    "UserListOutput",
    "UserOutput",
    "VerifySessionInput",
    # Ports
    "AuthAdapterPort",
]
