"""
Auth component unit tests.

Tests for authentication, session management, and user administration.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.components.auth import (
    CreateSessionInput,
    CreateUserInput,
    ListUsersInput,
    LoginInput,
    UpdateUserInput,
    VerifySessionInput,
    run_create_session,
    run_create_user,
    run_list_users,
    run_login,
    run_update_user,
    run_verify_session,
)
from src.domain.entities import Session, User
from src.domain.policy import PolicyEngine
from src.rules.loader import load_rules

# --- Mock Implementations ---


class MockUserRepo:
    """In-memory user repository for testing."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}
        self._by_email: dict[str, User] = {}

    def get_by_email(self, email: str) -> User | None:
        return self._by_email.get(email)

    def get_by_id(self, user_id: object) -> User | None:
        if isinstance(user_id, UUID):
            return self._users.get(user_id)
        try:
            return self._users.get(UUID(str(user_id)))
        except (ValueError, TypeError):
            return None

    def save(self, user: User) -> User:
        self._users[user.id] = user
        self._by_email[user.email] = user
        return user

    def list_all(self) -> list[User]:
        return list(self._users.values())


class MockAuthAdapter:
    """Mock auth adapter for testing."""

    def __init__(self) -> None:
        self._passwords: dict[str, str] = {}  # plain -> hash mapping

    def verify_password(self, plain: str, hashed: str) -> bool:
        # Simple mock: hash is "hashed_" + plain
        return hashed == f"hashed_{plain}"

    def hash_password(self, plain: str) -> str:
        return f"hashed_{plain}"

    def create_token(self, user_id: object, ttl_minutes: int) -> str:
        return f"token_{user_id}_{ttl_minutes}"


class MockTimePort:
    """Mock time port for deterministic testing."""

    def __init__(self, fixed_time: datetime | None = None) -> None:
        self._time = fixed_time or datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

    def now_utc(self) -> datetime:
        return self._time

    def advance(self, delta: timedelta) -> None:
        self._time = self._time + delta


