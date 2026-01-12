# Publish Component Contract

## Overview

The Publish component manages the content publishing lifecycle, including immediate publishing, scheduled publishing, unpublishing, and processing due scheduled items.

## Dependencies

### Required Ports

| Port | Purpose |
|------|---------|
| `ContentRepoPort` | Content item persistence (get, list, save) |
| `UserRepoPort` | User lookup for permission checks |
| `PolicyPort` | Permission verification via RBAC/ABAC |
| `ClockPort` | Current time for scheduling and transitions |

## Operations

### 1. Publish Now

**Input**: `PublishNowInput(user_id: UUID, item_id: UUID)`
**Output**: `PublishNowOutput(errors: list[PublishValidationError], success: bool)`

Immediately publishes a content item.

**Preconditions**:
- User must exist
- Content item must exist
- User must have `content:publish` permission on the item
- Content must be in a state that can transition to `published`

**Postconditions**:
- Item status is `published`
- Item `published_at` timestamp is set
- Item `updated_at` timestamp is updated

**Error Codes**:
- `USER_NOT_FOUND`: User does not exist
- `ITEM_NOT_FOUND`: Content item does not exist
- `PERMISSION_DENIED`: User lacks publish permission
- `TRANSITION_ERROR`: Invalid state transition

### 2. Schedule

**Input**: `ScheduleInput(user_id: UUID, item_id: UUID, at_datetime: datetime)`
**Output**: `ScheduleOutput(errors: list[PublishValidationError], success: bool)`

Schedules a content item for future publication.

**Preconditions**:
- User must exist
- Content item must exist
- User must have `content:publish` permission on the item
- `at_datetime` must be in the future
- Content must be in a state that can transition to `scheduled`

**Postconditions**:
- Item status is `scheduled`
- Item `publish_at` is set to the scheduled time
- Item `updated_at` timestamp is updated

**Error Codes**:
- `USER_NOT_FOUND`: User does not exist
- `ITEM_NOT_FOUND`: Content item does not exist
- `PERMISSION_DENIED`: User lacks publish permission
- `INVALID_SCHEDULE_TIME`: Schedule time is in the past
- `TRANSITION_ERROR`: Invalid state transition

### 3. Unpublish

**Input**: `UnpublishInput(user_id: UUID, item_id: UUID)`
**Output**: `UnpublishOutput(errors: list[PublishValidationError], success: bool)`

Unpublishes a content item (returns to draft status).

**Preconditions**:
- User must exist
- Content item must exist
- User must have `content:publish` permission on the item
- Content must be in a state that can transition to `draft`

**Postconditions**:
- Item status is `draft`
- Item `published_at` is cleared
- Item `updated_at` timestamp is updated

**Error Codes**:
- `USER_NOT_FOUND`: User does not exist
- `ITEM_NOT_FOUND`: Content item does not exist
- `PERMISSION_DENIED`: User lacks unpublish permission
- `TRANSITION_ERROR`: Invalid state transition

### 4. Process Due Items

**Input**: `ProcessDueInput()` (empty)
**Output**: `ProcessDueOutput(count: int, errors: list[PublishValidationError], success: bool)`

Processes all scheduled items that are due for publication.

**Preconditions**:
- None (system operation)

**Postconditions**:
- All scheduled items with `publish_at <= now` are published
- `count` reflects number of items successfully published
- Failed items are reported in `errors` but don't stop processing

**Error Codes**:
- `TRANSITION_ERROR`: One or more items failed to transition

## Usage Example

```python
from src.components.publish import (
    PublishComponent,
    PublishNowInput,
    ScheduleInput,
    UnpublishInput,
    ProcessDueInput,
)

# Initialize component with dependencies
component = PublishComponent(
    content_repo=content_repo,
    user_repo=user_repo,
    policy=policy_engine,
    clock=clock,
)

# Publish immediately
result = component.run(PublishNowInput(user_id=user_id, item_id=item_id))
if not result.success:
    for error in result.errors:
        print(f"{error.code}: {error.message}")

# Schedule for later
from datetime import datetime, timedelta
future_time = datetime.utcnow() + timedelta(days=1)
result = component.run(ScheduleInput(
    user_id=user_id,
    item_id=item_id,
    at_datetime=future_time,
))

# Unpublish
result = component.run(UnpublishInput(user_id=user_id, item_id=item_id))

# Process due items (typically called by scheduler)
result = component.run(ProcessDueInput())
print(f"Published {result.count} items")
```

## State Machine

The component relies on `src.domain.state.transition` for state machine validation:

```
draft -> published (publish_now)
draft -> scheduled (schedule, requires future publish_at)
scheduled -> published (process_due or publish_now)
scheduled -> draft (unpublish)
published -> draft (unpublish)
published -> archived (not exposed via this component)
```

## Invariants

1. A `scheduled` item always has a non-null `publish_at` timestamp
2. A `published` item always has a non-null `published_at` timestamp
3. Permission checks are always performed before state changes
4. State transitions are atomic (either succeed completely or fail with no changes)
