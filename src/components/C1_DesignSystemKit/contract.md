# Component Contract: C1-DesignSystemKit

## COMPONENT_ID

C1-DesignSystemKit

## PURPOSE

Defines and validates the design system foundations: Tailwind tokens, typography/prose patterns, spacing scale, color system, and motion primitives. Provides validation utilities to ensure consistent application of design rules across the application.

## INPUTS

- `ColorToken`: Hex color value to validate against the design system
- `SpacingValue`: Spacing value to validate against the scale
- `TypographyConfig`: Typography configuration to validate
- `ProseContent`: HTML/markup content to validate for prose rules

## OUTPUTS

- `ValidationResult`: Pass/fail with specific violations and recommendations
- `DesignTokens`: Exported token definitions for use in configuration
- `AccessibilityReport`: Contrast ratios and WCAG compliance status

## DEPENDENCIES (PORTS)

- None (pure design validation, no external dependencies)

## SIDE EFFECTS

- None (functional core only - pure validation)

## INVARIANTS

- I1: All color tokens must meet WCAG 2.1 AA contrast requirements (4.5:1 for text, 3:1 for UI)
- I2: Spacing values must follow the established scale (4px base unit)
- I3: Typography must use the defined font families only
- I4: Prose content must follow heading order (no skipped levels)
- I5: External links in prose must have rel="noopener noreferrer"

## ERROR SEMANTICS

- Validation functions return `ValidationResult` with:
  - `is_valid: bool`
  - `violations: list[str]`
  - `warnings: list[str]`
- No exceptions thrown for validation failures

## RULES DEPENDENCIES

- Section: `content.sanitization`
- Keys: `html_allowlist_profile`, `enforce_heading_order`, `rel_attribute_policy`

## SPEC REFS

- Epics: E1.1 (Design system foundations)
- Test Assertions: TA-E1.1-01 (visual snapshot tests), TA-E1.1-02 (accessibility checks)
- Regression Invariants: R6 (external links sanitization)

## FC (Functional Core)

Pure functions with no I/O:

### Color System
- `validate_color_token(hex: str) -> ValidationResult`: Validate hex color format
- `calculate_contrast_ratio(fg: str, bg: str) -> float`: WCAG contrast ratio calculation
- `check_wcag_aa_compliance(fg: str, bg: str, is_large_text: bool) -> ValidationResult`: AA compliance check

### Spacing System
- `validate_spacing(value: int) -> ValidationResult`: Validate against spacing scale
- `get_spacing_scale() -> list[int]`: Return the spacing scale (4, 8, 12, 16, 20, 24, 32, 40, 48, 64)

### Typography System
- `validate_font_family(family: str) -> ValidationResult`: Validate against allowed families
- `get_allowed_fonts() -> list[str]`: Return allowed font families

### Prose Rules
- `validate_heading_order(headings: list[int]) -> ValidationResult`: Check heading level sequence
- `validate_external_links(links: list[dict]) -> ValidationResult`: Check rel attributes

## IS (Imperative Shell)

- None (this component is pure functional core)

## TESTS

- `tests/unit/test_design_system.py`: Design token validation tests
  - Color token format validation
  - Contrast ratio calculations
  - Spacing scale validation
  - Typography validation
  - Heading order validation
  - External link validation
- Test Assertions: TA-E1.1-01, TA-E1.1-02

## EVIDENCE

- `artifacts/design_system_validation.json`: Validation run results
- Visual snapshot tests: Frontend Playwright tests (separate)
