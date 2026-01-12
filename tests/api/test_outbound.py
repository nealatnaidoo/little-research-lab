"""
Tests for Outbound Click Measurement Route (E6.2).

Test assertions:
- TA-0038: Outbound clicks are tracked and UTM params preserved
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import outbound
from src.api.routes.outbound import (
    is_safe_url,
    preserve_utm_params,
    reset_event_recorder,
)

# --- Test Setup ---


@pytest.fixture(autouse=True)
def reset_recorder() -> None:
    """Reset event recorder before each test."""
    reset_event_recorder()


@pytest.fixture
def app() -> FastAPI:
    """Test FastAPI app with outbound routes."""
    app = FastAPI()
    app.include_router(outbound.router, prefix="/out")
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Test client (no redirects)."""
    return TestClient(app, follow_redirects=False)


# --- URL Validation Tests ---


class TestUrlValidation:
    """Test URL safety validation."""

    def test_valid_https_url(self) -> None:
        """HTTPS URLs are valid."""
        assert is_safe_url("https://example.com/page") is True

    def test_valid_http_url(self) -> None:
        """HTTP URLs are valid."""
        assert is_safe_url("http://example.com/page") is True

    def test_invalid_javascript_url(self) -> None:
        """javascript: URLs are rejected."""
        assert is_safe_url("javascript:alert(1)") is False

    def test_invalid_data_url(self) -> None:
        """data: URLs are rejected."""
        assert is_safe_url("data:text/html,<script>") is False

    def test_invalid_no_scheme(self) -> None:
        """URLs without scheme are rejected."""
        assert is_safe_url("//example.com/page") is False

    def test_invalid_relative_path(self) -> None:
        """Relative paths are rejected."""
        assert is_safe_url("/local/path") is False

    def test_invalid_localhost(self) -> None:
        """localhost URLs are rejected."""
        assert is_safe_url("http://localhost/path") is False
        assert is_safe_url("http://127.0.0.1/path") is False

    def test_invalid_empty(self) -> None:
        """Empty URLs are rejected."""
        assert is_safe_url("") is False
        assert is_safe_url(None) is False  # type: ignore[arg-type]


# --- UTM Preservation Tests ---


class TestUtmPreservation:
    """Test UTM parameter preservation."""

    def test_adds_utm_params(self) -> None:
        """UTM params are added to URL."""
        result = preserve_utm_params(
            "https://example.com/page",
            {"utm_source": "newsletter", "utm_medium": "email"},
        )

        assert "utm_source=newsletter" in result
        assert "utm_medium=email" in result

    def test_preserves_existing_query(self) -> None:
        """Existing query params are preserved."""
        result = preserve_utm_params(
            "https://example.com/page?ref=123",
            {"utm_source": "google"},
        )

        assert "ref=123" in result
        assert "utm_source=google" in result

    def test_no_override_existing_utm(self) -> None:
        """Existing UTM params are not overridden."""
        result = preserve_utm_params(
            "https://example.com/page?utm_source=existing",
            {"utm_source": "new", "utm_medium": "email"},
        )

        assert "utm_source=existing" in result
        assert "utm_medium=email" in result
        # Should not have utm_source=new
        assert result.count("utm_source=") == 1

    def test_empty_params(self) -> None:
        """Empty params don't modify URL."""
        result = preserve_utm_params("https://example.com/page", {})
        assert result == "https://example.com/page"

    def test_preserves_fragment(self) -> None:
        """Fragment is preserved."""
        result = preserve_utm_params(
            "https://example.com/page#section",
            {"utm_source": "test"},
        )

        assert "#section" in result


# --- TA-0038: Outbound Click Tracking Tests ---


