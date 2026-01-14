"""
Render posts component - Render rich text to HTML.

Spec refs: E4.4
"""

# Re-exports from _impl for backwards compatibility
# Re-exports from legacy render_posts service (pending full migration)
from src.core.services.render_posts import (
    render_blockquote,
    render_bullet_list,
    render_code_block,
    render_content,
    render_hard_break,
    render_heading,
    render_horizontal_rule,
    render_image,
    render_list_item,
    render_node,
    render_ordered_list,
    render_paragraph,
    render_text,
)

from ._impl import (
    DEFAULT_RENDER_CONFIG,
    PostRenderer,
    RenderConfig,
    create_post_renderer,
    render_post_body,
    render_rich_text,
)
from .component import (
    run,
    run_extract_headings,
    run_extract_text,
    run_render,
)
from .models import (
    ExtractHeadingsInput,
    ExtractTextInput,
    Heading,
    HeadingsOutput,
    RenderPostInput,
    RenderPostOutput,
    RenderPostsValidationError,
    TextOutput,
)
from .ports import RichTextPort, RulesPort

__all__ = [
    # Entry points
    "run",
    "run_extract_headings",
    "run_extract_text",
    "run_render",
    # Input models
    "ExtractHeadingsInput",
    "ExtractTextInput",
    "RenderPostInput",
    # Output models
    "Heading",
    "HeadingsOutput",
    "RenderPostOutput",
    "RenderPostsValidationError",
    "TextOutput",
    # Ports
    "RichTextPort",
    "RulesPort",
    # Legacy _impl re-exports
    "DEFAULT_RENDER_CONFIG",
    "PostRenderer",
    "RenderConfig",
    "create_post_renderer",
    "render_post_body",
    "render_rich_text",
    # Legacy service re-exports
    "render_blockquote",
    "render_bullet_list",
    "render_code_block",
    "render_content",
    "render_hard_break",
    "render_heading",
    "render_horizontal_rule",
    "render_image",
    "render_list_item",
    "render_node",
    "render_ordered_list",
    "render_paragraph",
    "render_text",
]
