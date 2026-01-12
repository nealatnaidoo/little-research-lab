from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.adapters.sqlite.repos import SQLiteLinkRepo
from src.api.deps import get_content_repo, get_link_repo
from src.api.schemas import ContentItemResponse
from src.components.content.component import run_get, run_list
from src.components.content.models import GetContentInput, ListContentInput

router = APIRouter()


@router.get("/home")
def get_public_home(
    content_repo: Any = Depends(get_content_repo),
    link_repo: SQLiteLinkRepo = Depends(get_link_repo),
) -> dict[str, Any]:
    """Get public home page data: latest posts and links."""
    # List published posts
    # Legacy logic: list_public_items() returning 10.
    # We should assume default sorting (likely by created_at desc) in repo?
    # SQLiteContentRepo uses `ORDER BY created_at DESC` usually.

    inp = ListContentInput(status="published", limit=10)
    res = run_list(inp, repo=content_repo)
    posts = res.items if res.success else []

    all_links = link_repo.get_all()
    links = [link for link in all_links if link.visibility == "public" and link.status == "active"]

    return {"posts": posts, "links": links}


@router.get("/content/{slug}", response_model=ContentItemResponse)
def get_public_content(
    slug: str,
    content_repo: Any = Depends(get_content_repo),
) -> ContentItemResponse:
    """Get published content by slug."""
    # Try post first, then page
    res = run_get(GetContentInput(slug=slug, content_type="post"), repo=content_repo)
    if not res.success or not res.content:
        res = run_get(GetContentInput(slug=slug, content_type="page"), repo=content_repo)

    if not res.success or not res.content:
        raise HTTPException(status_code=404, detail="Content not found")

    item = res.content

    # Ensure content is published for public access
    # Atomic `run_get` retrieves any status, so we must enforce the check here
    if item.status != "published":
        raise HTTPException(status_code=404, detail="Content not found")

    return item  # type: ignore[return-value]
