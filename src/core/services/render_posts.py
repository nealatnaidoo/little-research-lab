"""
Post SSR Renderer Service (E4.4) - Render rich text to HTML.

Handles conversion of rich text JSON to safe, semantic HTML for SSR.

Spec refs: E4.4, TA-0025
Test assertions:
- TA-0025: Rich text renders to valid semantic HTML

Key behaviors:
- Converts ProseMirror-style JSON to HTML
- Applies sanitization during rendering
- Adds security attributes to links
- Generates semantic HTML structure
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from src.core.services.richtext import (
    RichTextConfig,
    build_link_rel,
    is_safe_url,
)

# --- Configuration ---


@dataclass(frozen=True)
class RenderConfig:
    """Rendering configuration."""

    # Rich text config for link handling
    rich_text_config: RichTextConfig | None = None

    # HTML rendering options
    wrap_in_article: bool = True
    add_heading_ids: bool = True
    code_block_class: str = "code-block"
    image_loading: str = "lazy"  # lazy, eager


DEFAULT_RENDER_CONFIG = RenderConfig()


# --- Node Renderers ---


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return html.escape(text)


def _slugify(text: str) -> str:
    """Create URL-safe slug from text."""
    import re

    # Lowercase, replace spaces with hyphens, remove non-alphanumeric
    slug = text.lower().strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def render_text(
    node: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render a text node with marks."""
    text = node.get("text", "")
    if not text:
        return ""

    # Escape the text content
    escaped = _escape(text)

    # Apply marks (in reverse order for proper nesting)
    marks = node.get("marks", [])
    for mark in reversed(marks):
        escaped = _apply_mark(escaped, mark, config)

    return escaped


def _apply_mark(
    content: str,
    mark: dict[str, Any],
    config: RenderConfig,
) -> str:
    """Apply a mark to content."""
    mark_type = mark.get("type", "")
    attrs = mark.get("attrs", {})

    rt_config = config.rich_text_config or RichTextConfig()

    if mark_type in ("bold", "strong"):
        return f"<strong>{content}</strong>"
    elif mark_type in ("italic", "em"):
        return f"<em>{content}</em>"
    elif mark_type == "code":
        return f"<code>{content}</code>"
    elif mark_type == "link":
        href = attrs.get("href", "")
        title = attrs.get("title", "")

        # Validate URL
        if not is_safe_url(href, rt_config):
            return content  # Strip unsafe link

        # Build attributes
        safe_href = _escape(href)
        rel = build_link_rel(rt_config)

        if title:
            safe_title = _escape(title)
            return f'<a href="{safe_href}" rel="{rel}" title="{safe_title}">{content}</a>'
        return f'<a href="{safe_href}" rel="{rel}">{content}</a>'

    # Unknown mark type - return content unchanged
    return content


