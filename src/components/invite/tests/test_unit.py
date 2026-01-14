"""
Invite component unit tests.

Tests for invitation creation and redemption.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.components.invite import (
    CreateInviteInput,
    RedeemInviteInput,
    run_create,
    run_redeem,
)
from src.domain.entities import Invite, User
from src.domain.policy import PolicyEngine
from src.rules.loader import load_rules

# --- Mock Implementations ---


class MockInviteRepo:
    """In-memory invite repository for testing."""

    def __init__(self) -> None:
        self._invites: dict[UUID, Invite] = {}
        self._by_token_hash: dict[str, Invite] = {}

    def save(self, invite: Invite) -> Invite:
        self._invites[invite.id] = invite
        self._by_token_hash[invite.token_hash] = invite
        return invite

    def get_by_token_hash(self, token_hash: str) -> Invite | None:
        return self._by_token_hash.get(token_hash)


class MockUserRepo:
    """In-memory user repository for testing."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}
        self._by_email: dict[str, User] = {}

    def get_by_email(self, email: str) -> User | None:
        return self._by_email.get(email)

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    def list_all(self) -> list[User]:
        return list(self._users.values())

    def save(self, user: User) -> None:
        self._users[user.id] = user
        self._by_email[user.email] = user


class MockAuthAdapter:
    """Mock auth adapter for testing."""

    def hash_password(self, plain: str) -> str:
        return f"hashed_{plain}"


class MockTimePort:
    """Mock time port for deterministic testing."""

    def __init__(self, fixed_time: datetime | None = None) -> None:
        self._time = fixed_time or datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

    def now_utc(self) -> datetime:
        return self._time

    def advance(self, delta: timedelta) -> None:
        self._time = self._time + delta


def _hash_token(token: str) -> str:
    """Helper to hash tokens for testing."""
    return hashlib.sha256(token.encode()).hexdigest()


# --- Fixtures ---


@pytest.fixture
def invite_repo() -> MockInviteRepo:
    return MockInviteRepo()


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
def policy() -> PolicyEngine:
    rules_path = Path("rules.yaml").resolve()
    rules = load_rules(rules_path)
    return PolicyEngine(rules)