class TestOutboundClickTracking:
    """Test TA-0038: Outbound click tracking."""

    def test_redirects_to_target(self, client: TestClient) -> None:
        """Redirects to target URL."""
        response = client.get(
            "/out/go",
            params={"url": "https://example.com/external"},
        )

        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com/external"

    def test_records_click_event(self, client: TestClient) -> None:
        """Click event is recorded."""
        client.get(
            "/out/go",
            params={"url": "https://example.com/external"},
        )

        recorder = outbound.get_event_recorder()
        events = recorder.get_events()

        assert len(events) == 1
        assert events[0]["event_type"] == "outbound_click"
        assert events[0]["target_url"] == "https://example.com/external"

    def test_records_link_id(self, client: TestClient) -> None:
        """Link ID is recorded."""
        client.get(
            "/out/go",
            params={
                "url": "https://example.com/external",
                "link_id": "newsletter-cta-1",
            },
        )

        recorder = outbound.get_event_recorder()
        events = recorder.get_events()

        assert events[0]["link_id"] == "newsletter-cta-1"

    def test_preserves_utm_in_redirect(self, client: TestClient) -> None:
        """UTM params from request are preserved in redirect URL."""
        response = client.get(
            "/out/go",
            params={
                "url": "https://example.com/external",
                "utm_source": "newsletter",
                "utm_medium": "email",
            },
        )

        location = response.headers["location"]
        assert "utm_source=newsletter" in location
        assert "utm_medium=email" in location

    def test_records_utm_params(self, client: TestClient) -> None:
        """UTM params are recorded in event."""
        client.get(
            "/out/go",
            params={
                "url": "https://example.com/external",
                "utm_source": "google",
                "utm_campaign": "summer",
            },
        )

        recorder = outbound.get_event_recorder()
        events = recorder.get_events()

        assert events[0]["utm_params"]["utm_source"] == "google"
        assert events[0]["utm_params"]["utm_campaign"] == "summer"

    def test_records_referrer(self, client: TestClient) -> None:
        """Referrer header is recorded."""
        client.get(
            "/out/go",
            params={"url": "https://example.com/external"},
            headers={"Referer": "https://mysite.com/post/123"},
        )

        recorder = outbound.get_event_recorder()
        events = recorder.get_events()

        assert events[0]["referrer"] == "https://mysite.com/post/123"

    def test_records_timestamp(self, client: TestClient) -> None:
        """Timestamp is recorded."""
        client.get(
            "/out/go",
            params={"url": "https://example.com/external"},
        )

        recorder = outbound.get_event_recorder()
        events = recorder.get_events()

        assert "timestamp" in events[0]


class TestOutboundUrlValidation:
    """Test URL validation in endpoints."""

    def test_rejects_unsafe_url(self, client: TestClient) -> None:
        """Unsafe URLs are rejected."""
        response = client.get(
            "/out/go",
            params={"url": "javascript:alert(1)"},
        )

        assert response.status_code == 400

    def test_rejects_localhost(self, client: TestClient) -> None:
        """localhost URLs are rejected."""
        response = client.get(
            "/out/go",
            params={"url": "http://localhost/admin"},
        )

        assert response.status_code == 400

    def test_rejects_internal_ip(self, client: TestClient) -> None:
        """Internal IP URLs are rejected."""
        response = client.get(
            "/out/go",
            params={"url": "http://127.0.0.1/admin"},
        )

        assert response.status_code == 400


class TestNamedLinkTracking:
    """Test named link tracking endpoint."""

    def test_redirects_with_link_id(self, client: TestClient) -> None:
        """Redirects with link ID path param."""
        response = client.get(
            "/out/click/newsletter-signup",
            params={"url": "https://example.com/signup"},
        )

        assert response.status_code == 302

    def test_records_link_id_from_path(self, client: TestClient) -> None:
        """Link ID from path is recorded."""
        client.get(
            "/out/click/cta-button-1",
            params={"url": "https://example.com/page"},
        )

        recorder = outbound.get_event_recorder()
        events = recorder.get_events()

        assert events[0]["link_id"] == "cta-button-1"

    def test_preserves_utm_in_named_link(self, client: TestClient) -> None:
        """UTM params preserved in named link redirect."""
        response = client.get(
            "/out/click/promo",
            params={
                "url": "https://example.com/offer",
                "utm_source": "twitter",
            },
        )

        location = response.headers["location"]
        assert "utm_source=twitter" in location


class TestAllUtmParams:
    """Test all UTM parameters are supported."""

    def test_all_utm_params_preserved(self, client: TestClient) -> None:
        """All 5 UTM params are preserved."""
        response = client.get(
            "/out/go",
            params={
                "url": "https://example.com/page",
                "utm_source": "google",
                "utm_medium": "cpc",
                "utm_campaign": "summer_sale",
                "utm_content": "banner1",
                "utm_term": "shoes",
            },
        )

        location = response.headers["location"]
        assert "utm_source=google" in location
        assert "utm_medium=cpc" in location
        assert "utm_campaign=summer_sale" in location
        assert "utm_content=banner1" in location
        assert "utm_term=shoes" in location

    def test_all_utm_params_recorded(self, client: TestClient) -> None:
        """All 5 UTM params are recorded in event."""
        client.get(
            "/out/go",
            params={
                "url": "https://example.com/page",
                "utm_source": "google",
                "utm_medium": "cpc",
                "utm_campaign": "summer_sale",
                "utm_content": "banner1",
                "utm_term": "shoes",
            },
        )

        recorder = outbound.get_event_recorder()
        events = recorder.get_events()
        utm = events[0]["utm_params"]

        assert utm["utm_source"] == "google"
        assert utm["utm_medium"] == "cpc"
        assert utm["utm_campaign"] == "summer_sale"
        assert utm["utm_content"] == "banner1"
        assert utm["utm_term"] == "shoes"
