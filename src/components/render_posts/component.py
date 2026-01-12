"""
Render posts component - Render rich text to HTML.

Spec refs: E4.4
Test assertions: TA-0025

Handles conversion of rich text JSON to safe, semantic HTML for SSR.

Invariants:
- I1: Output is sanitized HTML
- I2: Headings preserve hierarchy
- I3: Text extraction strips all formatting
- I4: Configurable wrap in article tag
"""

from __future__ import annotations

from src.components.richtext import RichTextConfig

from ._impl import (
    PostRenderer,
    RenderConfig,
)
from .models import (
    ExtractHeadingsInput,
    ExtractTextInput,
    Heading,
    HeadingsOutput,
    RenderPostInput,
    RenderPostOutput,
    TextOutput,
)
from .ports import RulesPort


def _build_config(
    rules: RulesPort | None,
    wrap_in_article: bool = True,
    add_heading_ids: bool = True,
) -> RenderConfig:
    """Build render config from rules port."""
    if rules is None:
        return RenderConfig(
            wrap_in_article=wrap_in_article,
            add_heading_ids=add_heading_ids,
        )

    link_rel = rules.get_link_rel_config()
    rich_text_config = RichTextConfig(
        add_noopener=link_rel.get("noopener", True),
        add_noreferrer=link_rel.get("noreferrer", True),
        add_ugc=link_rel.get("ugc", False),
    )

    return RenderConfig(
        rich_text_config=rich_text_config,
        wrap_in_article=wrap_in_article,
        add_heading_ids=add_heading_ids,
        code_block_class=rules.get_code_block_class(),
        image_loading=rules.get_image_loading(),
    )


# --- Component Entry Points ---


def run_render(
    inp: RenderPostInput,
    *,
    rules: RulesPort | None = None,
) -> RenderPostOutput:
    """
    Render post body to HTML (TA-0025).

    Args:
        inp: Input containing rich text JSON and render options.
        rules: Optional rules port for configuration.

    Returns:
        RenderPostOutput with rendered HTML.
    """
    config = _build_config(
        rules,
        wrap_in_article=inp.wrap_in_article,
        add_heading_ids=inp.add_heading_ids,
    )
    renderer = PostRenderer(config=config)

    html = renderer.render_post(inp.rich_text_json)

    return RenderPostOutput(
        html=html,
        errors=[],
        success=True,
    )


def run_extract_text(
    inp: ExtractTextInput,
    *,
    rules: RulesPort | None = None,
) -> TextOutput:
    """
    Extract plain text from post.

    Args:
        inp: Input containing rich text JSON.
        rules: Optional rules port for configuration.

    Returns:
        TextOutput with extracted plain text.
    """
    config = _build_config(rules)
    renderer = PostRenderer(config=config)

    text = renderer.extract_text(inp.rich_text_json)

    return TextOutput(
        text=text,
        errors=[],
        success=True,
    )


def run_extract_headings(
    inp: ExtractHeadingsInput,
    *,
    rules: RulesPort | None = None,
) -> HeadingsOutput:
    """
    Extract headings for table of contents.

    Args:
        inp: Input containing rich text JSON.
        rules: Optional rules port for configuration.

    Returns:
        HeadingsOutput with extracted headings.
    """
    config = _build_config(rules)
    renderer = PostRenderer(config=config)

    legacy_headings = renderer.extract_headings(inp.rich_text_json)
    headings = tuple(
        Heading(
            level=h["level"],
            text=h["text"],
            id=h["id"],
        )
        for h in legacy_headings
    )

    return HeadingsOutput(
        headings=headings,
        errors=[],
        success=True,
    )


def run(
    inp: RenderPostInput | ExtractTextInput | ExtractHeadingsInput,
    *,
    rules: RulesPort | None = None,
) -> RenderPostOutput | TextOutput | HeadingsOutput:
    """
    Main entry point for the render posts component.

    Dispatches to appropriate handler based on input type.

    Args:
        inp: Input object determining the operation.
        rules: Optional rules port for configuration.

    Returns:
        Appropriate output object based on input type.
    """
    if isinstance(inp, RenderPostInput):
        return run_render(inp, rules=rules)
    elif isinstance(inp, ExtractTextInput):
        return run_extract_text(inp, rules=rules)
    elif isinstance(inp, ExtractHeadingsInput):
        return run_extract_headings(inp, rules=rules)
    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
