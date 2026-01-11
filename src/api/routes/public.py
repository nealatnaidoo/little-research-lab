from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.adapters.sqlite.repos import SQLiteLinkRepo
from src.api.deps import get_content_service, get_link_repo
from src.api.schemas import ContentItemResponse
from src.services.content import ContentService

router = APIRouter()


@router.get("/home")
def get_public_home(
    content_service: ContentService = Depends(get_content_service),
    link_repo: SQLiteLinkRepo = Depends(get_link_repo),
) -> dict[str, Any]:
    """Get public home page data: latest posts and links."""
    posts = content_service.list_public_items()[:10]

    all_links = link_repo.get_all()
    links = [
        link for link in all_links
        if link.visibility == "public" and link.status == "active"
    ]

    return {"posts": posts, "links": links}


@router.get("/content/{slug}", response_model=ContentItemResponse)
def get_public_content(
    slug: str,
    content_service: ContentService = Depends(get_content_service),
) -> ContentItemResponse:
    """Get published content by slug."""
    # Try post first, then page
    item = content_service.get_by_slug(slug, "post")
    if not item:
        item = content_service.get_by_slug(slug, "page")

    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    return item  # type: ignore[return-value]
