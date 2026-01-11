from datetime import datetime
from typing import Any

from src.domain.entities import ContentItem, ContentStatus


def can_transition(
    current: ContentStatus, 
    new: ContentStatus, 
    publish_at: datetime | None = None, 
    now: datetime | None = None
) -> bool:
    """
    Determine if a state transition is allowed based on the rules.
    """
    if current == new:
        return True
        
    if current == "draft":
        if new == "published":
            return True
        if new == "scheduled":
            # Must have a future publish_at date
            if not publish_at or not now:
                return False
            return publish_at > now
        if new == "archived":
             return True # Drafts can be archived (soft delete)

    if current == "scheduled":
        if new == "published":
            # Allowed when time is reached OR manual publish
            return True
        if new == "draft":
            return True # Un-schedule
        if new == "archived":
            return True

    if current == "published":
        if new == "archived":
            return True
        if new == "draft":
            return True # Un-publish

    if current == "archived":
        if new == "draft":
            return True # Restore
            
    return False

def transition(item: ContentItem, new_status: ContentStatus, now: datetime) -> ContentItem:
    """
    Return a NEW ContentItem with the updated status and timestamps.
    Raises ValueError if transition is invalid.
    """
    if item.status == new_status:
        return item.model_copy()

    if not can_transition(item.status, new_status, item.publish_at, now):
        raise ValueError(f"Invalid transition from {item.status} to {new_status}")

    updates: dict[str, Any] = {
        "status": new_status,
        "updated_at": now
    }

    if new_status == "published":
        # Ensure published_at is set.
        updates["published_at"] = now
    
    # If moving back to draft/scheduled, typically we might clear published_at 
    # or keep it as history.
    # Spec Invariants: "published implies published_at not null"
    # "scheduled implies publish_at not null"
    
    if new_status == "draft":
        updates["published_at"] = None # Reset
        
    if new_status == "scheduled":
        updates["published_at"] = None # Reset
        # publish_at must exist already for this to be valid
        if not item.publish_at:
             raise ValueError("Cannot transition to scheduled without publish_at date")

    return item.model_copy(update=updates)
