from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.domain.entities import ContentItem, User
from src.services.content import ContentService


@pytest.fixture
def mock_repo():
    return Mock()

@pytest.fixture
def mock_policy():
    return Mock()

@pytest.fixture
def mock_validator():
    return Mock()

@pytest.fixture
def service(mock_repo, mock_policy, mock_validator):
    return ContentService(mock_repo, mock_policy, mock_validator)

def test_create_item_success(service, mock_policy, mock_validator, mock_repo):
    user = User(
        id=uuid4(), email="test@example.com", display_name="Test", 
        password_hash="hash", roles=["editor"]
    )
    item = ContentItem(
        id=uuid4(), type="post", slug="test-post", title="Test Post", 
        owner_user_id=user.id
    )
    
    mock_policy.check_permission.return_value = True
    mock_repo.save.return_value = item
    
    result = service.create_item(user, item)
    
    assert result == item
    mock_policy.check_permission.assert_called_with(
        user, user.roles, "content:create", resource=item
    )
    mock_repo.save.assert_called_with(item)

def test_create_item_denied(service, mock_policy):
    user = User(id=uuid4(), email="u", display_name="U", password_hash="h", roles=[])
    item = ContentItem(id=uuid4(), type="post", slug="s", title="T", owner_user_id=user.id)
    
    mock_policy.check_permission.return_value = False
    
    with pytest.raises(PermissionError):
        service.create_item(user, item)

def test_update_item_success(service, mock_policy, mock_repo):
    user = User(id=uuid4(), email="u", display_name="U", password_hash="h", roles=["editor"])
    item_id = uuid4()
    existing = ContentItem(
        id=item_id, type="post", slug="test", title="Old", 
        owner_user_id=user.id
    )
    updated = ContentItem(
        id=item_id, type="post", slug="test", title="New", 
        owner_user_id=user.id
    )

    mock_repo.get_by_id.return_value = existing
    mock_policy.check_permission.return_value = True
    
    service.update_item(user, updated)
    
    mock_policy.check_permission.assert_called_with(
        user, user.roles, "content:edit", resource=existing, context={}
    )
    mock_repo.save.assert_called_with(updated)

def test_delete_item_success(service, mock_policy, mock_repo):
    user = User(id=uuid4(), email="u", display_name="U", password_hash="h", roles=["admin"])
    item_id = uuid4()
    existing = ContentItem(id=item_id, type="post", slug="t", title="T", owner_user_id=uuid4())
    
    mock_repo.get_by_id.return_value = existing
    mock_policy.check_permission.return_value = True
    
    service.delete_item(user, item_id)
    
    mock_policy.check_permission.assert_called_with(
        user, user.roles, "content:delete", resource=existing, context={}
    )
    mock_repo.delete.assert_called_with(item_id)
