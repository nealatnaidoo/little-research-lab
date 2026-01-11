
from unittest.mock import MagicMock, patch

import pytest

from src.services.bootstrap import bootstrap_system


@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.rules.ops.bootstrap_admin.enabled_if_no_users = True
    ctx.auth_service.user_repo.list_all.return_value = [] # Empty DB
    return ctx

@patch.dict('os.environ', {
    'LRL_BOOTSTRAP_EMAIL': 'newcap@example.com',
    'LRL_BOOTSTRAP_PASSWORD': 'secure'
})
def test_bootstrap_success(mock_ctx):
    """Should create user if DB is empty and env vars set."""
    mock_ctx.auth_service.auth_adapter.hash_password.return_value = "hashed"
    
    bootstrap_system(mock_ctx)
    
    # Verify save called
    mock_ctx.auth_service.user_repo.save.assert_called_once()
    user = mock_ctx.auth_service.user_repo.save.call_args[0][0]
    assert user.email == "newcap@example.com"
    assert "owner" in user.roles

@patch.dict('os.environ', {}, clear=True)
def test_bootstrap_no_env_vars(mock_ctx):
    """Should skip if credentials missing."""
    bootstrap_system(mock_ctx)
    mock_ctx.auth_service.user_repo.save.assert_not_called()

def test_bootstrap_already_populated(mock_ctx):
    """Should skip if users exist."""
    mock_ctx.auth_service.user_repo.list_all.return_value = ["User1"]
    
    with patch.dict('os.environ', {'LRL_BOOTSTRAP_EMAIL': 'x', 'LRL_BOOTSTRAP_PASSWORD': 'y'}):
        bootstrap_system(mock_ctx)
        
    mock_ctx.auth_service.user_repo.save.assert_not_called()

def test_bootstrap_disabled(mock_ctx):
    """Should skip if feature disabled in rules."""
    mock_ctx.rules.ops.bootstrap_admin.enabled_if_no_users = False
    
    with patch.dict('os.environ', {'LRL_BOOTSTRAP_EMAIL': 'x', 'LRL_BOOTSTRAP_PASSWORD': 'y'}):
        bootstrap_system(mock_ctx)
        
    mock_ctx.auth_service.user_repo.save.assert_not_called()
