"""
TA-E2.2-01, TA-E2.2-02: Resource template tests.

Tests for C2-PublicTemplates resource template functionality:
- PDF embed support detection (TA-E2.2-01)
- Resource URL generation (TA-E2.2-02)
- File size/page count formatting
- Resource metadata generation

These tests ensure resource templates provide proper fallback UX
for browsers that don't support inline PDF viewing.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.components.C2_PublicTemplates.fc import (
    ResourceInfo,
    SiteConfig,
    format_file_size,
    format_page_count,
    generate_resource_metadata,
    generate_resource_render_config,
    generate_resource_urls,
    supports_pdf_embed,
)

# User agent strings for testing (defined at module level to avoid long lines)
UA_DESKTOP_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
UA_DESKTOP_FIREFOX = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
    "Gecko/20100101 Firefox/121.0"
)
UA_DESKTOP_SAFARI = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
)
UA_IPHONE_SAFARI = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.2 Mobile/15E148 Safari/604.1"
)
UA_IPAD_SAFARI = (
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.2 Mobile/15E148 Safari/604.1"
)
UA_CHROME_IOS = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1"
)
UA_FIREFOX_IOS = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "FxiOS/121.0 Mobile/15E148 Safari/605.1.15"
)
UA_FACEBOOK = (
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Version/4.0 Chrome/120.0.0.0 "
    "Mobile Safari/537.36 [FBAN/FB4A]"
)
UA_INSTAGRAM = (
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 Instagram"
)
UA_TWITTER = (
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 Twitter"
)
UA_LINKEDIN = (
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 LinkedIn"
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


@pytest.fixture
def pdf_resource() -> ResourceInfo:
    """Standard PDF resource for tests."""
    return ResourceInfo(
        asset_id="pdf123",
        filename="research-paper.pdf",
        mime_type="application/pdf",
        file_size_bytes=2_500_000,  # 2.5 MB
        page_count=12,
    )


class TestPdfEmbedSupport:
    """TA-E2.2-01: PDF embed support detection tests."""

    def test_desktop_chrome_supports_embed(self) -> None:
        """Desktop Chrome supports PDF embed."""
        supports, reason = supports_pdf_embed(UA_DESKTOP_CHROME)

        assert supports is True
        assert reason is None

    def test_desktop_firefox_supports_embed(self) -> None:
        """Desktop Firefox supports PDF embed."""
        supports, reason = supports_pdf_embed(UA_DESKTOP_FIREFOX)

        assert supports is True
        assert reason is None

    def test_desktop_safari_supports_embed(self) -> None:
        """Desktop Safari supports PDF embed."""
        supports, reason = supports_pdf_embed(UA_DESKTOP_SAFARI)

        assert supports is True
        assert reason is None

    def test_iphone_safari_does_not_support_embed(self) -> None:
        """iPhone Safari does not support PDF embed (TA-E2.2-01)."""
        supports, reason = supports_pdf_embed(UA_IPHONE_SAFARI)

        assert supports is False
        assert "iOS Safari" in reason

    def test_ipad_safari_does_not_support_embed(self) -> None:
        """iPad Safari does not support PDF embed."""
        supports, reason = supports_pdf_embed(UA_IPAD_SAFARI)

        assert supports is False
        assert "iOS Safari" in reason

    def test_chrome_ios_does_not_support_embed(self) -> None:
        """Chrome on iOS does not support PDF embed."""
        supports, reason = supports_pdf_embed(UA_CHROME_IOS)

        assert supports is False
        assert "iOS" in reason  # May match Safari or iOS browsers pattern

    def test_firefox_ios_does_not_support_embed(self) -> None:
        """Firefox on iOS does not support PDF embed."""
        supports, reason = supports_pdf_embed(UA_FIREFOX_IOS)

        assert supports is False
        assert "iOS" in reason  # May match Safari or iOS browsers pattern

    def test_facebook_inapp_browser_does_not_support_embed(self) -> None:
        """Facebook in-app browser does not support PDF embed."""
        supports, reason = supports_pdf_embed(UA_FACEBOOK)

        assert supports is False
        assert "In-app browsers" in reason

    def test_instagram_inapp_browser_does_not_support_embed(self) -> None:
        """Instagram in-app browser does not support PDF embed."""
        supports, reason = supports_pdf_embed(UA_INSTAGRAM)

        assert supports is False
        assert "In-app browsers" in reason

    def test_twitter_inapp_browser_does_not_support_embed(self) -> None:
        """Twitter in-app browser does not support PDF embed."""
        supports, reason = supports_pdf_embed(UA_TWITTER)

        assert supports is False
        assert "In-app browsers" in reason

    def test_linkedin_inapp_browser_does_not_support_embed(self) -> None:
        """LinkedIn in-app browser does not support PDF embed."""
        supports, reason = supports_pdf_embed(UA_LINKEDIN)

        assert supports is False
        assert "In-app browsers" in reason

    def test_unknown_user_agent_assumes_support(self) -> None:
        """Unknown user agent assumes embed support."""
        supports, reason = supports_pdf_embed(None)

        assert supports is True
        assert reason is None

    def test_empty_user_agent_assumes_support(self) -> None:
        """Empty user agent assumes embed support."""
        supports, reason = supports_pdf_embed("")

        assert supports is True
        assert reason is None


class TestResourceUrlGeneration:
    """TA-E2.2-02: Resource URL generation tests."""

    def test_generates_embed_url(self) -> None:
        """Generates correct embed URL."""
        embed, download, open_url = generate_resource_urls("asset123", "https://example.com")

        assert embed == "https://example.com/assets/asset123"

    def test_generates_download_url_with_query_param(self) -> None:
        """Download URL has download=true query param."""
        embed, download, open_url = generate_resource_urls("asset123", "https://example.com")

        assert download == "https://example.com/assets/asset123?download=true"

    def test_generates_open_url(self) -> None:
        """Open URL matches embed URL."""
        embed, download, open_url = generate_resource_urls("asset123", "https://example.com")

        assert open_url == embed

    def test_forces_https(self) -> None:
        """Forces HTTPS for all URLs."""
        embed, download, open_url = generate_resource_urls("asset123", "http://example.com")

        assert embed.startswith("https://")
        assert download.startswith("https://")
        assert open_url.startswith("https://")

    def test_handles_trailing_slash(self) -> None:
        """Handles base URL with trailing slash."""
        embed, download, open_url = generate_resource_urls("asset123", "https://example.com/")

        assert embed == "https://example.com/assets/asset123"

    def test_handles_no_trailing_slash(self) -> None:
        """Handles base URL without trailing slash."""
        embed, download, open_url = generate_resource_urls("asset123", "https://example.com")

        assert embed == "https://example.com/assets/asset123"


class TestFileSizeFormatting:
    """File size formatting tests."""

    def test_formats_bytes(self) -> None:
        """Formats small sizes in bytes."""
        assert format_file_size(512) == "512 B"

    def test_formats_kilobytes(self) -> None:
        """Formats KB sizes."""
        assert format_file_size(1024) == "1 KB"
        assert format_file_size(2048) == "2 KB"

    def test_formats_megabytes(self) -> None:
        """Formats MB sizes with one decimal."""
        assert format_file_size(1_048_576) == "1.0 MB"
        assert format_file_size(2_621_440) == "2.5 MB"

    def test_formats_gigabytes(self) -> None:
        """Formats GB sizes with one decimal."""
        assert format_file_size(1_073_741_824) == "1.0 GB"
        assert format_file_size(5_368_709_120) == "5.0 GB"

    def test_handles_zero(self) -> None:
        """Handles zero bytes."""
        assert format_file_size(0) == "0 B"

    def test_handles_negative(self) -> None:
        """Handles negative size."""
        assert format_file_size(-1) == "Unknown size"


class TestPageCountFormatting:
    """Page count formatting tests."""

    def test_formats_single_page(self) -> None:
        """Formats single page correctly."""
        assert format_page_count(1) == "1 page"

    def test_formats_multiple_pages(self) -> None:
        """Formats multiple pages correctly."""
        assert format_page_count(12) == "12 pages"
        assert format_page_count(100) == "100 pages"

    def test_returns_none_for_none(self) -> None:
        """Returns None when page count is None."""
        assert format_page_count(None) is None

    def test_returns_none_for_zero(self) -> None:
        """Returns None when page count is zero."""
        assert format_page_count(0) is None

    def test_returns_none_for_negative(self) -> None:
        """Returns None when page count is negative."""
        assert format_page_count(-1) is None


class TestResourceRenderConfig:
    """Resource render config generation tests."""

    def test_generates_config_for_pdf(self, pdf_resource: ResourceInfo) -> None:
        """Generates complete config for PDF resource."""
        config = generate_resource_render_config(
            pdf_resource, "https://example.com", user_agent=None
        )

        assert config.embed_url == "https://example.com/assets/pdf123"
        assert config.download_url == "https://example.com/assets/pdf123?download=true"
        assert config.open_url == config.embed_url
        assert config.file_size_display == "2.4 MB"  # 2.5 million bytes
        assert config.page_count_display == "12 pages"
        assert config.supports_embed is True
        assert config.fallback_reason is None

    def test_fallback_for_ios_safari(self, pdf_resource: ResourceInfo) -> None:
        """Falls back for iOS Safari."""
        config = generate_resource_render_config(
            pdf_resource, "https://example.com", user_agent=UA_IPHONE_SAFARI
        )

        assert config.supports_embed is False
        assert config.fallback_reason is not None
        assert "iOS" in config.fallback_reason

    def test_non_pdf_does_not_support_embed(self) -> None:
        """Non-PDF resources don't support embed."""
        docx_resource = ResourceInfo(
            asset_id="doc123",
            filename="document.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size_bytes=100_000,
            page_count=None,
        )
        config = generate_resource_render_config(
            docx_resource, "https://example.com", user_agent=None
        )

        assert config.supports_embed is False
        assert "Only PDF" in config.fallback_reason


