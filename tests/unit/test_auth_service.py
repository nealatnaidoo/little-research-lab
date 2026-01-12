from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.components.auth.component import run_create_session, run_login, run_verify_session
from src.components.auth.models import CreateSessionInput, LoginInput, VerifySessionInput
from src.domain.entities import User


@pytest.fixture
def mock_repo():
    return Mock()


@pytest.fixture
def mock_auth_adapter():
    return Mock()


@pytest.fixture
def mock_session_store():
    """Mock session store that stores sessions in a dict."""
    store = Mock()
    store._sessions = {}
    store.get.side_effect = lambda token: store._sessions.get(token)
    store.save.side_effect = lambda token, session: store._sessions.__setitem__(token, session)
    store.delete.side_effect = lambda token: store._sessions.pop(token, None)
    return store


@pytest.fixture
def mock_time():
    """Mock time port that returns a fixed time."""
    time = Mock()
    time.now_utc.return_value = datetime(2026, 1, 12, 12, 0, 0, tzinfo=UTC)
    return time


def test_login_success(mock_repo, mock_auth_adapter):
    user = User(
        id=uuid4(),
        email="test@example.com",
        display_name="Test",
        password_hash="hash",
        status="active",
    )
    mock_repo.get_by_email.return_value = user
    mock_auth_adapter.verify_password.return_value = True

    inp = LoginInput(email="test@example.com", password="password")
    result = run_login(inp, mock_repo, mock_auth_adapter)

    assert result.success is True
    assert result.user == user
    mock_auth_adapter.verify_password.assert_called_with("password", "hash")


def test_login_failed_password(mock_repo, mock_auth_adapter):
    user = User(id=uuid4(), email="test@example.com", display_name="Test", password_hash="hash")
    mock_repo.get_by_email.return_value = user
    mock_auth_adapter.verify_password.return_value = False

    inp = LoginInput(email="test@example.com", password="wrong")
    result = run_login(inp, mock_repo, mock_auth_adapter)

    assert result.success is False
    assert result.user is None


def test_login_user_not_found(mock_repo, mock_auth_adapter):
    mock_repo.get_by_email.return_value = None

    inp = LoginInput(email="unknown", password="pwd")
    result = run_login(inp, mock_repo, mock_auth_adapter)

    assert result.success is False
    assert result.user is None


def test_create_session(mock_auth_adapter, mock_session_store, mock_time):
    user = User(id=uuid4(), email="test@example.com", display_name="Test", password_hash="hash")

    # Mock create_token to return token string
    mock_auth_adapter.create_token.return_value = "secret_token"

    inp = CreateSessionInput(user=user)
    result = run_create_session(inp, mock_auth_adapter, mock_session_store, mock_time)

    assert result.success is True
    assert result.session.user_id == user.id
    assert result.session.token_hash == "secret_token"
    mock_session_store.save.assert_called_once()


def test_validate_session_success(mock_auth_adapter, mock_repo, mock_session_store, mock_time):
    user = User(id=uuid4(), email="test@example.com", display_name="Test", password_hash="hash")
    mock_auth_adapter.create_token.return_value = "token"

    # Create the session first
    create_inp = CreateSessionInput(user=user)
    run_create_session(create_inp, mock_auth_adapter, mock_session_store, mock_time)

    mock_repo.get_by_id.return_value = user

    # Verify
    verify_inp = VerifySessionInput(token="token")
    result = run_verify_session(verify_inp, mock_repo, mock_session_store, mock_time)

    assert result.success is True
    assert result.user == user
