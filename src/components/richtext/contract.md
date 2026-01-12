## COMPONENT_ID
C1-sub-richtext

## PURPOSE
Parse and validate rich text JSON (ProseMirror format) with sanitization.
Provides schema validation and safe HTML transformation.

## INPUTS
- `ValidateRichTextInput`: Validate rich text JSON structure
- `SanitizeRichTextInput`: Sanitize rich text for XSS prevention
- `TransformRichTextInput`: Transform nodes for rendering

## OUTPUTS
- `ValidateOutput`: Validation result with errors
- `SanitizeOutput`: Sanitized rich text JSON
- `TransformOutput`: Transformed node tree

## DEPENDENCIES (PORTS)
- `RulesPort`: Rich text rules (allowed nodes, marks, attributes)

## SIDE EFFECTS
- None (pure transformation)

## INVARIANTS
- I1: Only whitelisted node types allowed
- I2: Only whitelisted marks allowed
- I3: URLs sanitized and validated
- I4: No script content in output
- I5: Nested depth limited

## ERROR SEMANTICS
- Returns validation errors for invalid structure
- Strips disallowed content silently

## TESTS
- `tests/unit/test_richtext.py`: TA-0023, TA-0024 (51 tests)
  - Schema validation
  - XSS sanitization
  - Node type enforcement

## EVIDENCE
- `artifacts/pytest-richtext-report.json`