class TestResourceMetadata:
    """Resource metadata generation tests."""

    def test_generates_metadata_with_file_info(
        self, site_config: SiteConfig, pdf_resource: ResourceInfo
    ) -> None:
        """Generates metadata including file info in description."""
        metadata = generate_resource_metadata(
            title="Research Paper",
            slug="research-paper",
            description="A detailed study",
            resource=pdf_resource,
            published_at=datetime(2024, 1, 15, tzinfo=UTC),
            site_config=site_config,
        )

        assert metadata.title == "Research Paper"
        assert "2.4 MB" in metadata.description
        assert "12 pages" in metadata.description

    def test_uses_resource_path(
        self, site_config: SiteConfig, pdf_resource: ResourceInfo
    ) -> None:
        """Uses /r/ path for resource canonical URL."""
        metadata = generate_resource_metadata(
            title="Research Paper",
            slug="research-paper",
            description=None,
            resource=pdf_resource,
            published_at=None,
            site_config=site_config,
        )

        assert "/r/research-paper" in metadata.canonical_url
        assert "/p/" not in metadata.canonical_url

    def test_uses_summary_twitter_card(
        self, site_config: SiteConfig, pdf_resource: ResourceInfo
    ) -> None:
        """Uses summary card (not large image) for PDFs."""
        metadata = generate_resource_metadata(
            title="Research Paper",
            slug="research-paper",
            description=None,
            resource=pdf_resource,
            published_at=None,
            site_config=site_config,
        )

        assert metadata.twitter_card == "summary"

    def test_handles_no_description(
        self, site_config: SiteConfig, pdf_resource: ResourceInfo
    ) -> None:
        """Handles missing description gracefully."""
        metadata = generate_resource_metadata(
            title="Research Paper",
            slug="research-paper",
            description=None,
            resource=pdf_resource,
            published_at=None,
            site_config=site_config,
        )

        assert "PDF resource" in metadata.description
        assert "2.4 MB" in metadata.description

    def test_includes_publish_time(
        self, site_config: SiteConfig, pdf_resource: ResourceInfo
    ) -> None:
        """Includes publish time in metadata."""
        pub_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        metadata = generate_resource_metadata(
            title="Research Paper",
            slug="research-paper",
            description="A study",
            resource=pdf_resource,
            published_at=pub_time,
            site_config=site_config,
        )

        assert metadata.published_time is not None
        assert "2024-01-15" in metadata.published_time

    def test_handles_no_page_count(self, site_config: SiteConfig) -> None:
        """Handles resource without page count."""
        resource = ResourceInfo(
            asset_id="pdf456",
            filename="document.pdf",
            mime_type="application/pdf",
            file_size_bytes=500_000,  # 488 KB (1 KB = 1024 bytes)
            page_count=None,
        )
        metadata = generate_resource_metadata(
            title="Document",
            slug="document",
            description="A document",
            resource=resource,
            published_at=None,
            site_config=site_config,
        )

        # Should still include file size but not page count
        assert "488 KB" in metadata.description
