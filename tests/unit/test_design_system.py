"""
TA-E1.1-01, TA-E1.1-02: Design system validation tests.

Tests for C1-DesignSystemKit component validating:
- Color tokens and WCAG contrast
- Spacing scale adherence
- Typography font families
- Prose rules (heading order, external links)

These tests validate the design system rules enforcement.
"""

from __future__ import annotations

import pytest

from src.components.C1_DesignSystemKit.fc import (
    ALLOWED_FONTS,
    SPACING_SCALE,
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


class TestColorTokenValidation:
    """TA-E1.1-01: Color token format validation."""

    def test_valid_hex_6_digit(self) -> None:
        """Valid 6-digit hex colors pass validation."""
        result = validate_color_token("#FFFFFF")
        assert result.is_valid
        assert not result.violations

    def test_valid_hex_3_digit(self) -> None:
        """Valid 3-digit hex colors pass validation."""
        result = validate_color_token("#FFF")
        assert result.is_valid

    def test_valid_hex_lowercase(self) -> None:
        """Lowercase hex colors pass validation."""
        result = validate_color_token("#abc123")
        assert result.is_valid

    def test_invalid_no_hash(self) -> None:
        """Colors without hash prefix fail."""
        result = validate_color_token("FFFFFF")
        assert not result.is_valid
        assert "Invalid hex color format" in result.violations[0]

    def test_invalid_wrong_length(self) -> None:
        """Colors with wrong length fail."""
        result = validate_color_token("#FFFF")
        assert not result.is_valid

    def test_invalid_characters(self) -> None:
        """Colors with invalid characters fail."""
        result = validate_color_token("#GGGGGG")
        assert not result.is_valid


class TestContrastRatioCalculation:
    """TA-E1.1-02: WCAG contrast ratio calculations."""

    def test_black_on_white_max_contrast(self) -> None:
        """Black on white has maximum contrast (21:1)."""
        ratio = calculate_contrast_ratio("#000000", "#FFFFFF")
        assert ratio == pytest.approx(21.0, rel=0.01)

    def test_white_on_black_same_as_reverse(self) -> None:
        """Contrast is symmetric."""
        ratio1 = calculate_contrast_ratio("#000000", "#FFFFFF")
        ratio2 = calculate_contrast_ratio("#FFFFFF", "#000000")
        assert ratio1 == pytest.approx(ratio2, rel=0.01)

    def test_same_color_min_contrast(self) -> None:
        """Same color has minimum contrast (1:1)."""
        ratio = calculate_contrast_ratio("#808080", "#808080")
        assert ratio == pytest.approx(1.0, rel=0.01)

    def test_gray_on_white_mid_contrast(self) -> None:
        """Gray on white has mid-range contrast."""
        ratio = calculate_contrast_ratio("#767676", "#FFFFFF")
        # #767676 on white is approximately 4.54:1 (WCAG AA threshold)
        assert 4.5 <= ratio <= 5.0


class TestWCAGAACompliance:
    """TA-E1.1-02: WCAG AA compliance validation."""

    def test_high_contrast_passes_normal_text(self) -> None:
        """High contrast passes for normal text."""
        result = check_wcag_aa_compliance("#000000", "#FFFFFF")
        assert result.is_valid

    def test_low_contrast_fails_normal_text(self) -> None:
        """Low contrast fails for normal text."""
        result = check_wcag_aa_compliance("#AAAAAA", "#FFFFFF")
        assert not result.is_valid
        assert "4.5:1 required" in result.violations[0]

    def test_low_contrast_passes_large_text(self) -> None:
        """Lower threshold (3:1) applies to large text."""
        # Use a color that passes 3:1 but fails 4.5:1
        # #888888 on white is approximately 3.54:1
        result = check_wcag_aa_compliance("#888888", "#FFFFFF", is_large_text=True)
        assert result.is_valid

    def test_violation_includes_ratio(self) -> None:
        """Violation message includes actual ratio."""
        result = check_wcag_aa_compliance("#CCCCCC", "#FFFFFF")
        assert not result.is_valid
        assert ":1" in result.violations[0]


class TestSpacingValidation:
    """TA-E1.1-01: Spacing scale validation."""

    def test_get_spacing_scale_returns_tuple(self) -> None:
        """Spacing scale is returned as tuple."""
        scale = get_spacing_scale()
        assert isinstance(scale, tuple)
        assert 0 in scale  # Includes zero
        assert 4 in scale  # Base unit
        assert 16 in scale  # Common value

    def test_valid_spacing_on_scale(self) -> None:
        """Values on the scale pass validation."""
        for value in SPACING_SCALE:
            result = validate_spacing(value)
            assert result.is_valid, f"Spacing {value} should be valid"

    def test_invalid_spacing_off_scale(self) -> None:
        """Values off the scale fail validation."""
        result = validate_spacing(7)  # Not on scale
        assert not result.is_valid
        assert "not on the design scale" in result.violations[0]

    def test_invalid_spacing_shows_nearest(self) -> None:
        """Invalid spacing shows nearest valid values."""
        result = validate_spacing(5)
        assert not result.is_valid
        assert "4px" in result.warnings[0] or "6px" in result.warnings[0]


class TestTypographyValidation:
    """TA-E1.1-01: Typography font family validation."""

    def test_get_allowed_fonts_returns_tuple(self) -> None:
        """Allowed fonts is returned as tuple."""
        fonts = get_allowed_fonts()
        assert isinstance(fonts, tuple)
        assert "var(--font-terminal)" in fonts
        assert "system-ui" in fonts

    def test_valid_font_css_variable(self) -> None:
        """CSS variable fonts pass validation."""
        result = validate_font_family("var(--font-terminal)")
        assert result.is_valid

    def test_valid_font_system_stack(self) -> None:
        """System font stack passes validation."""
        result = validate_font_family("system-ui, sans-serif")
        assert result.is_valid

    def test_valid_font_mixed_stack(self) -> None:
        """Mixed font stack with valid fonts passes."""
        result = validate_font_family("var(--font-terminal), system-ui, sans-serif")
        assert result.is_valid

    def test_invalid_font_custom(self) -> None:
        """Custom fonts not in system fail validation."""
        result = validate_font_family("Comic Sans MS")
        assert not result.is_valid
        assert "not in the design system" in result.violations[0]


class TestHeadingOrderValidation:
    """TA-E1.1-02: Heading order accessibility validation."""

    def test_empty_headings_valid(self) -> None:
        """Empty heading list is valid."""
        result = validate_heading_order([])
        assert result.is_valid

    def test_sequential_headings_valid(self) -> None:
        """Sequential heading levels are valid."""
        result = validate_heading_order([1, 2, 3, 2, 3])
        assert result.is_valid

    def test_skipped_heading_invalid(self) -> None:
        """Skipped heading levels fail validation."""
        result = validate_heading_order([1, 3])  # Missing h2
        assert not result.is_valid
        assert "Heading level skipped" in result.violations[0]
        assert "missing h2" in result.violations[0]

    def test_multiple_skips_reported(self) -> None:
        """Multiple skipped levels are all reported."""
        result = validate_heading_order([1, 4, 6])  # Missing h2, h3, h5
        assert not result.is_valid
        assert len(result.violations) == 2

    def test_non_h1_start_warning(self) -> None:
        """Starting with non-h1 generates warning."""
        result = validate_heading_order([2, 3])
        assert result.is_valid  # Still valid
        assert len(result.warnings) > 0
        assert "consider starting with h1" in result.warnings[0]

    def test_decreasing_levels_valid(self) -> None:
        """Decreasing heading levels are valid."""
        result = validate_heading_order([1, 2, 3, 2, 1])
        assert result.is_valid


class TestExternalLinkValidation:
    """TA-E1.1-02: External link rel attribute validation (R6)."""

    def test_empty_links_valid(self) -> None:
        """Empty link list is valid."""
        result = validate_external_links([])
        assert result.is_valid

    def test_internal_link_no_rel_valid(self) -> None:
        """Internal links without rel are valid."""
        result = validate_external_links([
            {"href": "/about", "rel": ""},
            {"href": "#section", "rel": ""},
        ])
        assert result.is_valid

    def test_external_link_with_rel_valid(self) -> None:
        """External links with proper rel are valid."""
        result = validate_external_links([
            {"href": "https://example.com", "rel": "noopener noreferrer"},
        ])
        assert result.is_valid

    def test_external_link_missing_rel_invalid(self) -> None:
        """External links without rel fail validation."""
        result = validate_external_links([
            {"href": "https://example.com", "rel": ""},
        ])
        assert not result.is_valid
        assert "noopener" in result.violations[0]
        assert "noreferrer" in result.violations[0]

    def test_external_link_partial_rel_invalid(self) -> None:
        """External links with partial rel fail validation."""
        result = validate_external_links([
            {"href": "https://example.com", "rel": "noopener"},
        ])
        assert not result.is_valid
        assert "noreferrer" in result.violations[0]

    def test_http_link_considered_external(self) -> None:
        """HTTP links are treated as external."""
        result = validate_external_links([
            {"href": "http://example.com", "rel": ""},
        ])
        assert not result.is_valid

    def test_protocol_relative_link_considered_external(self) -> None:
        """Protocol-relative links (//) are treated as external."""
        result = validate_external_links([
            {"href": "//example.com/path", "rel": ""},
        ])
        assert not result.is_valid


class TestDesignTokenConstants:
    """Test design token constants are properly defined."""

    def test_spacing_scale_starts_at_zero(self) -> None:
        """Spacing scale includes zero."""
        assert SPACING_SCALE[0] == 0

    def test_spacing_scale_includes_base_unit(self) -> None:
        """Spacing scale includes 4px base unit."""
        assert 4 in SPACING_SCALE

    def test_spacing_scale_includes_common_values(self) -> None:
        """Spacing scale includes common values."""
        for value in [8, 12, 16, 24, 32, 48, 64]:
            assert value in SPACING_SCALE

    def test_allowed_fonts_includes_css_variables(self) -> None:
        """Allowed fonts includes CSS variable fonts."""
        assert any("var(--font" in f for f in ALLOWED_FONTS)

    def test_allowed_fonts_includes_fallbacks(self) -> None:
        """Allowed fonts includes system fallbacks."""
        assert "system-ui" in ALLOWED_FONTS
        assert "sans-serif" in ALLOWED_FONTS
