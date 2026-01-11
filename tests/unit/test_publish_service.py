from datetime import datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.domain.entities import ContentItem, User
from src.services.publish import PublishService


@pytest.fixture
def mock_repo():
    return Mock()

@pytest.fixture
def mock_policy():
    return Mock()

@pytest.fixture
def mock_clock():
    c = Mock()
    c.now.return_value = datetime(2025, 1, 1, 12, 0, 0)
    return c

@pytest.fixture
def service(mock_repo, mock_policy, mock_clock):
    return PublishService(mock_repo, mock_policy, mock_clock)

def test_publish_now_success(service, mock_repo, mock_policy, mock_clock):
    user = User(id=uuid4(), email="u", display_name="U", password_hash="h", roles=["editor"])
    item = ContentItem(
        id=uuid4(), type="post", slug="test", title="T", status="draft", owner_user_id=user.id
    )
    
    mock_repo.get_by_id.return_value = item
    mock_policy.check_permission.return_value = True
    
    service.publish_now(user, item.id)
    
    mock_policy.check_permission.assert_called_with(
        user, user.roles, "content:publish", resource=item
    )
    # Check save called with updated status logic
    # We can inspect the args passed to save
    args = mock_repo.save.call_args[0]
    saved_item = args[0]
    assert saved_item.status == "published"
    assert saved_item.published_at == mock_clock.now.return_value

def test_schedule_success(service, mock_repo, mock_policy, mock_clock):
    user = User(
        id=uuid4(), email="u", display_name="U", password_hash="h", roles=["editor"]
    )
    item = ContentItem(
        id=uuid4(), type="post", slug="test", title="T", status="draft", owner_user_id=user.id
    )
    
    mock_repo.get_by_id.return_value = item
    mock_policy.check_permission.return_value = True
    
    future = mock_clock.now.return_value + timedelta(days=1)
    service.schedule(user, item.id, future)
    
    args = mock_repo.save.call_args[0]
    saved_item = args[0]
    assert saved_item.status == "scheduled"
    assert saved_item.publish_at == future

def test_schedule_past_error(service, mock_repo, mock_policy, mock_clock):
    user = User(
        id=uuid4(), email="u", display_name="U", password_hash="h", roles=["editor"]
    )
    item = ContentItem(
        id=uuid4(), type="post", slug="test", title="T", status="draft", owner_user_id=user.id
    )
    
    mock_repo.get_by_id.return_value = item
    mock_policy.check_permission.return_value = True
    
    past = mock_clock.now.return_value - timedelta(minutes=1)
    with pytest.raises(ValueError, match="past"):
        service.schedule(user, item.id, past)

def test_process_due_items(service, mock_repo, mock_clock):
    now = mock_clock.now.return_value
    
    # 1. Due item
    due = ContentItem(
        id=uuid4(), type="post", slug="due", title="Due", status="scheduled", 
        owner_user_id=uuid4(), publish_at=now - timedelta(minutes=10)
    )
    # 2. Not due item
    future = ContentItem(
        id=uuid4(), type="post", slug="fut", title="Fut", status="scheduled", 
        owner_user_id=uuid4(), publish_at=now + timedelta(minutes=10)
    )
    # 3. Draft (shouldn't be in list if filtered correctly, but let's test defensive logic)
    draft = ContentItem(
        id=uuid4(), type="post", slug="d", title="D", status="draft", 
        owner_user_id=uuid4()
    )
    
    # Mock list_items to return these
    mock_repo.list_items.return_value = [due, future, draft]
    
    count = service.process_due_items()
    
    assert count == 1
    # Only 'due' should be saved as published
    mock_repo.save.assert_called_once()
    saved = mock_repo.save.call_args[0][0]
    assert saved.id == due.id
    assert saved.status == "published"
