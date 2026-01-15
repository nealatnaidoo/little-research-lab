"""
Tests for Public SSR Routes (E1.2).

Test assertions:
- TA-0003: Public SSR reflects settings
- TA-0004: SSR meta snapshot (title, description, canonical, OG, Twitter)
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.api.routes.public_ssr import (
    _escape_html,
    render_meta_tags_html,
    render_ssr_page,
)
from src.components.render import PageMetadata, RenderService, create_render_service
from src.components.settings import SettingsService, get_default_settings
from src.domain.entities import ContentItem, SiteSettings

# --- Mock Repository ---


class MockSettingsRepo:
    """In-memory settings repository for testing."""

    def __init__(self, initial: SiteSettings | None = None) -> None:
        self._settings = initial

    def get(self) -> SiteSettings | None:
        return self._settings

    def save(self, settings: SiteSettings) -> SiteSettings:
        self._settings = settings
        return settings


class MockContentRepo:
    """In-memory content repository for testing."""

    def __init__(self) -> None:
        self._items: dict[str, ContentItem] = {}

    def add(self, content: ContentItem) -> None:
        self._items[f"{content.type}:{content.slug}"] = content

    def get_by_slug(self, slug: str, item_type: str) -> ContentItem | None:
        return self._items.get(f"{item_type}:{slug}")


# --- Fixtures ---


@pytest.fixture
def mock_settings_repo() -> MockSettingsRepo:
    """Empty settings repo."""
    return MockSettingsRepo()


@pytest.fixture
def mock_settings_with_data() -> MockSettingsRepo:
    """Settings repo with configured settings."""
    settings = SiteSettings(
        site_title="Test Site Title",
        site_subtitle="Test site description for meta tags",
        avatar_asset_id=None,
        theme="dark",
        social_links_json={
            "twitter": "https://twitter.com/test",
            "og_image": "https://example.com/og-image.png",
        },
        updated_at=datetime.now(UTC),
    )
    return MockSettingsRepo(settings)


@pytest.fixture
def mock_content_repo() -> MockContentRepo:
    """Content repo with test content."""
    repo = MockContentRepo()
    repo.add(
        ContentItem(
            id=uuid4(),
            type="post",
            slug="test-post",
            title="Test Post Title",
            summary="Test post summary for meta description",
            status="published",
            owner_user_id=uuid4(),
            published_at=datetime.now(UTC),
        )
    )
    repo.add(
        ContentItem(
            id=uuid4(),
            type="page",
            slug="about",
            title="About Page",
            summary="About page description",
            status="published",
            owner_user_id=uuid4(),
        )
    )
    repo.add(
        ContentItem(
            id=uuid4(),
            type="post",
            slug="draft-post",
            title="Draft Post",
            summary="This is a draft",
            status="draft",
            owner_user_id=uuid4(),
        )
    )
    return repo


@pytest.fixture
def render_service() -> RenderService:
    """RenderService for testing."""
    return create_render_service(
        base_url="https://example.com",
        default_og_image_url="https://example.com/default-og.png",
    )


# --- TA-0003: Public SSR Reflects Settings ---


class TestSSRReflectsSettings:
    """Test TA-0003: Settings changes are reflected in SSR output."""

    def test_homepage_title_from_settings(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Homepage title uses site_title from settings."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)

        assert metadata.title == "Test Site Title"
        assert settings.site_title in metadata.title

    def test_homepage_description_from_settings(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Homepage description uses site_subtitle from settings."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)

        assert settings.site_subtitle in metadata.description

    def test_og_site_name_from_settings(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """OG site name uses site_title from settings."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)

        assert metadata.og_site_name == settings.site_title

    def test_settings_update_reflected_in_ssr(
        self,
        mock_settings_repo: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Settings update is reflected in subsequent SSR renders."""
        service = SettingsService(repo=mock_settings_repo)

        # Initial render with defaults
        settings1 = service.get()
        metadata1 = render_service.build_homepage_metadata(settings1)
        initial_title = metadata1.title

        # Update settings
        service.update(
            {
                "site_title": "New Site Title",
                "site_subtitle": "New site description",
            }
        )

        # Re-render with updated settings
        settings2 = service.get()
        metadata2 = render_service.build_homepage_metadata(settings2)

        assert metadata2.title == "New Site Title"
        assert metadata2.title != initial_title

    def test_default_settings_used_when_empty(
        self,
        mock_settings_repo: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Default settings are used when DB is empty."""
        service = SettingsService(repo=mock_settings_repo)
        settings = service.get()

        defaults = get_default_settings()
        metadata = render_service.build_homepage_metadata(settings)

        assert settings.site_title == defaults.site_title
        assert metadata.title == defaults.site_title


# --- TA-0004: SSR Meta Snapshot ---


class TestSSRMetaSnapshot:
    """Test TA-0004: Complete SSR metadata generation."""

    def test_homepage_has_all_required_meta(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Homepage metadata includes all required fields."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)

        # Required fields
        assert metadata.title
        assert metadata.description
        assert metadata.canonical_url
        assert metadata.robots

        # OG fields
        assert metadata.og_title
        assert metadata.og_description
        assert metadata.og_type == "website"
        assert metadata.og_url

        # Twitter fields
        assert metadata.twitter_card

    def test_content_page_has_article_og_type(
        self,
        mock_settings_with_data: MockSettingsRepo,
        mock_content_repo: MockContentRepo,
        render_service: RenderService,
    ) -> None:
        """Content page has og:type = article."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()
        content = mock_content_repo.get_by_slug("test-post", "post")

        assert content is not None
        metadata = render_service.build_content_metadata(settings, content)

        assert metadata.og_type == "article"

    def test_content_title_includes_site_name(
        self,
        mock_settings_with_data: MockSettingsRepo,
        mock_content_repo: MockContentRepo,
        render_service: RenderService,
    ) -> None:
        """Content page title includes content title and site name."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()
        content = mock_content_repo.get_by_slug("test-post", "post")

        assert content is not None
        metadata = render_service.build_content_metadata(settings, content)

        assert content.title in metadata.title
        assert settings.site_title in metadata.title

    def test_content_uses_summary_for_description(
        self,
        mock_settings_with_data: MockSettingsRepo,
        mock_content_repo: MockContentRepo,
        render_service: RenderService,
    ) -> None:
        """Content page uses content summary for meta description."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()
        content = mock_content_repo.get_by_slug("test-post", "post")

        assert content is not None
        metadata = render_service.build_content_metadata(settings, content)

        assert content.summary in metadata.description

    def test_canonical_url_built_correctly(
        self,
        mock_settings_with_data: MockSettingsRepo,
        mock_content_repo: MockContentRepo,
        render_service: RenderService,
    ) -> None:
        """Canonical URL is built correctly for content."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()
        content = mock_content_repo.get_by_slug("test-post", "post")

        assert content is not None
        metadata = render_service.build_content_metadata(settings, content)

        assert "https://example.com" in metadata.canonical_url
        assert content.slug in metadata.canonical_url


# --- HTML Rendering ---


class TestHTMLRendering:
    """Test HTML rendering utilities."""

    def test_escape_html_special_chars(self) -> None:
        """HTML special characters are escaped."""
        assert _escape_html("<script>") == "&lt;script&gt;"
        assert _escape_html('"test"') == "&quot;test&quot;"
        assert _escape_html("a & b") == "a &amp; b"
        assert _escape_html("it's") == "it&#x27;s"

    def test_render_meta_tags_includes_title(self) -> None:
        """Rendered HTML includes title tag."""
        metadata = PageMetadata(
            title="Test Title",
            description="Test description",
            canonical_url="https://example.com/",
        )

        html = render_meta_tags_html(metadata)

        assert "<title>Test Title</title>" in html

    def test_render_meta_tags_includes_description(self) -> None:
        """Rendered HTML includes meta description."""
        metadata = PageMetadata(
            title="Test Title",
            description="Test description",
            canonical_url="https://example.com/",
        )

        html = render_meta_tags_html(metadata)

        assert 'name="description"' in html
        assert "Test description" in html

    def test_render_meta_tags_includes_og_tags(self) -> None:
        """Rendered HTML includes OpenGraph tags."""
        metadata = PageMetadata(
            title="Test Title",
            description="Test description",
            canonical_url="https://example.com/",
            og_title="OG Title",
            og_image="https://example.com/og.png",
        )

        html = render_meta_tags_html(metadata)

        assert 'property="og:title"' in html
        assert 'property="og:image"' in html

    def test_render_meta_tags_includes_twitter_tags(self) -> None:
        """Rendered HTML includes Twitter Card tags."""
        metadata = PageMetadata(
            title="Test Title",
            description="Test description",
            canonical_url="https://example.com/",
            twitter_card="summary_large_image",
        )

        html = render_meta_tags_html(metadata)

        assert 'name="twitter:card"' in html
        assert "summary_large_image" in html

    def test_render_meta_tags_includes_canonical(self) -> None:
        """Rendered HTML includes canonical link."""
        metadata = PageMetadata(
            title="Test Title",
            description="Test description",
            canonical_url="https://example.com/page",
        )

        html = render_meta_tags_html(metadata)

        assert 'rel="canonical"' in html
        assert "https://example.com/page" in html

    def test_render_ssr_page_structure(self) -> None:
        """SSR page has proper HTML structure."""
        metadata = PageMetadata(
            title="Test Title",
            description="Test description",
            canonical_url="https://example.com/",
        )

        html = render_ssr_page(metadata, "<p>Content</p>")

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "<p>Content</p>" in html


# --- Content SSR ---


class TestContentSSR:
    """Test content page SSR."""

    def test_published_content_rendered(
        self,
        mock_settings_with_data: MockSettingsRepo,
        mock_content_repo: MockContentRepo,
        render_service: RenderService,
    ) -> None:
        """Published content is rendered correctly."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()
        content = mock_content_repo.get_by_slug("test-post", "post")

        assert content is not None
        assert content.status == "published"

        metadata = render_service.build_content_metadata(settings, content)
        html = render_ssr_page(metadata, f"<h1>{content.title}</h1>")

        assert content.title in html
        assert f"<title>{content.title}" in html

    def test_page_content_rendered(
        self,
        mock_settings_with_data: MockSettingsRepo,
        mock_content_repo: MockContentRepo,
        render_service: RenderService,
    ) -> None:
        """Page content (about, etc.) is rendered correctly."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()
        content = mock_content_repo.get_by_slug("about", "page")

        assert content is not None
        metadata = render_service.build_content_metadata(settings, content)

        assert "About Page" in metadata.title


# --- OG Image Resolution ---


class TestOGImageResolution:
    """Test OG image resolution (TA-0005)."""

    def test_settings_og_image_used(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Settings OG image is used when available."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        # Settings has og_image in social_links_json
        metadata = render_service.build_homepage_metadata(settings)

        assert metadata.og_image == "https://example.com/og-image.png"

    def test_default_og_image_used_when_no_settings(
        self,
        mock_settings_repo: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Default OG image is used when settings don't have one."""
        service = SettingsService(repo=mock_settings_repo)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)

        assert metadata.og_image == "https://example.com/default-og.png"


# --- Resource(PDF) SSR Tests (E3.2) ---


class TestResourcePDFSSR:
    """Tests for Resource(PDF) SSR (TA-0016, TA-0017, TA-0018)."""

    def test_resource_pdf_embed_html_structure(self) -> None:
        """TA-0017: PDF embed HTML has proper structure with fallback."""
        from src.api.routes.public_ssr import _render_pdf_embed_html

        html = _render_pdf_embed_html(
            pdf_url="https://example.com/api/public/assets/123/latest",
            download_url="https://example.com/api/public/assets/123/latest?download=1",
            filename="test-doc.pdf",
        )

        # Has PDF embed object tag
        assert "<object" in html
        assert 'type="application/pdf"' in html
        assert 'data="https://example.com/api/public/assets/123/latest"' in html

        # Has fallback content for iOS/Safari
        assert "pdf-fallback" in html
        assert "doesn't support embedded PDFs" in html

        # Has "Open in new tab" link (TA-0017 fallback)
        assert 'target="_blank"' in html
        assert "Open PDF in New Tab" in html

        # Has download link (TA-0018)
        assert 'download="test-doc.pdf"' in html
        assert "Download PDF" in html

    def test_resource_pdf_embed_has_download_section(self) -> None:
        """TA-0018: PDF embed has persistent download section."""
        from src.api.routes.public_ssr import _render_pdf_embed_html

        html = _render_pdf_embed_html(
            pdf_url="https://example.com/pdf",
            download_url="https://example.com/pdf?download=1",
            filename="report.pdf",
        )

        # Sticky download bar always visible below embed
        assert "pdf-download-bar" in html
        assert "report.pdf" in html  # Filename displayed in download bar

    def test_resource_pdf_embed_escapes_special_chars(self) -> None:
        """PDF embed HTML escapes special characters for security."""
        from src.api.routes.public_ssr import _render_pdf_embed_html

        html = _render_pdf_embed_html(
            pdf_url="https://example.com/pdf?a=1&b=2",
            download_url="https://example.com/pdf?download=1",
            filename="report<script>.pdf",
        )

        # Ampersand escaped
        assert "&amp;" in html or "&b=2" not in html
        # Script tag escaped
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_resource_pdf_metadata_built_correctly(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """TA-0016: Resource PDF has proper metadata for crawlers."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        # Create a resource_pdf content item
        resource_content = ContentItem(
            id=uuid4(),
            type="resource_pdf",
            slug="annual-report",
            title="2024 Annual Report",
            summary="Company annual report for fiscal year 2024",
            status="published",
            owner_user_id=uuid4(),
            published_at=datetime.now(UTC),
        )

        metadata = render_service.build_content_metadata(settings, resource_content)

        # Has proper metadata
        assert "2024 Annual Report" in metadata.title
        assert "annual report for fiscal year 2024" in metadata.description
        assert "annual-report" in metadata.canonical_url
        assert metadata.og_type == "article"

    def test_resource_ssr_page_renders_with_content(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Resource SSR page renders full HTML with content."""
        from src.api.routes.public_ssr import _render_pdf_embed_html

        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        resource_content = ContentItem(
            id=uuid4(),
            type="resource_pdf",
            slug="research-paper",
            title="Research Paper Title",
            summary="Abstract of the research paper",
            status="published",
            owner_user_id=uuid4(),
        )

        metadata = render_service.build_content_metadata(settings, resource_content)

        pdf_embed = _render_pdf_embed_html(
            pdf_url="https://example.com/pdf",
            download_url="https://example.com/pdf?download=1",
            filename="research-paper.pdf",
        )

        body = f"""
        <article class="resource-pdf">
            <h1>{resource_content.title}</h1>
            <p>{resource_content.summary}</p>
            {pdf_embed}
        </article>
        """

        html = render_ssr_page(metadata, body)

        # Has proper structure
        assert "<!DOCTYPE html>" in html
        assert "<title>Research Paper Title" in html
        assert '<meta name="description"' in html
        assert '<article class="resource-pdf">' in html
        assert "Research Paper Title" in html
        assert "Abstract of the research paper" in html
        assert "<object" in html


class TestResourcePDFIntegration:
    """Integration-style tests for Resource PDF route."""

    @pytest.fixture
    def resource_content_repo(self) -> MockContentRepo:
        """Content repo with resource_pdf content."""
        repo = MockContentRepo()

        # Published resource
        repo.add(
            ContentItem(
                id=uuid4(),
                type="resource_pdf",
                slug="published-report",
                title="Published Report",
                summary="A published PDF report",
                status="published",
                owner_user_id=uuid4(),
                published_at=datetime.now(UTC),
            )
        )

        # Draft resource (should not be served)
        repo.add(
            ContentItem(
                id=uuid4(),
                type="resource_pdf",
                slug="draft-report",
                title="Draft Report",
                summary="A draft PDF report",
                status="draft",
                owner_user_id=uuid4(),
            )
        )

        return repo

    def test_published_resource_found(
        self,
        resource_content_repo: MockContentRepo,
    ) -> None:
        """Published resource is found by slug."""
        content = resource_content_repo.get_by_slug("published-report", "resource_pdf")
        assert content is not None
        assert content.status == "published"

    def test_draft_resource_exists_but_not_servable(
        self,
        resource_content_repo: MockContentRepo,
    ) -> None:
        """Draft resource exists but should not be served publicly."""
        content = resource_content_repo.get_by_slug("draft-report", "resource_pdf")
        assert content is not None
        assert content.status == "draft"  # Should be filtered out in route

    def test_nonexistent_resource_returns_none(
        self,
        resource_content_repo: MockContentRepo,
    ) -> None:
        """Nonexistent resource returns None."""
        content = resource_content_repo.get_by_slug("does-not-exist", "resource_pdf")
        assert content is None


# --- Sitemap Tests (R2, T-0046) ---


class TestSitemapXML:
    """Tests for sitemap.xml endpoint (R2, T-0046)."""

    def test_sitemap_includes_published_content(self) -> None:
        """TA-0000: Sitemap includes published posts."""
        from src.api.routes.public_ssr import _render_sitemap_xml
        from src.components.C2_PublicTemplates import SitemapEntry

        entries = [
            SitemapEntry(loc="https://example.com/p/test-post", lastmod="2024-01-15"),
        ]
        xml = _render_sitemap_xml(entries)

        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert "<urlset" in xml
        assert "<loc>https://example.com/p/test-post</loc>" in xml
        assert "<lastmod>2024-01-15</lastmod>" in xml

    def test_sitemap_xml_structure(self) -> None:
        """Sitemap XML has valid structure."""
        from src.api.routes.public_ssr import _render_sitemap_xml
        from src.components.C2_PublicTemplates import SitemapEntry

        entries = [
            SitemapEntry(
                loc="https://example.com/",
                changefreq="daily",
                priority=1.0,
            ),
            SitemapEntry(
                loc="https://example.com/p/post-1",
                lastmod="2024-06-15",
                changefreq="weekly",
                priority=0.8,
            ),
        ]
        xml = _render_sitemap_xml(entries)

        # Valid XML declaration
        assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        # Proper namespace
        assert 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' in xml
        # All entries present
        assert xml.count("<url>") == 2
        assert xml.count("</url>") == 2
        # Priority formatting
        assert "<priority>1.0</priority>" in xml
        assert "<priority>0.8</priority>" in xml

    def test_sitemap_excludes_draft_content(self) -> None:
        """R2: Sitemap must exclude draft content."""
        from datetime import UTC, datetime

        from src.components.C2_PublicTemplates import filter_sitemap_entries

        now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

        # Entries: (slug, type, published_at, updated_at)
        # Draft has no published_at
        entries = [
            ("published-post", "post", now, now),
            ("draft-post", "post", None, now),  # Draft - no published_at
        ]

        result = filter_sitemap_entries(entries, "https://example.com", now)

        assert len(result) == 1
        assert "published-post" in result[0].loc
        assert all("draft-post" not in e.loc for e in result)

    def test_sitemap_excludes_future_dated_content(self) -> None:
        """R2: Sitemap must exclude content with future publish dates."""
        from datetime import UTC, datetime, timedelta

        from src.components.C2_PublicTemplates import filter_sitemap_entries

        now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        future = now + timedelta(days=7)

        entries = [
            ("current-post", "post", now, now),
            ("future-post", "post", future, future),  # Future dated
        ]

        result = filter_sitemap_entries(entries, "https://example.com", now)

        assert len(result) == 1
        assert "current-post" in result[0].loc
        assert all("future-post" not in e.loc for e in result)

    def test_sitemap_escapes_special_characters(self) -> None:
        """Sitemap XML properly escapes special characters."""
        from src.api.routes.public_ssr import _render_sitemap_xml
        from src.components.C2_PublicTemplates import SitemapEntry

        entries = [
            SitemapEntry(loc="https://example.com/p/test&post"),
        ]
        xml = _render_sitemap_xml(entries)

        # & should be escaped to &amp;
        assert "&amp;" in xml
        assert "test&post" not in xml  # Raw & should not appear


# --- Social Meta Tags Tests (TA-0072, TA-0073) ---


class TestTwitterCardMetaTags:
    """Test TA-0072: Twitter Card meta tags in SSR output."""

    def test_twitter_card_type_present(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Twitter card type is present in rendered HTML."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)
        html = render_meta_tags_html(metadata)

        assert 'name="twitter:card"' in html
        assert "summary_large_image" in html or "summary" in html

    def test_twitter_title_present(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Twitter title is present in rendered HTML."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)
        html = render_meta_tags_html(metadata)

        assert 'name="twitter:title"' in html
        assert settings.site_title in html

    def test_twitter_description_present(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Twitter description is present in rendered HTML."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)
        html = render_meta_tags_html(metadata)

        assert 'name="twitter:description"' in html

    def test_twitter_image_present_when_available(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Twitter image is present when OG image available."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        # Settings fixture has og_image
        metadata = render_service.build_homepage_metadata(settings)
        html = render_meta_tags_html(metadata)

        assert 'name="twitter:image"' in html
        assert "og-image.png" in html

    def test_twitter_card_content_page(
        self,
        mock_settings_with_data: MockSettingsRepo,
        mock_content_repo: MockContentRepo,
        render_service: RenderService,
    ) -> None:
        """Content page has proper Twitter card tags."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()
        content = mock_content_repo.get_by_slug("test-post", "post")

        assert content is not None
        metadata = render_service.build_content_metadata(settings, content)
        html = render_meta_tags_html(metadata)

        # Twitter card should use content title
        assert 'name="twitter:title"' in html
        assert content.title in html

    def test_twitter_card_summary_large_image_with_image(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Twitter card is summary_large_image when image available."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)

        # Settings has og_image, so should be summary_large_image
        assert metadata.twitter_card == "summary_large_image"


class TestOpenGraphMetaTags:
    """Test TA-0073: OpenGraph meta tags in SSR output."""

    def test_og_type_present(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """og:type is present in rendered HTML."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)
        html = render_meta_tags_html(metadata)

        assert 'property="og:type"' in html
        assert "website" in html

    def test_og_type_article_for_content(
        self,
        mock_settings_with_data: MockSettingsRepo,
        mock_content_repo: MockContentRepo,
        render_service: RenderService,
    ) -> None:
        """og:type is 'article' for content pages."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()
        content = mock_content_repo.get_by_slug("test-post", "post")

        assert content is not None
        metadata = render_service.build_content_metadata(settings, content)
        html = render_meta_tags_html(metadata)

        assert 'property="og:type"' in html
        # Content page should be article
        assert 'content="article"' in html

    def test_og_title_present(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """og:title is present in rendered HTML."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)
        html = render_meta_tags_html(metadata)

        assert 'property="og:title"' in html
        assert settings.site_title in html

    def test_og_description_present(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """og:description is present in rendered HTML."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)
        html = render_meta_tags_html(metadata)

        assert 'property="og:description"' in html

    def test_og_url_present(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """og:url is present in rendered HTML."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)
        html = render_meta_tags_html(metadata)

        assert 'property="og:url"' in html
        assert "https://example.com" in html

    def test_og_image_present_when_available(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """og:image is present when image available."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)
        html = render_meta_tags_html(metadata)

        assert 'property="og:image"' in html
        assert "og-image.png" in html

    def test_og_site_name_present(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """og:site_name is present in rendered HTML."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)
        html = render_meta_tags_html(metadata)

        assert 'property="og:site_name"' in html
        assert settings.site_title in html

    def test_og_content_page_uses_content_title(
        self,
        mock_settings_with_data: MockSettingsRepo,
        mock_content_repo: MockContentRepo,
        render_service: RenderService,
    ) -> None:
        """Content page OG title uses content title."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()
        content = mock_content_repo.get_by_slug("test-post", "post")

        assert content is not None
        metadata = render_service.build_content_metadata(settings, content)

        assert metadata.og_title == content.title


class TestSocialMetaTagsIntegration:
    """Integration tests for social meta tags in SSR pages."""

    def test_full_ssr_page_has_all_social_tags(
        self,
        mock_settings_with_data: MockSettingsRepo,
        mock_content_repo: MockContentRepo,
        render_service: RenderService,
    ) -> None:
        """Full SSR page contains all required social meta tags."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()
        content = mock_content_repo.get_by_slug("test-post", "post")

        assert content is not None
        metadata = render_service.build_content_metadata(settings, content)
        html = render_ssr_page(metadata, f"<h1>{content.title}</h1>")

        # All Twitter Card tags
        assert 'name="twitter:card"' in html
        assert 'name="twitter:title"' in html
        assert 'name="twitter:description"' in html
        assert 'name="twitter:image"' in html

        # All OpenGraph tags
        assert 'property="og:type"' in html
        assert 'property="og:title"' in html
        assert 'property="og:description"' in html
        assert 'property="og:url"' in html
        assert 'property="og:image"' in html
        assert 'property="og:site_name"' in html

    def test_resource_pdf_has_social_tags(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Resource PDF page has proper social meta tags."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        resource_content = ContentItem(
            id=uuid4(),
            type="resource_pdf",
            slug="report-2024",
            title="Annual Report 2024",
            summary="Company financial report",
            status="published",
            owner_user_id=uuid4(),
            published_at=datetime.now(UTC),
        )

        metadata = render_service.build_content_metadata(settings, resource_content)
        html = render_ssr_page(metadata, "<article>PDF content</article>")

        # Resource PDF should have article type
        assert 'property="og:type"' in html
        assert 'content="article"' in html

        # Twitter and OG tags should contain resource title
        assert "Annual Report 2024" in html

    def test_homepage_og_type_is_website(
        self,
        mock_settings_with_data: MockSettingsRepo,
        render_service: RenderService,
    ) -> None:
        """Homepage og:type is 'website' not 'article'."""
        service = SettingsService(repo=mock_settings_with_data)
        settings = service.get()

        metadata = render_service.build_homepage_metadata(settings)

        assert metadata.og_type == "website"

    def test_social_tags_escaped_properly(
        self,
        render_service: RenderService,
    ) -> None:
        """Social meta tags escape special characters properly."""
        # Create settings with special characters
        settings = SiteSettings(
            site_title="Test & Site <Title>",
            site_subtitle='Description with "quotes" & ampersands',
            avatar_asset_id=None,
            theme="dark",
            social_links_json={},
            updated_at=datetime.now(UTC),
        )

        metadata = render_service.build_homepage_metadata(settings)
        html = render_meta_tags_html(metadata)

        # Should not have unescaped special chars
        assert "<Title>" not in html  # Should be &lt;Title&gt;
        assert "&lt;" in html or "Test &amp; Site" in html
        assert '"quotes"' not in html or "&quot;" in html
