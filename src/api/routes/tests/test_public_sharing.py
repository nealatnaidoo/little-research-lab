"""
Tests for public sharing API endpoint.

Spec refs: E15.2
Test assertions: TA-0070, TA-0071
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.components.content.models import ContentOutput
from src.components.settings.models import GetSettingsOutput
from src.domain.entities import ContentItem, SiteSettings


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_content() -> ContentItem:
    """Create mock content item."""
    return ContentItem(
        id=uuid4(),
        slug="test-article",
        title="Test Article Title",
        summary="This is a test article summary.",
        type="post",
        status="published",
        owner_user_id=uuid4(),
        blocks=[],
    )


@pytest.fixture
def mock_settings() -> SiteSettings:
    """Create mock site settings."""
    return SiteSettings(
        site_title="Test Site",
        site_subtitle="Test Subtitle",
        theme="light",
        social_links_json={"base_url": "https://example.com"},
    )


class TestGenerateShareUrl:
    """Tests for POST /api/public/share/generate endpoint."""

    def test_generate_twitter_share_url(
        self, client: TestClient, mock_content: ContentItem, mock_settings: SiteSettings
    ) -> None:
        """Generates Twitter share URL successfully."""
        with patch("src.api.routes.public_sharing.run_get") as mock_get_content, patch(
            "src.api.routes.public_sharing.run_get_settings"
        ) as mock_get_settings:
            mock_get_content.return_value = ContentOutput(
                content=mock_content, success=True, errors=[]
            )
            mock_get_settings.return_value = GetSettingsOutput(settings=mock_settings)

            response = client.post(
                "/api/public/share/generate",
                json={"content_id": str(mock_content.id), "platform": "twitter"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "share_url" in data
            assert "twitter.com" in data["share_url"]
            assert data["platform"] == "twitter"
            assert data["utm_source"] == "twitter"
            assert data["utm_medium"] == "social"
            assert data["utm_campaign"] == "test-article"

    def test_generate_linkedin_share_url(
        self, client: TestClient, mock_content: ContentItem, mock_settings: SiteSettings
    ) -> None:
        """Generates LinkedIn share URL successfully."""
        with patch("src.api.routes.public_sharing.run_get") as mock_get_content, patch(
            "src.api.routes.public_sharing.run_get_settings"
        ) as mock_get_settings:
            mock_get_content.return_value = ContentOutput(
                content=mock_content, success=True, errors=[]
            )
            mock_get_settings.return_value = GetSettingsOutput(settings=mock_settings)

            response = client.post(
                "/api/public/share/generate",
                json={"content_id": str(mock_content.id), "platform": "linkedin"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "linkedin.com" in data["share_url"]
            assert data["utm_source"] == "linkedin"

    def test_generate_facebook_share_url(
        self, client: TestClient, mock_content: ContentItem, mock_settings: SiteSettings
    ) -> None:
        """Generates Facebook share URL successfully."""
        with patch("src.api.routes.public_sharing.run_get") as mock_get_content, patch(
            "src.api.routes.public_sharing.run_get_settings"
        ) as mock_get_settings:
            mock_get_content.return_value = ContentOutput(
                content=mock_content, success=True, errors=[]
            )
            mock_get_settings.return_value = GetSettingsOutput(settings=mock_settings)

            response = client.post(
                "/api/public/share/generate",
                json={"content_id": str(mock_content.id), "platform": "facebook"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "facebook.com" in data["share_url"]
            assert data["utm_source"] == "facebook"

    def test_generate_native_share_url(
        self, client: TestClient, mock_content: ContentItem, mock_settings: SiteSettings
    ) -> None:
        """Generates native share URL successfully."""
        with patch("src.api.routes.public_sharing.run_get") as mock_get_content, patch(
            "src.api.routes.public_sharing.run_get_settings"
        ) as mock_get_settings:
            mock_get_content.return_value = ContentOutput(
                content=mock_content, success=True, errors=[]
            )
            mock_get_settings.return_value = GetSettingsOutput(settings=mock_settings)

            response = client.post(
                "/api/public/share/generate",
                json={"content_id": str(mock_content.id), "platform": "native"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "example.com" in data["share_url"]
            assert data["utm_source"] == "share"

    def test_content_not_found(self, client: TestClient, mock_settings: SiteSettings) -> None:
        """Returns 404 when content not found."""
        with patch("src.api.routes.public_sharing.run_get") as mock_get_content, patch(
            "src.api.routes.public_sharing.run_get_settings"
        ) as mock_get_settings:
            mock_get_content.return_value = ContentOutput(
                content=None, success=False, errors=[]
            )
            mock_get_settings.return_value = GetSettingsOutput(settings=mock_settings)

            response = client.post(
                "/api/public/share/generate",
                json={"content_id": str(uuid4()), "platform": "twitter"},
            )

            assert response.status_code == 404

    def test_invalid_platform(self, client: TestClient) -> None:
        """Returns 422 for invalid platform."""
        response = client.post(
            "/api/public/share/generate",
            json={"content_id": str(uuid4()), "platform": "invalid"},
        )

        assert response.status_code == 422

    def test_missing_content_id(self, client: TestClient) -> None:
        """Returns 422 when content_id missing."""
        response = client.post(
            "/api/public/share/generate",
            json={"platform": "twitter"},
        )

        assert response.status_code == 422

    def test_resource_pdf_uses_r_prefix(
        self, client: TestClient, mock_settings: SiteSettings
    ) -> None:
        """Uses /r prefix for resource_pdf content type."""
        mock_resource = ContentItem(
            id=uuid4(),
            slug="test-pdf",
            title="Test PDF",
            summary="A PDF resource",
            type="resource_pdf",
            status="published",
            owner_user_id=uuid4(),
            blocks=[],
        )

        with patch("src.api.routes.public_sharing.run_get") as mock_get_content, patch(
            "src.api.routes.public_sharing.run_get_settings"
        ) as mock_get_settings:
            mock_get_content.return_value = ContentOutput(
                content=mock_resource, success=True, errors=[]
            )
            mock_get_settings.return_value = GetSettingsOutput(settings=mock_settings)

            response = client.post(
                "/api/public/share/generate",
                json={"content_id": str(mock_resource.id), "platform": "twitter"},
            )

            assert response.status_code == 200
            data = response.json()
            # The URL should contain /r/ for resources
            from urllib.parse import unquote
            decoded_url = unquote(data["share_url"])
            assert "/r/test-pdf" in decoded_url


class TestGetSharePlatforms:
    """Tests for GET /api/public/share/platforms endpoint."""

    def test_get_platforms(self, client: TestClient) -> None:
        """Returns list of available platforms."""
        response = client.get("/api/public/share/platforms")

        assert response.status_code == 200
        data = response.json()
        assert "platforms" in data
        assert "twitter" in data["platforms"]
        assert "linkedin" in data["platforms"]
        assert "facebook" in data["platforms"]
        assert "native" in data["platforms"]
