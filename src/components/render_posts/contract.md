## COMPONENT_ID
C2-sub-render-posts

## PURPOSE
Render post content from rich text JSON to HTML with post-specific formatting.
Provides heading extraction, text extraction, and TOC generation.

## INPUTS
- `RenderPostInput`: Render post body to HTML
- `ExtractTextInput`: Extract plain text from post
- `ExtractHeadingsInput`: Extract headings for TOC

## OUTPUTS
- `RenderOutput`: Rendered HTML string
- `TextOutput`: Plain text content
- `HeadingsOutput`: List of headings with levels and text

## DEPENDENCIES (PORTS)
- `RichTextPort`: Rich text component for base rendering
- `RulesPort`: Render rules (configuration)

## SIDE EFFECTS
- None (pure transformation)

## INVARIANTS
- I1: Output is sanitized HTML
- I2: Headings preserve hierarchy
- I3: Text extraction strips all formatting
- I4: Configurable wrap in article tag

## ERROR SEMANTICS
- Returns empty string for invalid input
- Graceful handling of unknown node types

## TESTS
- `tests/unit/test_render_posts.py`: TA-0025 (tests)
  - Post rendering
  - Text extraction
  - Heading extraction

## EVIDENCE
- `artifacts/pytest-render-posts-report.json`