class MockSessionStore:
    """In-memory session store for testing."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get(self, token: str) -> Session | None:
        return self._sessions.get(token)

    def save(self, token: str, session: Session) -> None:
        self._sessions[token] = session

    def delete(self, token: str) -> None:
        self._sessions.pop(token, None)

    def delete_by_user(self, user_id: UUID) -> int:
        to_delete = [
            token for token, session in self._sessions.items()
            if session.user_id == user_id
        ]
        for token in to_delete:
            del self._sessions[token]
        return len(to_delete)


# --- Fixtures ---


@pytest.fixture
def user_repo() -> MockUserRepo:
    return MockUserRepo()


@pytest.fixture
def auth_adapter() -> MockAuthAdapter:
    return MockAuthAdapter()


@pytest.fixture
def time_port() -> MockTimePort:
    return MockTimePort()


@pytest.fixture
def session_store() -> MockSessionStore:
    return MockSessionStore()


@pytest.fixture
def policy() -> PolicyEngine:
    rules_path = Path("rules.yaml").resolve()
    rules = load_rules(rules_path)
    return PolicyEngine(rules)


@pytest.fixture
def admin_user(user_repo: MockUserRepo, time_port: MockTimePort) -> User:
    """Create and save an admin user."""
    user = User(
        id=uuid4(),
        email="admin@example.com",
        display_name="Admin User",
        password_hash="hashed_admin123",
        roles=["admin"],
        status="active",
        created_at=time_port.now_utc(),
        updated_at=time_port.now_utc(),
    )
    user_repo.save(user)
    return user


@pytest.fixture
def regular_user(user_repo: MockUserRepo, time_port: MockTimePort) -> User:
    """Create and save a regular user."""
    user = User(
        id=uuid4(),
        email="user@example.com",
        display_name="Regular User",
        password_hash="hashed_user123",
        roles=["viewer"],
        status="active",
        created_at=time_port.now_utc(),
        updated_at=time_port.now_utc(),
    )
    user_repo.save(user)
    return user


# --- Login Tests ---


class TestLogin:
    """Test run_login functionality."""

    def test_login_success(
        self,
        admin_user: User,
        user_repo: MockUserRepo,
        auth_adapter: MockAuthAdapter,
    ) -> None:
        """Successful login with valid credentials."""
        inp = LoginInput(email="admin@example.com", password="admin123")
        result = run_login(inp, user_repo, auth_adapter)

        assert result.success is True
        assert result.user is not None
        assert result.user.email == "admin@example.com"
        assert result.error is None

    def test_login_invalid_email(
        self,
        user_repo: MockUserRepo,
        auth_adapter: MockAuthAdapter,
    ) -> None:
        """Login fails with non-existent email."""
        inp = LoginInput(email="unknown@example.com", password="password")
        result = run_login(inp, user_repo, auth_adapter)

        assert result.success is False
        assert result.user is None
        assert result.error == "Invalid credentials"

    def test_login_invalid_password(
        self,
        admin_user: User,
        user_repo: MockUserRepo,
        auth_adapter: MockAuthAdapter,
    ) -> None:
        """Login fails with wrong password."""
        inp = LoginInput(email="admin@example.com", password="wrongpassword")
        result = run_login(inp, user_repo, auth_adapter)

        assert result.success is False
        assert result.error == "Invalid credentials"

    def test_login_disabled_user(
        self,
        user_repo: MockUserRepo,
        auth_adapter: MockAuthAdapter,
        time_port: MockTimePort,
    ) -> None:
        """Login fails for disabled user."""
        disabled_user = User(
            id=uuid4(),
            email="disabled@example.com",
            display_name="Disabled User",
            password_hash="hashed_disabled123",
            roles=["viewer"],
            status="disabled",
            created_at=time_port.now_utc(),
            updated_at=time_port.now_utc(),
        )
        user_repo.save(disabled_user)

        inp = LoginInput(email="disabled@example.com", password="disabled123")
        result = run_login(inp, user_repo, auth_adapter)

        assert result.success is False
        assert result.error == "User account is disabled"


# --- Session Tests ---


class TestSession:
    """Test session management functionality."""

    def test_create_session_success(
        self,
        admin_user: User,
        auth_adapter: MockAuthAdapter,
        session_store: MockSessionStore,
        time_port: MockTimePort,
    ) -> None:
        """Successfully create a session."""
        inp = CreateSessionInput(user=admin_user)
        result = run_create_session(inp, auth_adapter, session_store, time_port)

        assert result.success is True
        assert result.session is not None
        assert result.token_raw is not None
        assert result.user == admin_user

    def test_verify_session_success(
        self,
        admin_user: User,
        user_repo: MockUserRepo,
        session_store: MockSessionStore,
        time_port: MockTimePort,
    ) -> None:
        """Successfully verify a valid session."""
        # Create session manually
        token = "test_token"
        session = Session(
            id=str(uuid4()),
            user_id=admin_user.id,
            token_hash=token,
            expires_at=time_port.now_utc() + timedelta(hours=24),
        )
        session_store.save(token, session)

        inp = VerifySessionInput(token=token)
        result = run_verify_session(inp, user_repo, session_store, time_port)

        assert result.success is True
        assert result.user == admin_user

    def test_verify_session_not_found(
        self,
        user_repo: MockUserRepo,
        session_store: MockSessionStore,
        time_port: MockTimePort,
    ) -> None:
        """Session verification fails for unknown token."""
        inp = VerifySessionInput(token="unknown_token")
        result = run_verify_session(inp, user_repo, session_store, time_port)

        assert result.success is False
        assert result.error == "Session not found"

    def test_verify_session_expired(
        self,
        admin_user: User,
        user_repo: MockUserRepo,
        session_store: MockSessionStore,
        time_port: MockTimePort,
    ) -> None:
        """Session verification fails for expired session."""
        # Create expired session
        token = "expired_token"
        session = Session(
            id=str(uuid4()),
            user_id=admin_user.id,
            token_hash=token,
            expires_at=time_port.now_utc() - timedelta(hours=1),  # Expired
        )
        session_store.save(token, session)

        inp = VerifySessionInput(token=token)
        result = run_verify_session(inp, user_repo, session_store, time_port)

        assert result.success is False
        assert result.error == "Session expired"
        # Session should be deleted
        assert session_store.get(token) is None


# --- User Management Tests ---


class TestUserManagement:
    """Test user creation and management functionality."""

    def test_create_user_success(
        self,
        admin_user: User,
        user_repo: MockUserRepo,
        auth_adapter: MockAuthAdapter,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Admin can create new user."""
        inp = CreateUserInput(
            actor=admin_user,
            email="newuser@example.com",
            password="newpass123",
            roles=["viewer"],
            display_name="New User",
        )
        result = run_create_user(inp, user_repo, auth_adapter, policy, time_port)

        assert result.success is True
        assert result.user is not None
        assert result.user.email == "newuser@example.com"
        assert result.user.display_name == "New User"

    def test_create_user_access_denied(
        self,
        regular_user: User,
        user_repo: MockUserRepo,
        auth_adapter: MockAuthAdapter,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Non-admin cannot create users."""
        inp = CreateUserInput(
            actor=regular_user,
            email="newuser@example.com",
            password="newpass123",
            roles=["viewer"],
        )
        result = run_create_user(inp, user_repo, auth_adapter, policy, time_port)

        assert result.success is False
        assert result.error == "Access denied"

    def test_create_user_duplicate_email(
        self,
        admin_user: User,
        user_repo: MockUserRepo,
        auth_adapter: MockAuthAdapter,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Cannot create user with existing email."""
        inp = CreateUserInput(
            actor=admin_user,
            email="admin@example.com",  # Already exists
            password="newpass123",
            roles=["viewer"],
        )
        result = run_create_user(inp, user_repo, auth_adapter, policy, time_port)

        assert result.success is False
        assert result.error == "Email already in use"

    def test_update_user_success(
        self,
        admin_user: User,
        regular_user: User,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
        session_store: MockSessionStore,
        time_port: MockTimePort,
    ) -> None:
        """Admin can update other user's roles."""
        inp = UpdateUserInput(
            actor=admin_user,
            target_id=str(regular_user.id),
            new_roles=["editor"],
        )
        result = run_update_user(inp, user_repo, policy, session_store, time_port)

        assert result.success is True
        assert result.user is not None
        assert "editor" in result.user.roles

    def test_update_user_cannot_remove_own_admin(
        self,
        admin_user: User,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
        session_store: MockSessionStore,
        time_port: MockTimePort,
    ) -> None:
        """Admin cannot remove admin role from themselves."""
        inp = UpdateUserInput(
            actor=admin_user,
            target_id=str(admin_user.id),
            new_roles=["viewer"],  # Removing admin
        )
        result = run_update_user(inp, user_repo, policy, session_store, time_port)

        assert result.success is False
        assert result.error == "Cannot remove admin role from yourself"

    def test_update_user_cannot_disable_self(
        self,
        admin_user: User,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
        session_store: MockSessionStore,
        time_port: MockTimePort,
    ) -> None:
        """Admin cannot disable themselves."""
        inp = UpdateUserInput(
            actor=admin_user,
            target_id=str(admin_user.id),
            new_status="disabled",
        )
        result = run_update_user(inp, user_repo, policy, session_store, time_port)

        assert result.success is False
        assert result.error == "Cannot disable yourself"

    def test_update_user_not_found(
        self,
        admin_user: User,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
        session_store: MockSessionStore,
        time_port: MockTimePort,
    ) -> None:
        """Cannot update non-existent user."""
        inp = UpdateUserInput(
            actor=admin_user,
            target_id=str(uuid4()),
            new_roles=["viewer"],
        )
        result = run_update_user(inp, user_repo, policy, session_store, time_port)

        assert result.success is False
        assert result.error == "User not found"

    def test_list_users_success(
        self,
        admin_user: User,
        regular_user: User,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
    ) -> None:
        """Admin can list all users."""
        inp = ListUsersInput(actor=admin_user)
        result = run_list_users(inp, user_repo, policy)

        assert result.success is True
        assert len(result.users) == 2

    def test_list_users_access_denied(
        self,
        regular_user: User,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
    ) -> None:
        """Non-admin cannot list users."""
        inp = ListUsersInput(actor=regular_user)
        result = run_list_users(inp, user_repo, policy)

        assert result.success is False
        assert result.error == "Access denied"
