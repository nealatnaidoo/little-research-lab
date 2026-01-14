"""
TA-E2.1-01, TA-E2.1-03: Public templates tests.

Tests for C2-PublicTemplates component validating:
- SSR metadata generation (TA-E2.1-01)
- Link sanitization (TA-E2.1-03, R6)
- Content visibility validation (R2)
- Prose structure validation

These tests ensure public templates meet SSR correctness and security requirements.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.components.C2_PublicTemplates.fc import (
    SiteConfig,
    extract_first_paragraph,
    extract_links,
    format_publish_date,
    generate_canonical_url,
    generate_og_image_url,
    generate_ssr_metadata,
    is_external_link,
    sanitize_external_links,
    truncate_description,
    validate_content_visibility,
    validate_prose_structure,
)


@pytest.fixture
def site_config() -> SiteConfig:
    """Standard site configuration for tests."""
    return SiteConfig(
        base_url="https://example.com",
        site_name="Test Site",
        default_og_image="/images/default-og.png",
        twitter_handle="@testsite",
    )


class TestCanonicalUrlGeneration:
    """TA-E2.1-01: Canonical URL generation tests."""

    def test_generates_absolute_url(self, site_config: SiteConfig) -> None:
        """Canonical URL is absolute."""
        url = generate_canonical_url("test-post", site_config.base_url)
        assert url.startswith("https://")
        assert "test-post" in url

    def test_uses_https(self) -> None:
        """Canonical URL forces HTTPS (I4)."""
        url = generate_canonical_url("test", "http://example.com")
        assert url.startswith("https://")
        assert "http://" not in url

    def test_includes_post_path(self, site_config: SiteConfig) -> None:
        """Canonical URL includes /p/ path."""
        url = generate_canonical_url("my-slug", site_config.base_url)
        assert "/p/my-slug" in url

    def test_handles_base_url_without_trailing_slash(self) -> None:
        """Works with base URL without trailing slash."""
        url = generate_canonical_url("test", "https://example.com")
        assert url == "https://example.com/p/test"

    def test_handles_base_url_with_trailing_slash(self) -> None:
        """Works with base URL with trailing slash."""
        url = generate_canonical_url("test", "https://example.com/")
        assert url == "https://example.com/p/test"


class TestOgImageUrlGeneration:
    """TA-E2.1-01: OG image URL generation tests."""

    def test_generates_asset_url(self) -> None:
        """Generates URL for asset ID."""
        url = generate_og_image_url("asset123", "https://example.com")
        assert url == "https://example.com/assets/asset123"

    def test_returns_none_for_no_image(self) -> None:
        """Returns None when no image ID or default."""
        url = generate_og_image_url(None, "https://example.com", None)
        assert url is None

    def test_returns_default_image(self) -> None:
        """Returns default image when no asset ID."""
        url = generate_og_image_url(None, "https://example.com", "/default.png")
        assert "default.png" in url

    def test_makes_relative_default_absolute(self) -> None:
        """Makes relative default image path absolute."""
        url = generate_og_image_url(None, "https://example.com", "/images/og.png")
        assert url.startswith("https://")

    def test_keeps_absolute_default(self) -> None:
        """Keeps already-absolute default URL."""
        url = generate_og_image_url(
            None, "https://example.com", "https://cdn.example.com/og.png"
        )
        assert url == "https://cdn.example.com/og.png"


class TestSSRMetadataGeneration:
    """TA-E2.1-01: Complete SSR metadata generation tests."""

    def test_generates_all_required_fields(self, site_config: SiteConfig) -> None:
        """Generates all required metadata fields."""
        metadata = generate_ssr_metadata(
            title="Test Post",
            slug="test-post",
            description="A test post description",
            og_image_id="img123",
            published_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
            updated_at=None,
            site_config=site_config,
        )

        assert metadata.title == "Test Post"
        assert metadata.og_title == "Test Post"
        assert metadata.twitter_title == "Test Post"
        assert metadata.canonical_url.startswith("https://")
        assert metadata.og_site_name == "Test Site"

    def test_truncates_long_description(self, site_config: SiteConfig) -> None:
        """Truncates description for meta tags."""
        long_desc = "x" * 300
        metadata = generate_ssr_metadata(
            title="Test",
            slug="test",
            description=long_desc,
            og_image_id=None,
            published_at=None,
            updated_at=None,
            site_config=site_config,
        )

        assert len(metadata.description) <= 163  # 160 + "..."
        assert len(metadata.og_description) <= 203  # 200 + "..."

    def test_includes_timestamps(self, site_config: SiteConfig) -> None:
        """Includes publication timestamps in ISO format."""
        pub_time = datetime(2024, 1, 15, tzinfo=UTC)
        mod_time = datetime(2024, 1, 20, tzinfo=UTC)

        metadata = generate_ssr_metadata(
            title="Test",
            slug="test",
            description="",
            og_image_id=None,
            published_at=pub_time,
            updated_at=mod_time,
            site_config=site_config,
        )

        assert metadata.published_time is not None
        assert "2024-01-15" in metadata.published_time
        assert metadata.modified_time is not None
        assert "2024-01-20" in metadata.modified_time

    def test_uses_summary_card_without_image(self, site_config: SiteConfig) -> None:
        """Uses summary card when no image available."""
        site_config.default_og_image = None
        metadata = generate_ssr_metadata(
            title="Test",
            slug="test",
            description="",
            og_image_id=None,
            published_at=None,
            updated_at=None,
            site_config=site_config,
        )

        assert metadata.twitter_card == "summary"

    def test_uses_large_image_card_with_image(self, site_config: SiteConfig) -> None:
        """Uses large image card when image available."""
        metadata = generate_ssr_metadata(
            title="Test",
            slug="test",
            description="",
            og_image_id="img123",
            published_at=None,
            updated_at=None,
            site_config=site_config,
        )

        assert metadata.twitter_card == "summary_large_image"


class TestExternalLinkDetection:
    """TA-E2.1-03: External link detection tests."""

    def test_absolute_url_different_domain_is_external(self) -> None:
        """Absolute URL to different domain is external."""
        assert is_external_link("https://other.com/page", "https://example.com")

    def test_absolute_url_same_domain_is_internal(self) -> None:
        """Absolute URL to same domain is internal."""
        assert not is_external_link("https://example.com/page", "https://example.com")

    def test_protocol_relative_is_external(self) -> None:
        """Protocol-relative URL is treated as external."""
        assert is_external_link("//cdn.example.com/script.js")

    def test_relative_url_is_internal(self) -> None:
        """Relative URL is internal."""
        assert not is_external_link("/about", "https://example.com")
        assert not is_external_link("about", "https://example.com")
        assert not is_external_link("#section", "https://example.com")

    def test_http_link_without_base_is_external(self) -> None:
        """HTTP link without base URL comparison is external."""
        assert is_external_link("https://any.com")

    def test_case_insensitive_domain_comparison(self) -> None:
        """Domain comparison is case-insensitive."""
        assert not is_external_link("https://EXAMPLE.COM/page", "https://example.com")


class TestLinkExtraction:
    """TA-E2.1-03: Link extraction tests."""

    def test_extracts_links_from_html(self) -> None:
        """Extracts links from HTML content."""
        html = '<p><a href="https://example.com">Example</a> text</p>'
        links = extract_links(html)

        assert len(links) == 1
        assert links[0].href == "https://example.com"

    def test_extracts_multiple_links(self) -> None:
        """Extracts multiple links."""
        html = '<a href="/a">A</a><a href="/b">B</a>'
        links = extract_links(html)

        assert len(links) == 2

    def test_detects_external_links(self) -> None:
        """Marks external links correctly."""
        html = '<a href="https://other.com">External</a><a href="/local">Local</a>'
        links = extract_links(html, "https://example.com")

        assert links[0].is_external
        assert not links[1].is_external

    def test_extracts_rel_attribute(self) -> None:
        """Extracts existing rel attribute."""
        html = '<a href="/page" rel="nofollow">Link</a>'
        links = extract_links(html)

        assert links[0].rel == "nofollow"


class TestLinkSanitization:
    """TA-E2.1-03, R6: Link sanitization tests."""

    def test_adds_rel_to_external_links(self) -> None:
        """Adds rel="noopener noreferrer" to external links (I1)."""
        html = '<a href="https://external.com">Link</a>'
        sanitized = sanitize_external_links(html, "https://example.com")

        assert 'rel="noopener noreferrer"' in sanitized

    def test_preserves_internal_links(self) -> None:
        """Does not modify internal links."""
        html = '<a href="/about">About</a>'
        sanitized = sanitize_external_links(html, "https://example.com")

        assert sanitized == html

    def test_preserves_existing_rel_attributes(self) -> None:
        """Preserves and extends existing rel attributes."""
        html = '<a href="https://ext.com" rel="nofollow">Link</a>'
        sanitized = sanitize_external_links(html, "https://example.com")

        assert "nofollow" in sanitized
        assert "noopener" in sanitized
        assert "noreferrer" in sanitized

    def test_handles_multiple_links(self) -> None:
        """Sanitizes multiple links correctly."""
        html = """
        <a href="https://ext1.com">Ext1</a>
        <a href="/local">Local</a>
        <a href="https://ext2.com">Ext2</a>
        """
        sanitized = sanitize_external_links(html, "https://example.com")

        # External links should have rel
        assert sanitized.count("noopener") == 2
        # Internal link should not
        assert '/local">Local' in sanitized

    def test_handles_protocol_relative_links(self) -> None:
        """Treats protocol-relative links as external."""
        html = '<a href="//cdn.example.com/file.js">CDN</a>'
        sanitized = sanitize_external_links(html)

        assert 'rel="noopener noreferrer"' in sanitized


class TestContentVisibilityValidation:
    """R2: Content visibility validation tests."""

    def test_published_state_is_valid(self) -> None:
        """Published state is publicly visible."""
        result = validate_content_visibility("published", None)
        assert result.is_valid

    def test_draft_state_is_invalid(self) -> None:
        """Draft state is not publicly visible (I3)."""
        result = validate_content_visibility("draft", None)
        assert not result.is_valid
        assert "draft" in result.violations[0]

    def test_scheduled_state_is_invalid(self) -> None:
        """Scheduled state is not publicly visible."""
        result = validate_content_visibility("scheduled", None)
        assert not result.is_valid

    def test_archived_state_is_invalid(self) -> None:
        """Archived state is not publicly visible."""
        result = validate_content_visibility("archived", None)
        assert not result.is_valid

    def test_future_publish_date_is_invalid(self) -> None:
        """Published content with future date is invalid."""
        future = datetime(2099, 1, 1, tzinfo=UTC)
        now = datetime(2024, 1, 1, tzinfo=UTC)

        result = validate_content_visibility("published", future, now)
        assert not result.is_valid
        assert "future" in result.violations[0]


class TestProseStructureValidation:
    """Prose structure validation tests."""

    def test_valid_heading_structure(self) -> None:
        """Valid heading structure passes."""
        blocks = [
            {"block_type": "heading", "data_json": {"level": 1}},
            {"block_type": "heading", "data_json": {"level": 2}},
            {"block_type": "heading", "data_json": {"level": 3}},
        ]
        result = validate_prose_structure(blocks)
        assert result.is_valid

    def test_skipped_heading_level_fails(self) -> None:
        """Skipped heading level fails validation."""
        blocks = [
            {"block_type": "heading", "data_json": {"level": 1}},
            {"block_type": "heading", "data_json": {"level": 3}},  # Skips h2
        ]
        result = validate_prose_structure(blocks)
        assert not result.is_valid

    def test_empty_blocks_valid(self) -> None:
        """Empty blocks list is valid."""
        result = validate_prose_structure([])
        assert result.is_valid


class TestDescriptionTruncation:
    """Description truncation tests."""

    def test_short_text_unchanged(self) -> None:
        """Short text is not truncated."""
        text = "Short description"
        result = truncate_description(text, 160)
        assert result == text

    def test_long_text_truncated(self) -> None:
        """Long text is truncated with ellipsis."""
        text = "x" * 200
        result = truncate_description(text, 160)
        assert len(result) <= 163
        assert result.endswith("...")

    def test_strips_html_tags(self) -> None:
        """HTML tags are stripped."""
        text = "<p>Hello <strong>world</strong></p>"
        result = truncate_description(text)
        assert "<" not in result
        assert "Hello world" in result

    def test_decodes_html_entities(self) -> None:
        """HTML entities are decoded."""
        text = "Hello &amp; world"
        result = truncate_description(text)
        assert "Hello & world" in result

    def test_truncates_at_word_boundary(self) -> None:
        """Truncation happens at word boundary when possible."""
        text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"
        result = truncate_description(text, 30)
        # Should not cut in middle of word
        assert not result.endswith("ord...")


class TestFirstParagraphExtraction:
    """First paragraph extraction tests."""

    def test_extracts_text_block(self) -> None:
        """Extracts text from text block."""
        blocks = [{"block_type": "text", "data_json": {"text": "First paragraph"}}]
        result = extract_first_paragraph(blocks)
        assert result == "First paragraph"

    def test_skips_empty_blocks(self) -> None:
        """Skips empty text blocks."""
        blocks = [
            {"block_type": "text", "data_json": {"text": ""}},
            {"block_type": "text", "data_json": {"text": "Actual content"}},
        ]
        result = extract_first_paragraph(blocks)
        assert result == "Actual content"

    def test_returns_empty_for_no_text(self) -> None:
        """Returns empty string when no text blocks."""
        blocks = [{"block_type": "image", "data_json": {"src": "img.png"}}]
        result = extract_first_paragraph(blocks)
        assert result == ""


class TestPublishDateFormatting:
    """Publish date formatting tests."""

    def test_formats_date(self) -> None:
        """Formats date with default format."""
        dt = datetime(2024, 1, 15, tzinfo=UTC)
        result = format_publish_date(dt)
        assert "January" in result
        assert "15" in result
        assert "2024" in result

    def test_custom_format(self) -> None:
        """Supports custom format string."""
        dt = datetime(2024, 1, 15, tzinfo=UTC)
        result = format_publish_date(dt, "%Y-%m-%d")
        assert result == "2024-01-15"

    def test_none_returns_empty(self) -> None:
        """None date returns empty string."""
        result = format_publish_date(None)
        assert result == ""
