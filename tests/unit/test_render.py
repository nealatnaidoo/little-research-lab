"""
TA-0004, TA-0005: RenderService SSR metadata tests.

TA-0004: SSR meta snapshot (title, description, canonical, OG, Twitter)
TA-0005: OG image resolution rules (content > settings > default)

Spec refs: E1.2, R6
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.components.render import (
    ImageInfo,
    PageMetadata,
    RenderService,
    build_canonical_url,
    create_render_service,
    get_content_path,
    resolve_og_image,
    truncate_description,
)
from src.core.entities import ContentItem, SiteSettings


@pytest.fixture
def settings() -> SiteSettings:
    """Create test site settings."""
    return SiteSettings(
        site_title="Test Site",
        site_subtitle="A test site for testing",
        theme="light",
        social_links_json={
            "twitter": "https://twitter.com/test",
            "og_image": "https://example.com/og-default.png",
        },
    )


@pytest.fixture
def content() -> ContentItem:
    """Create test content item."""
    return ContentItem(
        id=uuid4(),
        type="post",
        slug="test-post",
        title="Test Post Title",
        summary="This is a test post summary for testing metadata generation.",
        status="published",
        owner_user_id=uuid4(),
    )


@pytest.fixture
def service() -> RenderService:
    """Create render service with test configuration."""
    return RenderService(
        base_url="https://example.com",
        default_og_image_url="https://example.com/default-og.png",
        routing_config={
            "posts_prefix": "/p",
            "resources_prefix": "/r",
        },
    )


class TestTA0004SSRMetaSnapshot:
    """TA-0004: SSR meta snapshot tests."""

    def test_build_page_metadata_includes_title(
        self, service: RenderService, settings: SiteSettings, content: ContentItem
    ) -> None:
        """Page metadata includes correct title."""
        meta = service.build_page_metadata(settings, content)

        assert meta.title == "Test Post Title | Test Site"

    def test_build_page_metadata_includes_description(
        self, service: RenderService, settings: SiteSettings, content: ContentItem
    ) -> None:
        """Page metadata includes description from content summary."""
        meta = service.build_page_metadata(settings, content)

        assert "test post summary" in meta.description.lower()

    def test_build_page_metadata_includes_canonical_url(
        self, service: RenderService, settings: SiteSettings, content: ContentItem
    ) -> None:
        """Page metadata includes correct canonical URL."""
        meta = service.build_page_metadata(settings, content)

        assert meta.canonical_url == "https://example.com/p/test-post"

    def test_build_page_metadata_includes_og_tags(
        self, service: RenderService, settings: SiteSettings, content: ContentItem
    ) -> None:
        """Page metadata includes OpenGraph tags."""
        meta = service.build_page_metadata(settings, content)

        assert meta.og_title == "Test Post Title"
        assert meta.og_type == "article"
        assert meta.og_url == "https://example.com/p/test-post"
        assert meta.og_site_name == "Test Site"

    def test_build_page_metadata_includes_twitter_tags(
        self, service: RenderService, settings: SiteSettings, content: ContentItem
    ) -> None:
        """Page metadata includes Twitter Card tags."""
        meta = service.build_page_metadata(settings, content)

        assert meta.twitter_card in ("summary", "summary_large_image")
        # twitter_title should be set when we have an OG title

    def test_homepage_metadata_uses_settings(
        self, service: RenderService, settings: SiteSettings
    ) -> None:
        """Homepage metadata uses site settings."""
        meta = service.build_homepage_metadata(settings)

        assert meta.title == "Test Site"
        assert "test site" in meta.description.lower()
        assert meta.canonical_url == "https://example.com/"
        assert meta.og_type == "website"

    def test_to_meta_tags_generates_all_tags(
        self, service: RenderService, settings: SiteSettings, content: ContentItem
    ) -> None:
        """to_meta_tags generates complete list of meta tags."""
        meta = service.build_page_metadata(settings, content)
        tags = meta.to_meta_tags()

        # Should have description, robots, og:*, twitter:*
        tag_names = [t.name for t in tags if t.name]
        tag_props = [t.property for t in tags if t.property]

        assert "description" in tag_names
        assert "robots" in tag_names
        assert "og:title" in tag_props
        assert "og:description" in tag_props
        assert "og:url" in tag_props
        assert "twitter:card" in tag_names

    def test_title_override(self, service: RenderService, settings: SiteSettings) -> None:
        """Custom title can be provided."""
        meta = service.build_page_metadata(settings, page_title="Custom Page Title")

        assert meta.title == "Custom Page Title"

    def test_description_override(self, service: RenderService, settings: SiteSettings) -> None:
        """Custom description can be provided."""
        meta = service.build_page_metadata(settings, page_description="Custom description here")

        assert "Custom description" in meta.description


class TestTA0005OGImageResolution:
    """TA-0005: OG image resolution rules tests."""

    def test_content_image_highest_priority(self) -> None:
        """Content image takes priority over all others."""
        content_img = "https://example.com/content-image.png"
        settings_img = "https://example.com/settings-image.png"
        default_img = "https://example.com/default-image.png"

        result = resolve_og_image(content_img, settings_img, default_img)

        assert result is not None
        assert result.url == content_img

    def test_settings_image_second_priority(self) -> None:
        """Settings image used when no content image."""
        settings_img = "https://example.com/settings-image.png"
        default_img = "https://example.com/default-image.png"

        result = resolve_og_image(None, settings_img, default_img)

        assert result is not None
        assert result.url == settings_img

    def test_default_image_lowest_priority(self) -> None:
        """Default image used when no other images available."""
        default_img = "https://example.com/default-image.png"

        result = resolve_og_image(None, None, default_img)

        assert result is not None
        assert result.url == default_img

    def test_no_image_returns_none(self) -> None:
        """Returns None when no images available."""
        result = resolve_og_image(None, None, None)

        assert result is None

    def test_empty_string_treated_as_none(self) -> None:
        """Empty strings are treated as no image."""
        default_img = "https://example.com/default.png"

        result = resolve_og_image("", "", default_img)

        # Empty string is falsy, so should fall through to default
        assert result is not None
        assert result.url == default_img

    def test_metadata_uses_resolved_og_image(
        self, service: RenderService, settings: SiteSettings, content: ContentItem
    ) -> None:
        """Page metadata uses resolved OG image."""
        meta = service.build_page_metadata(
            settings, content, og_image_url="https://example.com/specific.png"
        )

        assert meta.og_image == "https://example.com/specific.png"

    def test_metadata_falls_back_to_settings_og_image(
        self, service: RenderService, settings: SiteSettings, content: ContentItem
    ) -> None:
        """Page metadata falls back to settings OG image."""
        meta = service.build_page_metadata(settings, content)

        # Settings has og_image in social_links_json
        assert meta.og_image == "https://example.com/og-default.png"

    def test_metadata_falls_back_to_default_og_image(
        self, settings: SiteSettings, content: ContentItem
    ) -> None:
        """Page metadata falls back to default OG image."""
        # Create service with default OG image but settings without
        service = RenderService(
            base_url="https://example.com",
            default_og_image_url="https://example.com/default-og.png",
        )

        # Modify settings to remove og_image
        settings.social_links_json = {}

        meta = service.build_page_metadata(settings, content)

        assert meta.og_image == "https://example.com/default-og.png"


class TestCanonicalURLBuilding:
    """Canonical URL building tests."""

    def test_build_canonical_url_basic(self) -> None:
        """Basic canonical URL building works."""
        result = build_canonical_url("https://example.com", "/page")

        assert result == "https://example.com/page"

    def test_build_canonical_url_strips_trailing_slash(self) -> None:
        """Trailing slash on base URL is handled."""
        result = build_canonical_url("https://example.com/", "/page")

        assert result == "https://example.com/page"

    def test_build_canonical_url_adds_leading_slash(self) -> None:
        """Leading slash on path is added if missing."""
        result = build_canonical_url("https://example.com", "page")

        assert result == "https://example.com/page"

    def test_build_canonical_url_root_path(self) -> None:
        """Root path works correctly."""
        result = build_canonical_url("https://example.com", "/")

        assert result == "https://example.com/"


class TestContentPathGeneration:
    """Content path generation tests."""

    def test_get_content_path_post(self, content: ContentItem) -> None:
        """Post content uses posts prefix."""
        routing = {"posts_prefix": "/blog"}

        path = get_content_path(content, routing)

        assert path == "/blog/test-post"

    def test_get_content_path_resource(self) -> None:
        """Resource content uses resources prefix."""
        resource = ContentItem(
            type="page",  # or resource_pdf
            slug="my-resource",
            title="Resource",
            owner_user_id=uuid4(),
        )
        routing = {"resources_prefix": "/files"}

        path = get_content_path(resource, routing)

        assert path == "/files/my-resource"

    def test_get_content_path_default_prefixes(self, content: ContentItem) -> None:
        """Default prefixes are used when not configured."""
        path = get_content_path(content, {})

        assert path == "/p/test-post"


class TestDescriptionTruncation:
    """Description truncation tests."""

    def test_short_text_unchanged(self) -> None:
        """Short text is not truncated."""
        text = "This is a short description."

        result = truncate_description(text)

        assert result == text
        assert "..." not in result

    def test_long_text_truncated(self) -> None:
        """Long text is truncated with ellipsis."""
        text = "A" * 200

        result = truncate_description(text, max_length=160)

        assert len(result) <= 163  # 160 + "..."
        assert result.endswith("...")

    def test_truncation_at_word_boundary(self) -> None:
        """Truncation breaks at word boundary."""
        text = (
            "This is a long sentence that should be truncated "
            "at a word boundary not in the middle of words"
        )

        result = truncate_description(text, max_length=50)

        assert not result.endswith("word...")  # Should break at space
        assert result.endswith("...")

    def test_exact_length_not_truncated(self) -> None:
        """Text exactly at limit is not truncated."""
        text = "x" * 160

        result = truncate_description(text, max_length=160)

        assert result == text


class TestPageMetadataModel:
    """PageMetadata model tests."""

    def test_default_values(self) -> None:
        """PageMetadata has sensible defaults."""
        meta = PageMetadata(
            title="Test",
            description="Test description",
            canonical_url="https://example.com/",
        )

        assert meta.robots == "index, follow"
        assert meta.og_type == "website"
        assert meta.twitter_card == "summary_large_image"

    def test_og_defaults_to_page_values(self) -> None:
        """OG values default to page values in to_meta_tags."""
        meta = PageMetadata(
            title="Page Title",
            description="Page description",
            canonical_url="https://example.com/page",
        )

        tags = meta.to_meta_tags()
        og_title = next(t for t in tags if t.property == "og:title")
        og_desc = next(t for t in tags if t.property == "og:description")

        assert og_title.content == "Page Title"
        assert og_desc.content == "Page description"


class TestImageInfo:
    """ImageInfo model tests."""

    def test_image_info_basic(self) -> None:
        """ImageInfo stores URL and alt."""
        info = ImageInfo(url="https://example.com/img.png", alt="Test image")

        assert info.url == "https://example.com/img.png"
        assert info.alt == "Test image"

    def test_image_info_default_alt(self) -> None:
        """ImageInfo has empty alt by default."""
        info = ImageInfo(url="https://example.com/img.png")

        assert info.alt == ""


class TestFactoryFunction:
    """Factory function tests."""

    def test_create_render_service(self) -> None:
        """create_render_service creates configured service."""
        service = create_render_service(
            base_url="https://test.com",
            default_og_image_url="https://test.com/og.png",
            routing_config={"posts_prefix": "/articles"},
        )

        assert service._base_url == "https://test.com"
        assert service._default_og_image == "https://test.com/og.png"
        assert service._routing["posts_prefix"] == "/articles"
