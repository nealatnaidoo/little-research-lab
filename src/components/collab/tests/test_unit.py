"""
Collab component unit tests.

Tests for collaboration grant, revoke, and list functionality.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.components.collab import (
    GrantAccessInput,
    ListCollaboratorsInput,
    RevokeAccessInput,
    run_grant,
    run_list,
    run_revoke,
)
from src.domain.entities import CollaborationGrant, ContentItem, User
from src.domain.policy import PolicyEngine
from src.rules.loader import load_rules

# --- Mock Implementations ---


class MockCollabRepo:
    """In-memory collab repository for testing."""

    def __init__(self) -> None:
        self._grants: dict[UUID, CollaborationGrant] = {}

    def get_by_content_and_user(
        self, content_id: UUID, user_id: UUID
    ) -> CollaborationGrant | None:
        for grant in self._grants.values():
            if grant.content_item_id == content_id and grant.user_id == user_id:
                return grant
        return None

    def list_by_content(self, content_id: UUID) -> list[CollaborationGrant]:
        return [g for g in self._grants.values() if g.content_item_id == content_id]

    def save(self, grant: CollaborationGrant) -> CollaborationGrant:
        self._grants[grant.id] = grant
        return grant

    def delete(self, grant_id: UUID) -> None:
        self._grants.pop(grant_id, None)


class MockContentRepo:
    """In-memory content repository for testing."""

    def __init__(self) -> None:
        self._items: dict[UUID, ContentItem] = {}

    def get_by_id(self, content_id: UUID) -> ContentItem | None:
        return self._items.get(content_id)

    def add(self, item: ContentItem) -> None:
        self._items[item.id] = item


class MockUserRepo:
    """In-memory user repository for testing."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}
        self._by_email: dict[str, User] = {}

    def get_by_email(self, email: str) -> User | None:
        return self._by_email.get(email)

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    def add(self, user: User) -> None:
        self._users[user.id] = user
        self._by_email[user.email] = user


class MockTimePort:
    """Mock time port for deterministic testing."""

    def __init__(self, fixed_time: datetime | None = None) -> None:
        self._time = fixed_time or datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

    def now_utc(self) -> datetime:
        return self._time


# --- Fixtures ---


@pytest.fixture
def collab_repo() -> MockCollabRepo:
    return MockCollabRepo()


@pytest.fixture
def content_repo() -> MockContentRepo:
    return MockContentRepo()


@pytest.fixture
def user_repo() -> MockUserRepo:
    return MockUserRepo()


@pytest.fixture
def time_port() -> MockTimePort:
    return MockTimePort()


@pytest.fixture
def policy() -> PolicyEngine:
    rules_path = Path("rules.yaml").resolve()
    rules = load_rules(rules_path)
    return PolicyEngine(rules)


@pytest.fixture
def owner_user(user_repo: MockUserRepo, time_port: MockTimePort) -> User:
    """Create and save an owner user."""
    user = User(
        id=uuid4(),
        email="owner@example.com",
        display_name="Content Owner",
        password_hash="hashed",
        roles=["admin"],
        status="active",
        created_at=time_port.now_utc(),
        updated_at=time_port.now_utc(),
    )
    user_repo.add(user)
    return user


@pytest.fixture
def collaborator_user(user_repo: MockUserRepo, time_port: MockTimePort) -> User:
    """Create and save a collaborator user."""
    user = User(
        id=uuid4(),
        email="collaborator@example.com",
        display_name="Collaborator",
        password_hash="hashed",
        roles=["viewer"],
        status="active",
        created_at=time_port.now_utc(),
        updated_at=time_port.now_utc(),
    )
    user_repo.add(user)
    return user


@pytest.fixture
def content_item(
    owner_user: User, content_repo: MockContentRepo, time_port: MockTimePort
) -> ContentItem:
    """Create and save a content item."""
    item = ContentItem(
        id=uuid4(),
        owner_user_id=owner_user.id,
        type="post",
        title="Test Content",
        slug="test-content",
        status="draft",
        summary="Test summary",
        blocks=[],
        created_at=time_port.now_utc(),
        updated_at=time_port.now_utc(),
    )
    content_repo.add(item)
    return item


# --- Grant Tests ---


