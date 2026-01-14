"""
C1-DesignSystemKit Functional Core: Pure validation functions.

No I/O operations - all functions are pure and deterministic.
Implements design token validation per E1.1 spec requirements.

Spec refs: E1.1, TA-E1.1-01, TA-E1.1-02
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of a design system validation check."""

    is_valid: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# SPACING SYSTEM
# Base unit: 4px, following Tailwind conventions
# ═══════════════════════════════════════════════════════════════════════════

SPACING_SCALE = (0, 1, 2, 4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 36, 40, 44, 48, 56, 64, 80, 96)
"""Spacing scale in pixels. Follows 4px base unit with common breakpoints."""


def get_spacing_scale() -> tuple[int, ...]:
    """Return the spacing scale (4px base unit)."""
    return SPACING_SCALE


def validate_spacing(value: int) -> ValidationResult:
    """
    Validate a spacing value against the design scale.

    Args:
        value: Spacing value in pixels

    Returns:
        ValidationResult with violations if value is not on scale
    """
    if value in SPACING_SCALE:
        return ValidationResult(is_valid=True)

    # Find nearest values on scale
    lower = max((s for s in SPACING_SCALE if s < value), default=0)
    upper = min((s for s in SPACING_SCALE if s > value), default=SPACING_SCALE[-1])

    return ValidationResult(
        is_valid=False,
        violations=[f"Spacing {value}px is not on the design scale"],
        warnings=[f"Nearest values: {lower}px or {upper}px"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY SYSTEM
# ═══════════════════════════════════════════════════════════════════════════

ALLOWED_FONTS = (
    "var(--font-terminal)",
    "var(--font-arcade)",
    "var(--font-mono)",
    "system-ui",
    "sans-serif",
    "monospace",
)
"""Allowed font families in the design system."""


def get_allowed_fonts() -> tuple[str, ...]:
    """Return allowed font families."""
    return ALLOWED_FONTS


def validate_font_family(family: str) -> ValidationResult:
    """
    Validate a font family against the design system.

    Args:
        family: Font family string

    Returns:
        ValidationResult with violations if font is not allowed
    """
    # Normalize and check each font in the stack
    fonts = [f.strip().lower() for f in family.split(",")]
    allowed_lower = [f.lower() for f in ALLOWED_FONTS]

    invalid_fonts = []
    for font in fonts:
        # Check if font matches any allowed font (exact or partial)
        if not any(allowed in font or font in allowed for allowed in allowed_lower):
            invalid_fonts.append(font)

    if invalid_fonts:
        return ValidationResult(
            is_valid=False,
            violations=[f"Font '{f}' is not in the design system" for f in invalid_fonts],
        )

    return ValidationResult(is_valid=True)


# ═══════════════════════════════════════════════════════════════════════════
# COLOR SYSTEM
# WCAG 2.1 AA compliance: 4.5:1 for normal text, 3:1 for large text/UI
# ═══════════════════════════════════════════════════════════════════════════

HEX_COLOR_PATTERN = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")


def validate_color_token(hex_color: str) -> ValidationResult:
    """
    Validate a hex color token format.

    Args:
        hex_color: Color in hex format (#RGB or #RRGGBB)

    Returns:
        ValidationResult with violations if format is invalid
    """
    if HEX_COLOR_PATTERN.match(hex_color):
        return ValidationResult(is_valid=True)

    return ValidationResult(
        is_valid=False,
        violations=[f"Invalid hex color format: {hex_color}. Expected #RGB or #RRGGBB"],
    )


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")

    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)

    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _relative_luminance(r: int, g: int, b: int) -> float:
    """
    Calculate relative luminance per WCAG 2.1.

    Formula: L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    Where R, G, B are sRGB values normalized and linearized.
    """

    def linearize(c: int) -> float:
        c_srgb = c / 255
        if c_srgb <= 0.04045:
            return c_srgb / 12.92
        return float(((c_srgb + 0.055) / 1.055) ** 2.4)

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def calculate_contrast_ratio(fg: str, bg: str) -> float:
    """
    Calculate WCAG contrast ratio between two colors.

    Args:
        fg: Foreground color in hex format
        bg: Background color in hex format

    Returns:
        Contrast ratio (1.0 to 21.0)
    """
    fg_rgb = _hex_to_rgb(fg)
    bg_rgb = _hex_to_rgb(bg)

    l1 = _relative_luminance(*fg_rgb)
    l2 = _relative_luminance(*bg_rgb)

    lighter = max(l1, l2)
    darker = min(l1, l2)

    return (lighter + 0.05) / (darker + 0.05)


def check_wcag_aa_compliance(
    fg: str,
    bg: str,
    is_large_text: bool = False,
) -> ValidationResult:
    """
    Check WCAG 2.1 AA compliance for color contrast.

    Args:
        fg: Foreground color in hex format
        bg: Background color in hex format
        is_large_text: True if text is >= 18pt or >= 14pt bold

    Returns:
        ValidationResult with compliance status
    """
    ratio = calculate_contrast_ratio(fg, bg)
    threshold = 3.0 if is_large_text else 4.5

    if ratio >= threshold:
        return ValidationResult(is_valid=True)

    return ValidationResult(
        is_valid=False,
        violations=[
            f"Contrast ratio {ratio:.2f}:1 does not meet WCAG AA "
            f"({threshold}:1 required for {'large' if is_large_text else 'normal'} text)"
        ],
        warnings=[f"Current contrast: {ratio:.2f}:1, needed: {threshold}:1"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# PROSE RULES
# Content sanitization and accessibility
# ═══════════════════════════════════════════════════════════════════════════


def validate_heading_order(headings: list[int]) -> ValidationResult:
    """
    Validate heading level sequence for accessibility.

    Headings should not skip levels (e.g., h1 -> h3 without h2).
    Invariant I4: Prose content must follow heading order.

    Args:
        headings: List of heading levels (1-6) in document order

    Returns:
        ValidationResult with violations if heading order is invalid
    """
    if not headings:
        return ValidationResult(is_valid=True)

    violations = []

    # First heading should typically be h1 (warning, not violation)
    warnings = []
    if headings[0] != 1:
        warnings.append(f"Document starts with h{headings[0]}, consider starting with h1")

    # Check for skipped levels
    for i in range(1, len(headings)):
        prev = headings[i - 1]
        curr = headings[i]

        # Going deeper should only increase by 1
        if curr > prev + 1:
            violations.append(
                f"Heading level skipped: h{prev} to h{curr} "
                f"(missing h{prev + 1})"
            )

    return ValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
        warnings=warnings,
    )


def validate_external_links(links: list[dict[str, str]]) -> ValidationResult:
    """
    Validate external links have proper rel attributes.

    Invariant I5: External links must have rel="noopener noreferrer".

    Args:
        links: List of link dicts with 'href' and 'rel' keys

    Returns:
        ValidationResult with violations for unsafe external links
    """
    violations = []

    for link in links:
        href = link.get("href", "")
        rel = link.get("rel", "")

        # Check if external (starts with http/https or //)
        is_external = href.startswith(("http://", "https://", "//"))

        if is_external:
            rel_values = set(rel.lower().split())
            required = {"noopener", "noreferrer"}

            missing = required - rel_values
            if missing:
                violations.append(
                    f"External link '{href}' missing rel attributes: {', '.join(missing)}"
                )

    return ValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
    )
