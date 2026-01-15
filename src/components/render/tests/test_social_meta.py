"""
Unit tests for Social Meta Tag generation.

Spec refs: E15.3
Test assertions: TA-0072, TA-0073

Tests:
- TA-0072: Twitter Card meta tags generation
- TA-0073: OpenGraph meta tags generation
"""

from __future__ import annotations

from .._impl import (
    DEFAULT_FACEBOOK_IMAGE_CONFIG,
    DEFAULT_TWITTER_IMAGE_CONFIG,
    generate_opengraph_meta,
    generate_social_meta_tags,
    generate_twitter_card_meta,
    validate_image_dimensions,
)

# --- Image Dimension Validation Tests ---


class TestValidateImageDimensions:
    """Tests for image dimension validation."""

    def test_valid_dimensions(self) -> None:
        """Valid dimensions pass validation."""
        is_valid, warning = validate_image_dimensions(
            width=1200, height=630, min_width=280, min_height=150
        )
        assert is_valid is True
        assert warning is None

    def test_dimensions_too_small(self) -> None:
        """Dimensions below minimum fail validation."""
        is_valid, warning = validate_image_dimensions(
            width=200, height=100, min_width=280, min_height=150
        )
        assert is_valid is False
        assert warning is not None
        assert "200x100" in warning
        assert "280x150" in warning

    def test_width_too_small(self) -> None:
        """Width below minimum fails validation."""
        is_valid, warning = validate_image_dimensions(
            width=200, height=200, min_width=280, min_height=150
        )
        assert is_valid is False
        assert warning is not None

    def test_height_too_small(self) -> None:
        """Height below minimum fails validation."""
        is_valid, warning = validate_image_dimensions(
            width=300, height=100, min_width=280, min_height=150
        )
        assert is_valid is False
        assert warning is not None

    def test_unknown_dimensions_pass(self) -> None:
        """Unknown dimensions (None) pass validation."""
        is_valid, warning = validate_image_dimensions(
            width=None, height=None, min_width=280, min_height=150
        )
        assert is_valid is True
        assert warning is None

    def test_partial_unknown_dimensions_pass(self) -> None:
        """Partially unknown dimensions pass validation."""
        is_valid, warning = validate_image_dimensions(
            width=1200, height=None, min_width=280, min_height=150
        )
        assert is_valid is True


# --- Twitter Card Meta Tests (TA-0072) ---


class TestGenerateTwitterCardMeta:
    """Tests for Twitter Card meta tag generation (TA-0072)."""

    def test_basic_twitter_card(self) -> None:
        """Generates basic Twitter Card tags."""
        tags, warnings = generate_twitter_card_meta(
            title="Test Article",
            description="This is a test description",
        )

        assert tags["twitter:card"] == "summary_large_image"
        assert tags["twitter:title"] == "Test Article"
        assert tags["twitter:description"] == "This is a test description"
        assert warnings == []

    def test_twitter_card_with_image(self) -> None:
        """Includes image in Twitter Card."""
        tags, warnings = generate_twitter_card_meta(
            title="Test Article",
            description="Description",
            image_url="https://example.com/image.jpg",
            image_alt="Alt text",
        )

        assert tags["twitter:image"] == "https://example.com/image.jpg"
        assert tags["twitter:image:alt"] == "Alt text"
        assert warnings == []

    def test_twitter_card_title_truncation(self) -> None:
        """Truncates long titles to 70 characters."""
        long_title = "A" * 100
        tags, warnings = generate_twitter_card_meta(
            title=long_title,
            description="Description",
        )

        assert len(tags["twitter:title"]) == 70

    def test_twitter_card_description_truncation(self) -> None:
        """Truncates long descriptions to 200 characters."""
        long_desc = "B" * 250
        tags, warnings = generate_twitter_card_meta(
            title="Title",
            description=long_desc,
        )

        assert len(tags["twitter:description"]) == 200

    def test_twitter_card_summary_type(self) -> None:
        """Can specify summary card type."""
        tags, warnings = generate_twitter_card_meta(
            title="Title",
            description="Description",
            card_type="summary",
        )

        assert tags["twitter:card"] == "summary"

    def test_twitter_card_downgrades_on_small_image(self) -> None:
        """Downgrades to summary card if image too small for large image."""
        tags, warnings = generate_twitter_card_meta(
            title="Title",
            description="Description",
            image_url="https://example.com/small.jpg",
            image_width=100,
            image_height=100,
            card_type="summary_large_image",
        )

        # Downgrades to summary
        assert tags["twitter:card"] == "summary"
        assert len(warnings) == 1
        assert "Twitter" in warnings[0]

    def test_twitter_card_valid_large_image(self) -> None:
        """Keeps summary_large_image for valid dimensions."""
        tags, warnings = generate_twitter_card_meta(
            title="Title",
            description="Description",
            image_url="https://example.com/large.jpg",
            image_width=1200,
            image_height=630,
            card_type="summary_large_image",
        )

        assert tags["twitter:card"] == "summary_large_image"
        assert tags["twitter:image"] == "https://example.com/large.jpg"
        assert warnings == []

    def test_default_image_config(self) -> None:
        """Default Twitter image config has correct values."""
        assert DEFAULT_TWITTER_IMAGE_CONFIG.min_width == 280
        assert DEFAULT_TWITTER_IMAGE_CONFIG.min_height == 150


