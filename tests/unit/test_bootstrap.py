from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.components.bootstrap.component import run
from src.components.bootstrap.models import BootstrapInput


class FakeTime:
    def now_utc(self):
        return datetime(2026, 1, 12, 12, 0, 0, tzinfo=UTC)


class FakeRules:
    def __init__(self, enabled: bool = True):
        self._enabled = enabled

    def get_bootstrap_config(self):
        mock_config = MagicMock()
        mock_config.enabled_if_no_users = self._enabled
        return mock_config


@pytest.fixture
def mock_user_repo():
    repo = MagicMock()
    repo.list_all.return_value = []  # Empty DB
    return repo


@pytest.fixture
def mock_auth_adapter():
    adapter = MagicMock()
    adapter.hash_password.return_value = "hashed_password"
    return adapter


def test_bootstrap_success(mock_user_repo, mock_auth_adapter):
    """Should create user if DB is empty and credentials provided."""
    inp = BootstrapInput(
        bootstrap_email="newcap@example.com",
        bootstrap_password="secure",
    )

    result = run(
        inp,
        user_repo=mock_user_repo,
        auth_adapter=mock_auth_adapter,
        rules=FakeRules(enabled=True),
        time=FakeTime(),
    )

    assert result.success is True
    assert result.created is True
    assert result.user is not None
    assert result.user.email == "newcap@example.com"
    assert "owner" in result.user.roles

    # Verify save called
    mock_user_repo.save.assert_called_once()


def test_bootstrap_no_credentials():
    """Should skip if credentials missing."""
    mock_repo = MagicMock()
    mock_repo.list_all.return_value = []

    inp = BootstrapInput(
        bootstrap_email=None,
        bootstrap_password=None,
    )

    result = run(
        inp,
        user_repo=mock_repo,
        auth_adapter=MagicMock(),
        rules=FakeRules(enabled=True),
        time=FakeTime(),
    )

    assert result.success is True
    assert result.created is False
    assert result.skipped_reason is not None
    mock_repo.save.assert_not_called()


def test_bootstrap_already_populated(mock_auth_adapter):
    """Should skip if users exist."""
    mock_repo = MagicMock()
    mock_repo.list_all.return_value = [MagicMock()]  # Has users

    inp = BootstrapInput(
        bootstrap_email="newcap@example.com",
        bootstrap_password="secure",
    )

    result = run(
        inp,
        user_repo=mock_repo,
        auth_adapter=mock_auth_adapter,
        rules=FakeRules(enabled=True),
        time=FakeTime(),
    )

    assert result.success is True
    assert result.created is False
    assert "already exist" in result.skipped_reason
    mock_repo.save.assert_not_called()


def test_bootstrap_disabled(mock_user_repo, mock_auth_adapter):
    """Should skip if feature disabled in rules."""
    inp = BootstrapInput(
        bootstrap_email="newcap@example.com",
        bootstrap_password="secure",
    )

    result = run(
        inp,
        user_repo=mock_user_repo,
        auth_adapter=mock_auth_adapter,
        rules=FakeRules(enabled=False),
        time=FakeTime(),
    )

    assert result.success is True
    assert result.created is False
    assert "not enabled" in result.skipped_reason
    mock_user_repo.save.assert_not_called()
