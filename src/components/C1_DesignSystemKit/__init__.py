"""
C1-DesignSystemKit: Design system foundations component.

Provides validation utilities for Tailwind tokens, typography/prose patterns,
spacing scale, color system, and motion primitives.

Spec refs: E1.1, TA-E1.1-01, TA-E1.1-02
"""

from src.components.C1_DesignSystemKit.fc import (
    ALLOWED_FONTS,
    SPACING_SCALE,
    ValidationResult,
    calculate_contrast_ratio,
    check_wcag_aa_compliance,
    get_allowed_fonts,
    get_spacing_scale,
    validate_color_token,
    validate_external_links,
    validate_font_family,
    validate_heading_order,
    validate_spacing,
)

__all__ = [
    "ValidationResult",
    "validate_color_token",
    "calculate_contrast_ratio",
    "check_wcag_aa_compliance",
    "validate_spacing",
    "get_spacing_scale",
    "validate_font_family",
    "get_allowed_fonts",
    "validate_heading_order",
    "validate_external_links",
    "SPACING_SCALE",
    "ALLOWED_FONTS",
]