# --- OpenGraph Meta Tests (TA-0073) ---


class TestGenerateOpenGraphMeta:
    """Tests for OpenGraph meta tag generation (TA-0073)."""

    def test_basic_og_tags(self) -> None:
        """Generates basic OpenGraph tags."""
        tags, warnings = generate_opengraph_meta(
            title="Test Article",
            description="This is a test description",
            url="https://example.com/p/test-article",
            site_name="Example Site",
        )

        assert tags["og:type"] == "article"
        assert tags["og:title"] == "Test Article"
        assert tags["og:description"] == "This is a test description"
        assert tags["og:url"] == "https://example.com/p/test-article"
        assert tags["og:site_name"] == "Example Site"
        assert warnings == []

    def test_og_with_image(self) -> None:
        """Includes image in OpenGraph tags."""
        tags, warnings = generate_opengraph_meta(
            title="Test Article",
            description="Description",
            url="https://example.com/p/test",
            site_name="Site",
            image_url="https://example.com/image.jpg",
            image_alt="Alt text",
            image_width=1200,
            image_height=630,
        )

        assert tags["og:image"] == "https://example.com/image.jpg"
        assert tags["og:image:alt"] == "Alt text"
        assert tags["og:image:width"] == "1200"
        assert tags["og:image:height"] == "630"
        assert warnings == []

    def test_og_website_type(self) -> None:
        """Can specify website type for homepage."""
        tags, warnings = generate_opengraph_meta(
            title="Site Title",
            description="Site description",
            url="https://example.com",
            site_name="Site",
            og_type="website",
        )

        assert tags["og:type"] == "website"

    def test_og_warns_on_small_image(self) -> None:
        """Warns but doesn't include image if too small."""
        tags, warnings = generate_opengraph_meta(
            title="Title",
            description="Description",
            url="https://example.com/p/test",
            site_name="Site",
            image_url="https://example.com/small.jpg",
            image_width=100,
            image_height=100,
        )

        # Image not included, warning generated
        assert "og:image" not in tags
        assert len(warnings) == 1
        assert "OpenGraph" in warnings[0]

    def test_og_valid_image_dimensions(self) -> None:
        """Includes image with valid dimensions."""
        tags, warnings = generate_opengraph_meta(
            title="Title",
            description="Description",
            url="https://example.com/p/test",
            site_name="Site",
            image_url="https://example.com/valid.jpg",
            image_width=400,
            image_height=400,
        )

        assert tags["og:image"] == "https://example.com/valid.jpg"
        assert warnings == []

    def test_default_facebook_config(self) -> None:
        """Default Facebook image config has correct values."""
        assert DEFAULT_FACEBOOK_IMAGE_CONFIG.min_width == 200
        assert DEFAULT_FACEBOOK_IMAGE_CONFIG.min_height == 200


# --- Combined Social Meta Tests ---


