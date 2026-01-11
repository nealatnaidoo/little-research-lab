from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_content_service, get_current_user
from src.api.schemas import (
    ContentBlockModel,
    ContentCreateRequest,
    ContentItemResponse,
    ContentUpdateRequest,
)
from src.domain.entities import ContentBlock, ContentItem, User
from src.services.content import ContentService

router = APIRouter()


@router.get("", response_model=list[ContentItemResponse])
def list_content(
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    service: ContentService = Depends(get_content_service),
) -> list[ContentItemResponse]:
    """List all content items for admin."""
    filters = {}
    if status:
        filters["status"] = status

    try:
        items = service.list_items(current_user, filters)
        return items  # type: ignore[return-value]
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied") from None


@router.get("/{item_id}", response_model=ContentItemResponse)
def get_content(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ContentService = Depends(get_content_service),
) -> ContentItemResponse:
    """Get a specific content item."""
    try:
        item = service.get_item(current_user, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Content not found")
        return item  # type: ignore[return-value]
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied") from None


def _blocks_from_request(blocks: list[ContentBlockModel]) -> list[ContentBlock]:
    """Convert request block models to domain entities."""
    return [
        ContentBlock(
            id=b.id or "",
            block_type=b.block_type,
            data_json=b.data_json,
        )
        for b in blocks
    ]


@router.post("", response_model=ContentItemResponse)
def create_content(
    req: ContentCreateRequest,
    current_user: User = Depends(get_current_user),
    service: ContentService = Depends(get_content_service),
) -> ContentItemResponse:
    """Create a new content item."""
    item = ContentItem(
        type=req.type,
        slug=req.slug,
        title=req.title,
        summary=req.summary or "",
        status=req.status,
        visibility=req.visibility,
        publish_at=req.publish_at,
        owner_user_id=current_user.id,
        blocks=_blocks_from_request(req.blocks),
    )

    try:
        created = service.create_item(current_user, item)
        return created  # type: ignore[return-value]
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not allowed to create content") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.put("/{item_id}", response_model=ContentItemResponse)
def update_content(
    item_id: UUID,
    req: ContentUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: ContentService = Depends(get_content_service),
) -> ContentItemResponse:
    """Update an existing content item."""
    existing = service.get_item(current_user, item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Content not found")

    # Update fields if provided
    if req.title is not None:
        existing.title = req.title
    if req.slug is not None:
        existing.slug = req.slug
    if req.summary is not None:
        existing.summary = req.summary
    if req.status is not None:
        existing.status = req.status
    if req.visibility is not None:
        existing.visibility = req.visibility
    if req.publish_at is not None:
        existing.publish_at = req.publish_at
    if req.blocks is not None:
        existing.blocks = _blocks_from_request(req.blocks)

    try:
        updated = service.update_item(current_user, existing)
        return updated  # type: ignore[return-value]
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not allowed to edit content") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.delete("/{item_id}", status_code=204)
def delete_content(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ContentService = Depends(get_content_service),
) -> None:
    """Delete a content item."""
    try:
        service.delete_item(current_user, item_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not allowed to delete content") from None
    except ValueError:
        raise HTTPException(status_code=404, detail="Content not found") from None
