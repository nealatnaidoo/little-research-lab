## COMPONENT_ID
C2-render

## PURPOSE
Render content from rich text JSON to HTML for display.
Provides configurable rendering with security sanitization.

## INPUTS
- `RenderContentInput`: Content to render (rich text JSON)
- `RenderPostInput`: Post body to render
- `ExtractTextInput`: Extract plain text from rich text
- `ExtractHeadingsInput`: Extract headings for TOC

## OUTPUTS
- `RenderOutput`: Rendered HTML string
- `TextOutput`: Plain text extraction
- `HeadingsOutput`: List of headings with levels

## DEPENDENCIES (PORTS)
- `SettingsPort`: Site settings for render configuration
- `RulesPort`: Render rules (sanitization, allowed tags)

## SIDE EFFECTS
- None (pure transformation)

## INVARIANTS
- I1: Output is sanitized HTML (no XSS)
- I2: Only allowed tags in output
- I3: URLs are validated
- I4: Heading extraction preserves hierarchy

## ERROR SEMANTICS
- Returns empty string for invalid input
- Graceful degradation for unsupported node types

## TESTS
- `tests/unit/test_render.py`: TA-0025 (tests)
  - Rich text to HTML rendering
  - Sanitization enforcement
  - Heading extraction

## EVIDENCE
- `artifacts/pytest-render-report.json`