class TestGenerateSocialMetaTags:
    """Tests for combined social meta tag generation."""

    def test_combined_tags_basic(self) -> None:
        """Generates both Twitter and OG tags."""
        tags, warnings = generate_social_meta_tags(
            title="Test Article",
            description="Test description",
            canonical_url="https://example.com/p/test",
            site_name="Example Site",
        )

        # Twitter tags
        assert "twitter:card" in tags
        assert "twitter:title" in tags
        assert "twitter:description" in tags

        # OG tags
        assert "og:type" in tags
        assert "og:title" in tags
        assert "og:description" in tags
        assert "og:url" in tags
        assert "og:site_name" in tags

        assert warnings == []

    def test_combined_tags_with_image(self) -> None:
        """Includes image in both Twitter and OG tags."""
        tags, warnings = generate_social_meta_tags(
            title="Article",
            description="Description",
            canonical_url="https://example.com/p/article",
            site_name="Site",
            image_url="https://example.com/image.jpg",
            image_width=1200,
            image_height=630,
        )

        assert tags["twitter:image"] == "https://example.com/image.jpg"
        assert tags["og:image"] == "https://example.com/image.jpg"
        assert warnings == []

    def test_combined_tags_article_type(self) -> None:
        """Uses article type for content."""
        tags, warnings = generate_social_meta_tags(
            title="Article",
            description="Description",
            canonical_url="https://example.com/p/article",
            site_name="Site",
            content_type="article",
        )

        assert tags["og:type"] == "article"

    def test_combined_tags_website_type(self) -> None:
        """Uses website type for homepage."""
        tags, warnings = generate_social_meta_tags(
            title="Site",
            description="Description",
            canonical_url="https://example.com",
            site_name="Site",
            content_type="website",
        )

        assert tags["og:type"] == "website"

    def test_combined_tags_custom_dimensions(self) -> None:
        """Respects custom dimension requirements."""
        tags, warnings = generate_social_meta_tags(
            title="Article",
            description="Description",
            canonical_url="https://example.com/p/article",
            site_name="Site",
            image_url="https://example.com/image.jpg",
            image_width=300,
            image_height=200,
            min_twitter_width=400,  # Image too small for Twitter
            min_og_width=200,  # Image OK for OG
        )

        # Twitter warns, OG includes image
        assert any("Twitter" in w for w in warnings)
        assert tags["og:image"] == "https://example.com/image.jpg"

    def test_combined_tags_aggregates_warnings(self) -> None:
        """Aggregates warnings from both platforms."""
        tags, warnings = generate_social_meta_tags(
            title="Article",
            description="Description",
            canonical_url="https://example.com/p/article",
            site_name="Site",
            image_url="https://example.com/tiny.jpg",
            image_width=50,
            image_height=50,
            min_twitter_width=280,
            min_twitter_height=150,
            min_og_width=200,
            min_og_height=200,
        )

        # Both should warn
        assert len(warnings) == 2
        assert any("Twitter" in w for w in warnings)
        assert any("OpenGraph" in w for w in warnings)


# --- Integration Tests ---


class TestSocialMetaIntegration:
    """Integration tests for social meta generation."""

    def test_full_article_meta(self) -> None:
        """Complete meta generation for an article."""
        tags, warnings = generate_social_meta_tags(
            title="How to Build a REST API",
            description="Learn how to build scalable REST APIs with Python and FastAPI",
            canonical_url="https://littleresearchlab.com/p/how-to-build-rest-api",
            site_name="Little Research Lab",
            content_type="article",
            image_url="https://littleresearchlab.com/images/rest-api-cover.jpg",
            image_alt="REST API architecture diagram",
            image_width=1200,
            image_height=630,
        )

        # Verify all required tags present
        assert tags["twitter:card"] == "summary_large_image"
        assert tags["twitter:title"] == "How to Build a REST API"
        assert tags["og:type"] == "article"
        assert tags["og:url"] == "https://littleresearchlab.com/p/how-to-build-rest-api"
        assert tags["og:site_name"] == "Little Research Lab"
        assert warnings == []

    def test_homepage_meta(self) -> None:
        """Complete meta generation for homepage."""
        tags, warnings = generate_social_meta_tags(
            title="Little Research Lab",
            description="Technical articles and resources for developers",
            canonical_url="https://littleresearchlab.com",
            site_name="Little Research Lab",
            content_type="website",
        )

        assert tags["og:type"] == "website"
        assert tags["og:url"] == "https://littleresearchlab.com"
        assert warnings == []
