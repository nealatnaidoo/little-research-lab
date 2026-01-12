from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.adapters.clock import SystemClock
from src.api.deps import get_content_repo, get_current_user, get_policy
from src.api.schemas import (
    ContentBlockModel,
    ContentCreateRequest,
    ContentItemResponse,
    ContentTransitionRequest,
    ContentUpdateRequest,
)
from src.components.content.component import (
    run_create,
    run_delete,
    run_get,
    run_list,
    run_transition,
    run_update,
)
from src.components.content.models import (
    CreateContentInput,
    DeleteContentInput,
    GetContentInput,
    ListContentInput,
    TransitionContentInput,
    UpdateContentInput,
)
from src.domain.entities import ContentBlock, User

# We need a TimePort implementation. SystemClock fits?
# SystemClock usually implements now(), but component needs TimePort (now_utc, etc).
# I'll check SystemClock in src/adapters/clock.py.
# If it doesn't match, I might need an adapter locally.


def get_time_port() -> Any:
    return SystemClock()


router = APIRouter()


@router.get("", response_model=list[ContentItemResponse])
def list_content(
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    repo: Any = Depends(get_content_repo),
    policy: Any = Depends(get_policy),
) -> list[ContentItemResponse]:
    """List all content items for admin."""
    # Policy check
    if not policy.check_permission(current_user, current_user.roles, "content:list"):
        raise HTTPException(status_code=403, detail="Access denied")

    inp = ListContentInput(status=status)  # type: ignore
    # Note: Component ListContentInput defines status as ContentStatus (Literal).
    # str input might need casting or validation.

    result = run_list(inp, repo=repo)
    if not result.success:
        raise HTTPException(status_code=400, detail="Failed to list content")

    return result.items  # type: ignore


@router.get("/{item_id}", response_model=ContentItemResponse)
def get_content(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    repo: Any = Depends(get_content_repo),
    policy: Any = Depends(get_policy),
) -> ContentItemResponse:
    """Get a specific content item."""
    inp = GetContentInput(content_id=item_id)
    result = run_get(inp, repo=repo)

    if not result.success or not result.content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Policy Check
    has_perm = policy.check_permission(
        current_user, current_user.roles, "content:read", resource=result.content
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="Access denied")

    return result.content  # type: ignore[return-value]


def _blocks_from_request(blocks: list[ContentBlockModel]) -> list[dict[str, Any]]:
    """Convert request block models to dict for component input."""
    # CreateContentInput expects blocks as list[dict] (JSON-like) usually,
    # or component expects Check models.py.
    # src/components/content/models.py: CreateContentInput blocks: list[dict[str, Any]]
    return [{"type": b.block_type, "data": b.data_json} for b in blocks]


@router.post("", response_model=ContentItemResponse)
def create_content(
    req: ContentCreateRequest,
    current_user: User = Depends(get_current_user),
    repo: Any = Depends(get_content_repo),
    policy: Any = Depends(get_policy),
    time: Any = Depends(get_time_port),
) -> ContentItemResponse:
    """Create a new content item."""
    # Policy Check (global)
    if not policy.check_permission(current_user, current_user.roles, "content:create"):
        raise HTTPException(status_code=403, detail="Not allowed to create content")

    inp = CreateContentInput(
        owner_user_id=current_user.id,
        type=req.type,
        title=req.title,
        slug=req.slug,
        summary=req.summary or "",
        blocks=_blocks_from_request(req.blocks),
    )

    result = run_create(inp, repo=repo, time=time)

    if not result.success:
        err = result.errors[0]
        # Map specific validation errors if needed
        raise HTTPException(status_code=400, detail=err.message)

    return result.content  # type: ignore[return-value]


@router.put("/{item_id}", response_model=ContentItemResponse)
def update_content(
    item_id: UUID,
    req: ContentUpdateRequest,
    current_user: User = Depends(get_current_user),
    repo: Any = Depends(get_content_repo),
    policy: Any = Depends(get_policy),
    time: Any = Depends(get_time_port),
) -> ContentItemResponse:
    """Update an existing content item."""
    # Need to fetch first to check permission on resource
    get_res = run_get(GetContentInput(content_id=item_id), repo=repo)
    if not get_res.success or not get_res.content:
        raise HTTPException(status_code=404, detail="Content not found")

    existing = get_res.content

    has_perm = policy.check_permission(
        current_user, current_user.roles, "content:edit", resource=existing
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="Not allowed to edit content")

    updates = req.model_dump(exclude_unset=True)
    # Convert blocks if present
    if "blocks" in updates:
        # component expects blocks? UpdateContentInput: updates: dict[str, Any]
        # But `run_update` logic applies setattr.
        # `ContentItem.blocks` is list[ContentBlock].
        # If I pass dicts, setattr might fail if it expects objects, OR I need to convert.
        # Looking at `run_update` in component:
        # `    for key, value in updates.items():`
        # `        if hasattr(content, key):`
        # `            setattr(content, key, value)`
        # It blindly sets attributes.
        # Must provide list[ContentBlock] since ContentItem uses that type.
        # Convert inputs to ContentBlock.

        updates["blocks"] = [
            ContentBlock(block_type=b.block_type, data_json=b.data_json) for b in req.blocks or []
        ]

    inp = UpdateContentInput(content_id=item_id, updates=updates)
    result = run_update(inp, repo=repo, time=time)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.errors[0].message)

    return result.content  # type: ignore[return-value]


@router.post("/{item_id}/transition", response_model=ContentItemResponse)
def transition_content(
    item_id: UUID,
    req: ContentTransitionRequest,
    current_user: User = Depends(get_current_user),
    repo: Any = Depends(get_content_repo),
    policy: Any = Depends(get_policy),
    time: Any = Depends(get_time_port),
) -> ContentItemResponse:
    """Transition content status."""
    # Get content for permission check
    get_res = run_get(GetContentInput(content_id=item_id), repo=repo)
    if not get_res.success or not get_res.content:
        raise HTTPException(status_code=404, detail="Content not found")

    has_perm = policy.check_permission(
        current_user, current_user.roles, "content:edit", resource=get_res.content
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="Not allowed to edit content")

    # Convert input
    inp = TransitionContentInput(
        content_id=item_id, to_status=req.status, publish_at=req.publish_at
    )

    # Using defaults for rules/asset_resolver for now as not fully implemented in adapters
    result = run_transition(inp, repo=repo, time=time)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.errors[0].message)

    return result.content  # type: ignore


@router.delete("/{item_id}", status_code=204)
def delete_content(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    repo: Any = Depends(get_content_repo),
    policy: Any = Depends(get_policy),
) -> None:
    """Delete a content item."""
    # Get first for permission
    get_res = run_get(GetContentInput(content_id=item_id), repo=repo)
    if not get_res.success or not get_res.content:
        raise HTTPException(status_code=404, detail="Content not found")

    has_perm = policy.check_permission(
        current_user, current_user.roles, "content:delete", resource=get_res.content
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="Not allowed to delete content")

    inp = DeleteContentInput(content_id=item_id)
    result = run_delete(inp, repo=repo)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.errors[0].message)
