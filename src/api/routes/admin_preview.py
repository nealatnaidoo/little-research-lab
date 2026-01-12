"""
Admin Preview API Routes (E4.4).

Provides preview endpoints for content before publishing.

Spec refs: E4.4, TA-0025
Test assertions:
- TA-0025: Preview renders same as public (content parity)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.components.render_posts import (
    PostRenderer,
    RenderConfig,
    render_rich_text,
)
from src.components.richtext import RichTextConfig

router = APIRouter()


# --- Request/Response Models ---


class PreviewRequest(BaseModel):
    """Request to preview rich text content."""

    rich_text_json: dict[str, Any] = Field(..., description="Rich text document")
    wrap_in_article: bool = Field(default=True, description="Wrap in <article> tag")
    add_heading_ids: bool = Field(default=True, description="Add IDs to headings")


class PreviewResponse(BaseModel):
    """Preview response with rendered HTML."""

    html: str
    plain_text: str
    headings: list[dict[str, Any]]
    word_count: int
    link_count: int


class ContentPreviewRequest(BaseModel):
    """Request to preview content by ID."""

    content_id: UUID


class ContentPreviewResponse(BaseModel):
    """Full content preview response."""

    content_id: UUID
    title: str
    slug: str
    html: str
    plain_text: str
    headings: list[dict[str, Any]]
    word_count: int


# --- Dependencies ---


def get_post_renderer() -> PostRenderer:
    """Get post renderer dependency."""
    config = RenderConfig(
        rich_text_config=RichTextConfig(),
        wrap_in_article=True,
        add_heading_ids=True,
    )
    return PostRenderer(config=config)


# --- Helper Functions ---


def count_words(text: str) -> int:
    """Count words in plain text."""
    if not text:
        return 0
    return len(text.split())


def count_links(doc: dict[str, Any]) -> int:
    """Count links in document."""
    count = 0

    def traverse(node: dict[str, Any]) -> None:
        nonlocal count
        for mark in node.get("marks", []):
            if mark.get("type") == "link":
                count += 1
        for child in node.get("content", []):
            traverse(child)

    traverse(doc)
    return count


# --- Routes ---


@router.post("/preview", response_model=PreviewResponse)
def preview_rich_text(
    request: PreviewRequest,
    renderer: PostRenderer = Depends(get_post_renderer),
) -> PreviewResponse:
    """
    Preview rich text content (TA-0025).

    Renders the same way as public pages for content parity.
    """
    # Build config from request
    config = RenderConfig(
        rich_text_config=RichTextConfig(),
        wrap_in_article=request.wrap_in_article,
        add_heading_ids=request.add_heading_ids,
    )

    # Render HTML
    html = render_rich_text(request.rich_text_json, config)

    # Extract metadata
    plain_text = renderer.extract_text(request.rich_text_json)
    headings = renderer.extract_headings(request.rich_text_json)
    word_count = count_words(plain_text)
    link_count = count_links(request.rich_text_json)

    return PreviewResponse(
        html=html,
        plain_text=plain_text,
        headings=headings,
        word_count=word_count,
        link_count=link_count,
    )


@router.post("/preview/validate")
def validate_rich_text(
    request: PreviewRequest,
) -> dict[str, Any]:
    """
    Validate rich text content without rendering.

    Returns validation errors if any.
    """
    from src.components.richtext import RichTextService

    service = RichTextService()
    errors = service.validate(request.rich_text_json)

    return {
        "valid": len(errors) == 0,
        "errors": [{"code": e.code, "message": e.message, "path": e.path} for e in errors],
    }


@router.post("/preview/sanitize")
def sanitize_rich_text(
    request: PreviewRequest,
    renderer: PostRenderer = Depends(get_post_renderer),
) -> dict[str, Any]:
    """
    Sanitize rich text and return cleaned version.

    Strips disallowed content and returns the sanitized document.
    """
    from src.components.richtext import RichTextService

    service = RichTextService()
    sanitized, errors = service.sanitize(request.rich_text_json)

    # Render sanitized version
    config = RenderConfig(
        rich_text_config=RichTextConfig(),
        wrap_in_article=request.wrap_in_article,
        add_heading_ids=request.add_heading_ids,
    )
    html = render_rich_text(sanitized, config)

    return {
        "sanitized": sanitized,
        "html": html,
        "changes": [{"code": e.code, "message": e.message, "path": e.path} for e in errors],
    }


@router.post("/preview/headings")
def extract_headings(
    request: PreviewRequest,
    renderer: PostRenderer = Depends(get_post_renderer),
) -> dict[str, Any]:
    """
    Extract headings for table of contents.
    """
    headings = renderer.extract_headings(request.rich_text_json)
    return {"headings": headings}


@router.post("/preview/stats")
def get_content_stats(
    request: PreviewRequest,
    renderer: PostRenderer = Depends(get_post_renderer),
) -> dict[str, Any]:
    """
    Get content statistics.
    """
    plain_text = renderer.extract_text(request.rich_text_json)
    word_count = count_words(plain_text)
    char_count = len(plain_text)
    link_count = count_links(request.rich_text_json)
    headings = renderer.extract_headings(request.rich_text_json)

    return {
        "word_count": word_count,
        "char_count": char_count,
        "link_count": link_count,
        "heading_count": len(headings),
        "reading_time_minutes": max(1, word_count // 200),
    }
