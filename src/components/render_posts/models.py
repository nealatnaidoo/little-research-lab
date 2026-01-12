"""
Render posts component input/output models.

Spec refs: E4.4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# --- Validation Error ---


@dataclass(frozen=True)
class RenderPostsValidationError:
    """Render posts validation error."""

    code: str
    message: str
    field: str | None = None


# --- Heading Model ---


@dataclass(frozen=True)
class Heading:
    """Extracted heading for TOC."""

    level: int
    text: str
    id: str


# --- Input Models ---


@dataclass(frozen=True)
class RenderPostInput:
    """Input for rendering post body to HTML."""

    rich_text_json: dict[str, Any]
    wrap_in_article: bool = True
    add_heading_ids: bool = True


@dataclass(frozen=True)
class ExtractTextInput:
    """Input for extracting plain text from post."""

    rich_text_json: dict[str, Any]


@dataclass(frozen=True)
class ExtractHeadingsInput:
    """Input for extracting headings for TOC."""

    rich_text_json: dict[str, Any]


# --- Output Models ---


@dataclass(frozen=True)
class RenderPostOutput:
    """Output containing rendered HTML."""

    html: str
    errors: list[RenderPostsValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class TextOutput:
    """Output containing extracted plain text."""

    text: str
    errors: list[RenderPostsValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class HeadingsOutput:
    """Output containing extracted headings."""

    headings: tuple[Heading, ...]
    errors: list[RenderPostsValidationError] = field(default_factory=list)
    success: bool = True