def render_paragraph(
    node: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render a paragraph node."""
    content = render_content(node.get("content", []), config)
    return f"<p>{content}</p>"


def render_heading(
    node: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render a heading node."""
    attrs = node.get("attrs", {})
    level = attrs.get("level", 1)
    level = max(1, min(6, level))  # Clamp to 1-6

    content = render_content(node.get("content", []), config)

    if config.add_heading_ids:
        # Extract text for ID
        text = _extract_text(node)
        heading_id = _slugify(text)
        if heading_id:
            return f'<h{level} id="{heading_id}">{content}</h{level}>'

    return f"<h{level}>{content}</h{level}>"


def render_blockquote(
    node: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render a blockquote node."""
    content = render_content(node.get("content", []), config)
    return f"<blockquote>{content}</blockquote>"


def render_bullet_list(
    node: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render an unordered list."""
    items = render_content(node.get("content", []), config)
    return f"<ul>{items}</ul>"


def render_ordered_list(
    node: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render an ordered list."""
    attrs = node.get("attrs", {})
    start = attrs.get("start", 1)

    items = render_content(node.get("content", []), config)

    if start != 1:
        return f'<ol start="{start}">{items}</ol>'
    return f"<ol>{items}</ol>"


def render_list_item(
    node: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render a list item."""
    content = render_content(node.get("content", []), config)
    return f"<li>{content}</li>"


def render_code_block(
    node: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render a code block."""
    attrs = node.get("attrs", {})
    language = attrs.get("language", "")

    # Get text content directly
    text = _extract_text(node)
    escaped = _escape(text)

    if language:
        safe_lang = _escape(language)
        return (
            f'<pre class="{config.code_block_class}">'
            f'<code class="language-{safe_lang}">{escaped}</code>'
            f"</pre>"
        )
    return f'<pre class="{config.code_block_class}"><code>{escaped}</code></pre>'


def render_image(
    node: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render an image."""
    attrs = node.get("attrs", {})
    src = attrs.get("src", "")
    alt = attrs.get("alt", "")
    title = attrs.get("title", "")
    width = attrs.get("width")
    height = attrs.get("height")

    rt_config = config.rich_text_config or RichTextConfig()

    # Validate URL
    if not is_safe_url(src, rt_config):
        return ""  # Skip unsafe images

    parts = [f'src="{_escape(src)}"']
    parts.append(f'alt="{_escape(alt)}"')

    if title:
        parts.append(f'title="{_escape(title)}"')
    if width:
        parts.append(f'width="{_escape(str(width))}"')
    if height:
        parts.append(f'height="{_escape(str(height))}"')

    parts.append(f'loading="{config.image_loading}"')

    return f"<img {' '.join(parts)} />"


def render_hard_break(
    node: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render a hard break."""
    return "<br />"


def render_horizontal_rule(
    node: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render a horizontal rule."""
    return "<hr />"


# --- Node Type Dispatch ---

NODE_RENDERERS = {
    "paragraph": render_paragraph,
    "heading": render_heading,
    "blockquote": render_blockquote,
    "bulletList": render_bullet_list,
    "orderedList": render_ordered_list,
    "listItem": render_list_item,
    "codeBlock": render_code_block,
    "image": render_image,
    "hardBreak": render_hard_break,
    "horizontalRule": render_horizontal_rule,
}


def render_node(
    node: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render a single node."""
    node_type = node.get("type", "")

    # Text nodes are special
    if node_type == "text":
        return render_text(node, config)

    # Doc node just renders children
    if node_type == "doc":
        return render_content(node.get("content", []), config)

    # Look up renderer
    renderer = NODE_RENDERERS.get(node_type)
    if renderer:
        return renderer(node, config)

    # Unknown node - try to render content
    content = node.get("content", [])
    if content:
        return render_content(content, config)

    return ""


def render_content(
    nodes: list[dict[str, Any]],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """Render a list of nodes."""
    return "".join(render_node(node, config) for node in nodes)


def _extract_text(node: dict[str, Any]) -> str:
    """Extract plain text from a node tree."""
    if node.get("type") == "text":
        text: str = node.get("text", "")
        return text

    content = node.get("content", [])
    return "".join(_extract_text(child) for child in content)


# --- Main Rendering Functions ---


def render_rich_text(
    doc: dict[str, Any],
    config: RenderConfig = DEFAULT_RENDER_CONFIG,
) -> str:
    """
    Render rich text document to HTML (TA-0025).

    Args:
        doc: ProseMirror-style document
        config: Rendering configuration

    Returns:
        Rendered HTML string
    """
    content = render_node(doc, config)

    if config.wrap_in_article:
        return f"<article>{content}</article>"

    return content


def render_post_body(
    rich_text_json: dict[str, Any],
    config: RenderConfig | None = None,
) -> str:
    """
    Render a post body from rich text JSON.

    Convenience wrapper for render_rich_text.
    """
    cfg = config or DEFAULT_RENDER_CONFIG
    return render_rich_text(rich_text_json, cfg)


# --- Post Renderer Service ---


class PostRenderer:
    """
    Post renderer service (E4.4).

    Renders post content from rich text JSON to HTML.
    """

    def __init__(
        self,
        config: RenderConfig | None = None,
        rich_text_config: RichTextConfig | None = None,
    ) -> None:
        """Initialize renderer."""
        if config:
            self._config = config
        elif rich_text_config:
            self._config = RenderConfig(rich_text_config=rich_text_config)
        else:
            self._config = DEFAULT_RENDER_CONFIG

    def render(self, doc: dict[str, Any]) -> str:
        """Render document to HTML."""
        return render_rich_text(doc, self._config)

    def render_post(self, rich_text_json: dict[str, Any]) -> str:
        """Render a post body."""
        return render_post_body(rich_text_json, self._config)

    def extract_text(self, doc: dict[str, Any]) -> str:
        """Extract plain text from document."""
        return _extract_text(doc)

    def extract_headings(self, doc: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract headings for table of contents."""
        headings: list[dict[str, Any]] = []
        self._collect_headings(doc, headings)
        return headings

    def _collect_headings(
        self,
        node: dict[str, Any],
        headings: list[dict[str, Any]],
    ) -> None:
        """Recursively collect headings."""
        if node.get("type") == "heading":
            attrs = node.get("attrs", {})
            level = attrs.get("level", 1)
            text = _extract_text(node)
            slug = _slugify(text)
            headings.append(
                {
                    "level": level,
                    "text": text,
                    "id": slug,
                }
            )

        for child in node.get("content", []):
            self._collect_headings(child, headings)


# --- Factory ---


def create_post_renderer(
    config: RenderConfig | None = None,
    rich_text_config: RichTextConfig | None = None,
) -> PostRenderer:
    """Create a PostRenderer."""
    return PostRenderer(config=config, rich_text_config=rich_text_config)
