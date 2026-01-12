from datetime import timedelta
from typing import Literal, cast
from uuid import UUID, uuid4

from src.domain.entities import RoleType, Session, User
from src.domain.policy import PolicyEngine

from .models import (
    AuthOutput,
    CreateSessionInput,
    CreateUserInput,
    ListUsersInput,
    LoginInput,
    UpdateUserInput,
    UserListOutput,
    UserOutput,
    VerifySessionInput,
)
from .ports import AuthAdapterPort, SessionStorePort, TimePort, UserRepoPort


def run_login(
    inp: LoginInput, user_repo: UserRepoPort, auth_adapter: AuthAdapterPort
) -> AuthOutput:
    user = user_repo.get_by_email(inp.email)
    if not user:
        return AuthOutput(success=False, error="Invalid credentials")

    if not auth_adapter.verify_password(inp.password, user.password_hash):
        return AuthOutput(success=False, error="Invalid credentials")

    if user.status != "active":
        return AuthOutput(success=False, error="User account is disabled")

    return AuthOutput(user=user, success=True)


def run_create_session(
    inp: CreateSessionInput,
    auth_adapter: AuthAdapterPort,
    session_store: SessionStorePort,
    time: TimePort,
) -> AuthOutput:
    token = auth_adapter.create_token(inp.user.id, 24 * 60)  # 24 hours
    now = time.now_utc()

    session = Session(
        id=str(uuid4()),
        user_id=inp.user.id,
        token_hash=token,  # Note: using token as hash key for simplified store
        expires_at=now + timedelta(hours=24),
    )
    session_store.save(token, session)
    return AuthOutput(user=inp.user, session=session, token_raw=token, success=True)


def run_verify_session(
    inp: VerifySessionInput,
    user_repo: UserRepoPort,
    session_store: SessionStorePort,
    time: TimePort,
) -> AuthOutput:
    session = session_store.get(inp.token)
    if not session:
        return AuthOutput(success=False, error="Session not found")

    now = time.now_utc()
    if session.expires_at < now:
        session_store.delete(inp.token)
        return AuthOutput(success=False, error="Session expired")

    user = user_repo.get_by_id(session.user_id)
    if not user:
        return AuthOutput(success=False, error="User not found")

    return AuthOutput(user=user, session=session, success=True)


def run_create_user(
    inp: CreateUserInput,
    user_repo: UserRepoPort,
    auth_adapter: AuthAdapterPort,
    policy: PolicyEngine,
    time: TimePort,
) -> UserOutput:
    if not policy.can_manage_users(inp.actor):
        return UserOutput(success=False, error="Access denied")

    if user_repo.get_by_email(inp.email):
        return UserOutput(success=False, error="Email already in use")

    password_hash = auth_adapter.hash_password(inp.password)
    now = time.now_utc()

    new_user = User(
        id=uuid4(),
        email=inp.email,
        display_name=inp.display_name or inp.email.split("@")[0],
        password_hash=password_hash,
        roles=cast(list[RoleType], inp.roles),
        status="active",
        created_at=now,
        updated_at=now,
    )
    user_repo.save(new_user)
    return UserOutput(user=new_user, success=True)


def run_update_user(
    inp: UpdateUserInput,
    user_repo: UserRepoPort,
    policy: PolicyEngine,
    session_store: SessionStorePort,
    time: TimePort,
) -> UserOutput:
    if not policy.can_manage_users(inp.actor):
        return UserOutput(success=False, error="Access denied")

    try:
        uid = UUID(str(inp.target_id))
    except (ValueError, TypeError):
        return UserOutput(success=False, error="Invalid user ID format")

    target = user_repo.get_by_id(uid)
    if not target:
        return UserOutput(success=False, error="User not found")

    # Self-lockout check
    if str(target.id) == str(inp.actor.id):
        is_removing_admin = (
            inp.new_roles is not None and "admin" in target.roles and "admin" not in inp.new_roles
        )
        if is_removing_admin:
            return UserOutput(success=False, error="Cannot remove admin role from yourself")
        if inp.new_status is not None and inp.new_status != "active":
            return UserOutput(success=False, error="Cannot disable yourself")

    if inp.new_status and inp.new_status != "active" and target.status == "active":
        # Remove all sessions for this user
        session_store.delete_by_user(target.id)

    if inp.new_roles is not None:
        target.roles = cast(list[RoleType], inp.new_roles)
    if inp.new_status is not None:
        target.status = cast(Literal["active", "disabled"], inp.new_status)

    target.updated_at = time.now_utc()
    user_repo.save(target)
    return UserOutput(user=target, success=True)


def run_list_users(
    inp: ListUsersInput, user_repo: UserRepoPort, policy: PolicyEngine
) -> UserListOutput:
    if not policy.can_manage_users(inp.actor):
        return UserListOutput(users=[], success=False, error="Access denied")

    return UserListOutput(users=user_repo.list_all(), success=True)


def run(
    inp: (
        LoginInput
        | CreateSessionInput
        | VerifySessionInput
        | CreateUserInput
        | UpdateUserInput
        | ListUsersInput
    ),
    *,
    user_repo: UserRepoPort | None = None,
    auth_adapter: AuthAdapterPort | None = None,
    policy: PolicyEngine | None = None,
    session_store: SessionStorePort | None = None,
    time: TimePort | None = None,
) -> AuthOutput | UserOutput | UserListOutput:
    if isinstance(inp, LoginInput):
        assert user_repo and auth_adapter
        return run_login(inp, user_repo, auth_adapter)

    elif isinstance(inp, CreateSessionInput):
        assert auth_adapter and session_store and time
        return run_create_session(inp, auth_adapter, session_store, time)

    elif isinstance(inp, VerifySessionInput):
        assert user_repo and session_store and time
        return run_verify_session(inp, user_repo, session_store, time)

    elif isinstance(inp, CreateUserInput):
        assert user_repo and auth_adapter and policy and time
        return run_create_user(inp, user_repo, auth_adapter, policy, time)

    elif isinstance(inp, UpdateUserInput):
        assert user_repo and policy and session_store and time
        return run_update_user(inp, user_repo, policy, session_store, time)

    elif isinstance(inp, ListUsersInput):
        assert user_repo and policy
        return run_list_users(inp, user_repo, policy)

    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