class TestGrantAccess:
    """Test run_grant functionality."""

    def test_grant_access_success(
        self,
        owner_user: User,
        collaborator_user: User,
        content_item: ContentItem,
        collab_repo: MockCollabRepo,
        content_repo: MockContentRepo,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Owner can grant edit access to collaborator."""
        inp = GrantAccessInput(
            actor=owner_user,
            content_id=content_item.id,
            target_email="collaborator@example.com",
            scope="edit",
        )
        result = run_grant(
            inp, collab_repo, content_repo, user_repo, policy, time_port
        )

        assert result.success is True
        assert result.grant is not None
        assert result.grant.user_id == collaborator_user.id
        assert result.grant.scope == "edit"

    def test_grant_access_content_not_found(
        self,
        owner_user: User,
        collab_repo: MockCollabRepo,
        content_repo: MockContentRepo,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Grant fails if content doesn't exist."""
        inp = GrantAccessInput(
            actor=owner_user,
            content_id=uuid4(),
            target_email="collaborator@example.com",
            scope="edit",
        )
        result = run_grant(
            inp, collab_repo, content_repo, user_repo, policy, time_port
        )

        assert result.success is False
        assert result.error == "Content not found"

    def test_grant_access_target_not_found(
        self,
        owner_user: User,
        content_item: ContentItem,
        collab_repo: MockCollabRepo,
        content_repo: MockContentRepo,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Grant fails if target user doesn't exist."""
        inp = GrantAccessInput(
            actor=owner_user,
            content_id=content_item.id,
            target_email="unknown@example.com",
            scope="edit",
        )
        result = run_grant(
            inp, collab_repo, content_repo, user_repo, policy, time_port
        )

        assert result.success is False
        assert result.error == "Target user not found"

    def test_grant_access_cannot_grant_to_owner(
        self,
        owner_user: User,
        content_item: ContentItem,
        collab_repo: MockCollabRepo,
        content_repo: MockContentRepo,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Cannot grant access to the content owner."""
        inp = GrantAccessInput(
            actor=owner_user,
            content_id=content_item.id,
            target_email="owner@example.com",
            scope="edit",
        )
        result = run_grant(
            inp, collab_repo, content_repo, user_repo, policy, time_port
        )

        assert result.success is False
        assert result.error is not None
        assert "already the owner" in result.error

    def test_grant_access_update_existing(
        self,
        owner_user: User,
        collaborator_user: User,
        content_item: ContentItem,
        collab_repo: MockCollabRepo,
        content_repo: MockContentRepo,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Granting again updates existing grant scope."""
        # First grant with view
        inp1 = GrantAccessInput(
            actor=owner_user,
            content_id=content_item.id,
            target_email="collaborator@example.com",
            scope="view",
        )
        result1 = run_grant(
            inp1, collab_repo, content_repo, user_repo, policy, time_port
        )
        assert result1.success is True
        assert result1.grant is not None
        assert result1.grant.scope == "view"

        # Second grant with edit - should update
        inp2 = GrantAccessInput(
            actor=owner_user,
            content_id=content_item.id,
            target_email="collaborator@example.com",
            scope="edit",
        )
        result2 = run_grant(
            inp2, collab_repo, content_repo, user_repo, policy, time_port
        )
        assert result2.success is True
        assert result2.grant is not None
        assert result2.grant.scope == "edit"


# --- Revoke Tests ---


class TestRevokeAccess:
    """Test run_revoke functionality."""

    def test_revoke_access_success(
        self,
        owner_user: User,
        collaborator_user: User,
        content_item: ContentItem,
        collab_repo: MockCollabRepo,
        content_repo: MockContentRepo,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Owner can revoke collaborator access."""
        # First grant access
        grant = CollaborationGrant(
            id=uuid4(),
            content_item_id=content_item.id,
            user_id=collaborator_user.id,
            scope="edit",
            created_at=time_port.now_utc(),
        )
        collab_repo.save(grant)

        # Then revoke
        inp = RevokeAccessInput(
            actor=owner_user,
            content_id=content_item.id,
            target_user_id=collaborator_user.id,
        )
        result = run_revoke(inp, collab_repo, content_repo, policy)

        assert result.success is True
        # Grant should be deleted
        remaining = collab_repo.get_by_content_and_user(
            content_item.id, collaborator_user.id
        )
        assert remaining is None

    def test_revoke_access_content_not_found(
        self,
        owner_user: User,
        collaborator_user: User,
        collab_repo: MockCollabRepo,
        content_repo: MockContentRepo,
        policy: PolicyEngine,
    ) -> None:
        """Revoke fails if content doesn't exist."""
        inp = RevokeAccessInput(
            actor=owner_user,
            content_id=uuid4(),
            target_user_id=collaborator_user.id,
        )
        result = run_revoke(inp, collab_repo, content_repo, policy)

        assert result.success is False
        assert result.error == "Content not found"


# --- List Tests ---


class TestListCollaborators:
    """Test run_list functionality."""

    def test_list_collaborators_success(
        self,
        owner_user: User,
        collaborator_user: User,
        content_item: ContentItem,
        collab_repo: MockCollabRepo,
        content_repo: MockContentRepo,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
        time_port: MockTimePort,
    ) -> None:
        """Owner can list collaborators."""
        # Add a grant
        grant = CollaborationGrant(
            id=uuid4(),
            content_item_id=content_item.id,
            user_id=collaborator_user.id,
            scope="edit",
            created_at=time_port.now_utc(),
        )
        collab_repo.save(grant)

        inp = ListCollaboratorsInput(actor=owner_user, content_id=content_item.id)
        result = run_list(inp, collab_repo, content_repo, user_repo, policy)

        assert result.success is True
        assert len(result.collaborators) == 1
        user, scope = result.collaborators[0]
        assert user.id == collaborator_user.id
        assert scope == "edit"

    def test_list_collaborators_empty(
        self,
        owner_user: User,
        content_item: ContentItem,
        collab_repo: MockCollabRepo,
        content_repo: MockContentRepo,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
    ) -> None:
        """Returns empty list when no collaborators."""
        inp = ListCollaboratorsInput(actor=owner_user, content_id=content_item.id)
        result = run_list(inp, collab_repo, content_repo, user_repo, policy)

        assert result.success is True
        assert len(result.collaborators) == 0

    def test_list_collaborators_content_not_found(
        self,
        owner_user: User,
        collab_repo: MockCollabRepo,
        content_repo: MockContentRepo,
        user_repo: MockUserRepo,
        policy: PolicyEngine,
    ) -> None:
        """List fails if content doesn't exist."""
        inp = ListCollaboratorsInput(actor=owner_user, content_id=uuid4())
        result = run_list(inp, collab_repo, content_repo, user_repo, policy)

        assert result.success is False
        assert result.error == "Content not found"
