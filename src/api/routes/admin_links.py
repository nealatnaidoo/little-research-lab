"""Admin routes for managing links."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import get_current_user, get_link_service
from src.components.links import (
    CreateLinkInput,
    DeleteLinkInput,
    GetLinkInput,
    LinkService,
    UpdateLinkInput,
    run_create,
    run_delete,
    run_get,
    run_list,
    run_update,
)
from src.domain.entities import ContentVisibility, LinkStatus, User

router = APIRouter()


# --- Request/Response Models ---


class LinkCreateRequest(BaseModel):
    slug: str
    title: str
    url: str
    icon: str | None = None
    status: LinkStatus = "active"
    position: int = 0
    visibility: ContentVisibility = "public"
    group_id: str | None = None


class LinkUpdateRequest(BaseModel):
    slug: str | None = None
    title: str | None = None
    url: str | None = None
    icon: str | None = None
    status: LinkStatus | None = None
    position: int | None = None
    visibility: ContentVisibility | None = None
    group_id: str | None = None


class LinkResponse(BaseModel):
    id: str
    slug: str
    title: str
    url: str
    icon: str | None
    status: LinkStatus
    position: int
    visibility: ContentVisibility
    group_id: str | None


class LinkListResponse(BaseModel):
    items: list[LinkResponse]
    total: int


# --- Routes ---


@router.get("/links", response_model=LinkListResponse)
def list_links(
    current_user: User = Depends(get_current_user),
    service: LinkService = Depends(get_link_service),
) -> LinkListResponse:
    """List all links."""
    result = run_list(service)
    return LinkListResponse(
        items=[
            LinkResponse(
                id=str(link.id),
                slug=link.slug,
                title=link.title,
                url=link.url,
                icon=link.icon,
                status=link.status,
                position=link.position,
                visibility=link.visibility,
                group_id=str(link.group_id) if link.group_id else None,
            )
            for link in result.links
        ],
        total=result.total,
    )


@router.post("/links", response_model=LinkResponse, status_code=201)
def create_link(
    data: LinkCreateRequest,
    current_user: User = Depends(get_current_user),
    service: LinkService = Depends(get_link_service),
) -> LinkResponse:
    """Create a new link."""
    input_data = CreateLinkInput(
        title=data.title,
        slug=data.slug,
        url=data.url,
        icon=data.icon,
        status=data.status,
        position=data.position,
        visibility=data.visibility,
        group_id=UUID(data.group_id) if data.group_id else None,
    )

    result = run_create(input_data, service)

    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=[
                {"code": err.code, "message": err.message, "field": err.field}
                for err in result.errors
            ],
        )

    link = result.link
    assert link is not None  # Success guarantees link is not None
    return LinkResponse(
        id=str(link.id),
        slug=link.slug,
        title=link.title,
        url=link.url,
        icon=link.icon,
        status=link.status,
        position=link.position,
        visibility=link.visibility,
        group_id=str(link.group_id) if link.group_id else None,
    )


@router.get("/links/{link_id}", response_model=LinkResponse)
def get_link(
    link_id: str,
    current_user: User = Depends(get_current_user),
    service: LinkService = Depends(get_link_service),
) -> LinkResponse:
    """Get a link by ID."""
    input_data = GetLinkInput(link_id=UUID(link_id))
    result = run_get(input_data, service)

    if not result.success:
        raise HTTPException(status_code=404, detail="Link not found")

    link = result.link
    assert link is not None
    return LinkResponse(
        id=str(link.id),
        slug=link.slug,
        title=link.title,
        url=link.url,
        icon=link.icon,
        status=link.status,
        position=link.position,
        visibility=link.visibility,
        group_id=str(link.group_id) if link.group_id else None,
    )


@router.put("/links/{link_id}", response_model=LinkResponse)
def update_link(
    link_id: str,
    data: LinkUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: LinkService = Depends(get_link_service),
) -> LinkResponse:
    """Update a link."""
    input_data = UpdateLinkInput(
        link_id=UUID(link_id),
        title=data.title,
        slug=data.slug,
        url=data.url,
        icon=data.icon,
        status=data.status,
        position=data.position,
        visibility=data.visibility,
        group_id=UUID(data.group_id) if data.group_id else None,
    )

    result = run_update(input_data, service)

    if not result.success:
        # Check if it's a not found error
        if result.errors and result.errors[0].code == "link_not_found":
            raise HTTPException(status_code=404, detail="Link not found")
        raise HTTPException(
            status_code=400,
            detail=[
                {"code": err.code, "message": err.message, "field": err.field}
                for err in result.errors
            ],
        )

    link = result.link
    assert link is not None
    return LinkResponse(
        id=str(link.id),
        slug=link.slug,
        title=link.title,
        url=link.url,
        icon=link.icon,
        status=link.status,
        position=link.position,
        visibility=link.visibility,
        group_id=str(link.group_id) if link.group_id else None,
    )


@router.delete("/links/{link_id}", status_code=204)
def delete_link(
    link_id: str,
    current_user: User = Depends(get_current_user),
    service: LinkService = Depends(get_link_service),
) -> None:
    """Delete a link."""
    input_data = DeleteLinkInput(link_id=UUID(link_id))
    result = run_delete(input_data, service)

    if not result.success:
        raise HTTPException(status_code=404, detail="Link not found")