@pytest.fixture
def admin_user(time_port: MockTimePort) -> User:
    """Create an admin user for testing."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        display_name="Admin",
        password_hash="hashed",
        roles=["admin"],
        status="active",
        created_at=time_port.now_utc(),
        updated_at=time_port.now_utc(),
    )


@pytest.fixture
def regular_user(time_port: MockTimePort) -> User:
    """Create a regular user for testing."""
    return User(
        id=uuid4(),
        email="user@example.com",
        display_name="User",
        password_hash="hashed",
        roles=["viewer"],
        status="active",
        created_at=time_port.now_utc(),
        updated_at=time_port.now_utc(),
    )


# --- Create Invite Tests ---


class TestCreateInvite:
    """Test run_create functionality."""

    def test_create_invite_success(
        self,
        admin_user: User,
        invite_repo: MockInviteRepo,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Admin can create invite."""
        inp = CreateInviteInput(creator=admin_user, role="viewer", days_valid=7)
        result = run_create(inp, invite_repo, policy, time_port)

        assert result.success is True
        assert result.token is not None
        assert len(result.token) > 0

    def test_create_invite_access_denied(
        self,
        regular_user: User,
        invite_repo: MockInviteRepo,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Non-admin cannot create invite."""
        inp = CreateInviteInput(creator=regular_user, role="viewer", days_valid=7)
        result = run_create(inp, invite_repo, policy, time_port)

        assert result.success is False
        assert result.error is not None
        assert "cannot create invites" in result.error

    def test_create_invite_stores_hashed_token(
        self,
        admin_user: User,
        invite_repo: MockInviteRepo,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Token is stored as hash, not plaintext."""
        inp = CreateInviteInput(creator=admin_user, role="editor", days_valid=14)
        result = run_create(inp, invite_repo, policy, time_port)

        assert result.success is True
        assert result.token is not None
        # Verify invite is saved with hashed token
        token_hash = _hash_token(result.token)
        saved_invite = invite_repo.get_by_token_hash(token_hash)
        assert saved_invite is not None
        assert saved_invite.role == "editor"


# --- Redeem Invite Tests ---


class TestRedeemInvite:
    """Test run_redeem functionality."""

    def test_redeem_invite_success(
        self,
        invite_repo: MockInviteRepo,
        user_repo: MockUserRepo,
        auth_adapter: MockAuthAdapter,
        time_port: MockTimePort,
    ) -> None:
        """Valid invite can be redeemed."""
        # Create an invite directly
        token = "test_invite_token_123"
        token_hash = _hash_token(token)
        invite = Invite(
            id=uuid4(),
            token_hash=token_hash,
            role="editor",
            expires_at=time_port.now_utc() + timedelta(days=7),
            created_at=time_port.now_utc(),
        )
        invite_repo.save(invite)

        inp = RedeemInviteInput(
            token=token,
            email="newuser@example.com",
            display_name="New User",
            password="password123",
        )
        result = run_redeem(inp, invite_repo, user_repo, auth_adapter, time_port)

        assert result.success is True
        assert result.user is not None
        assert result.user.email == "newuser@example.com"
        assert "editor" in result.user.roles

    def test_redeem_invite_invalid_token(
        self,
        invite_repo: MockInviteRepo,
        user_repo: MockUserRepo,
        auth_adapter: MockAuthAdapter,
        time_port: MockTimePort,
    ) -> None:
        """Invalid token returns error."""
        inp = RedeemInviteInput(
            token="invalid_token",
            email="newuser@example.com",
            display_name="New User",
            password="password123",
        )
        result = run_redeem(inp, invite_repo, user_repo, auth_adapter, time_port)

        assert result.success is False
        assert result.error is not None
        assert "Invalid invite token" in result.error

    def test_redeem_invite_already_redeemed(
        self,
        invite_repo: MockInviteRepo,
        user_repo: MockUserRepo,
        auth_adapter: MockAuthAdapter,
        time_port: MockTimePort,
    ) -> None:
        """Already redeemed invite returns error."""
        token = "already_used_token"
        token_hash = _hash_token(token)
        invite = Invite(
            id=uuid4(),
            token_hash=token_hash,
            role="viewer",
            expires_at=time_port.now_utc() + timedelta(days=7),
            created_at=time_port.now_utc(),
            redeemed_at=time_port.now_utc(),  # Already redeemed
            redeemed_by_user_id=uuid4(),
        )
        invite_repo.save(invite)

        inp = RedeemInviteInput(
            token=token,
            email="another@example.com",
            display_name="Another",
            password="password123",
        )
        result = run_redeem(inp, invite_repo, user_repo, auth_adapter, time_port)

        assert result.success is False
        assert result.error is not None
        assert "already redeemed" in result.error

    def test_redeem_invite_expired(
        self,
        invite_repo: MockInviteRepo,
        user_repo: MockUserRepo,
        auth_adapter: MockAuthAdapter,
        time_port: MockTimePort,
    ) -> None:
        """Expired invite returns error."""
        token = "expired_token"
        token_hash = _hash_token(token)
        invite = Invite(
            id=uuid4(),
            token_hash=token_hash,
            role="viewer",
            expires_at=time_port.now_utc() - timedelta(days=1),  # Expired
            created_at=time_port.now_utc() - timedelta(days=8),
        )
        invite_repo.save(invite)

        inp = RedeemInviteInput(
            token=token,
            email="expired@example.com",
            display_name="Expired",
            password="password123",
        )
        result = run_redeem(inp, invite_repo, user_repo, auth_adapter, time_port)

        assert result.success is False
        assert result.error is not None
        assert "expired" in result.error

    def test_redeem_invite_email_already_registered(
        self,
        invite_repo: MockInviteRepo,
        user_repo: MockUserRepo,
        auth_adapter: MockAuthAdapter,
        time_port: MockTimePort,
    ) -> None:
        """Cannot redeem if email already registered."""
        # Register existing user
        existing = User(
            id=uuid4(),
            email="existing@example.com",
            display_name="Existing",
            password_hash="hashed",
            roles=["viewer"],
            status="active",
            created_at=time_port.now_utc(),
            updated_at=time_port.now_utc(),
        )
        user_repo.save(existing)

        # Create valid invite
        token = "valid_token"
        token_hash = _hash_token(token)
        invite = Invite(
            id=uuid4(),
            token_hash=token_hash,
            role="editor",
            expires_at=time_port.now_utc() + timedelta(days=7),
            created_at=time_port.now_utc(),
        )
        invite_repo.save(invite)

        inp = RedeemInviteInput(
            token=token,
            email="existing@example.com",  # Already registered
            display_name="Duplicate",
            password="password123",
        )
        result = run_redeem(inp, invite_repo, user_repo, auth_adapter, time_port)

        assert result.success is False
        assert result.error is not None
        assert "already registered" in result.error
