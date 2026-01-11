from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.domain.entities import User
from src.services.auth import AuthService


@pytest.fixture
def mock_repo():
    return Mock()

@pytest.fixture
def mock_auth_adapter():
    return Mock()

@pytest.fixture
def mock_policy():
    return Mock()

@pytest.fixture
def service(mock_repo, mock_auth_adapter, mock_policy):
    return AuthService(mock_repo, mock_auth_adapter, mock_policy)

def test_login_success(service, mock_repo, mock_auth_adapter):
    user = User(
        id=uuid4(), email="test@example.com", display_name="Test", 
        password_hash="hash", status="active"
    )
    mock_repo.get_by_email.return_value = user
    mock_auth_adapter.verify_password.return_value = True
    
    result = service.login("test@example.com", "password")
    
    assert result == user
    mock_auth_adapter.verify_password.assert_called_with("password", "hash")

def test_login_failed_password(service, mock_repo, mock_auth_adapter):
    user = User(
        id=uuid4(), email="test@example.com", display_name="Test", 
        password_hash="hash"
    )
    mock_repo.get_by_email.return_value = user
    mock_auth_adapter.verify_password.return_value = False
    
    assert service.login("test@example.com", "wrong") is None

def test_login_user_not_found(service, mock_repo):
    mock_repo.get_by_email.return_value = None
    assert service.login("unknown", "pwd") is None

def test_create_session(service, mock_auth_adapter):
    user = User(
        id=uuid4(), email="test@example.com", display_name="Test", 
        password_hash="hash"
    )
    
    # Mock create_token to return token string
    mock_auth_adapter.create_token.return_value = "secret_token"
    
    session = service.create_session(user)
    
    assert session.user_id == user.id
    assert session.token_hash == "secret_token"
    
def test_validate_session_success(service, mock_auth_adapter, mock_repo):
    user = User(
        id=uuid4(), email="test@example.com", display_name="Test", 
        password_hash="hash"
    )
    mock_auth_adapter.create_token.return_value = "token"
    service.create_session(user)
    
    mock_repo.get_by_id.return_value = user
    
    # get_user_by_token uses in-memory sessions
    result = service.get_user_by_token("token")
    assert result == user 
