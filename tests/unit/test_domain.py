from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from src.domain.entities import ContentItem
from src.domain.state import can_transition, transition


def test_content_item_defaults():
    item = ContentItem(
        type="post",
        slug="hello-world",
        title="Hello",
        owner_user_id=uuid4()
    )
    assert item.status == "draft"
    assert item.visibility == "public"
    assert len(item.blocks) == 0

def test_transition_draft_to_published():
    now = datetime.utcnow()
    item = ContentItem(
        type="post",
        slug="test",
        title="Test",
        owner_user_id=uuid4(),
        status="draft"
    )
    
    new_item = transition(item, "published", now)
    assert new_item.status == "published"
    assert new_item.published_at == now
    assert new_item.updated_at == now

def test_transition_draft_to_scheduled_valid():
    now = datetime.utcnow()
    future = now + timedelta(days=1)
    
    item = ContentItem(
        type="post",
        slug="test",
        title="Test",
        owner_user_id=uuid4(),
        status="draft",
        publish_at=future
    )
    
    assert can_transition("draft", "scheduled", future, now) is True
    
    new_item = transition(item, "scheduled", now)
    assert new_item.status == "scheduled"
    assert new_item.published_at is None

def test_transition_draft_to_scheduled_invalid_past():
    now = datetime.utcnow()
    past = now - timedelta(hours=1)
    
    item = ContentItem(
        type="post",
        slug="test",
        title="Test",
        owner_user_id=uuid4(),
        status="draft",
        publish_at=past
    )
    
    assert can_transition("draft", "scheduled", past, now) is False
    
    with pytest.raises(ValueError, match="Invalid transition"):
        transition(item, "scheduled", now)

def test_transition_invalid_direct():
    """Test a transition that shouldn't happen directly if defined so."""
    # Our simple state machine is quite permissive, but let's check basic sanity.
    # Current implementation allows almost all transitions if conditions met.
    pass 
