"""
Tests for Analytics Ingestion API (E6.1).

Test assertions:
- TA-0034: Event validation (allowed types, fields)
- TA-0035: PII prevention (forbidden fields blocked)
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.analytics_ingest import router

# --- Test Client Setup ---


@pytest.fixture
def client() -> TestClient:
    """Test client."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# --- TA-0034: Event Type Validation ---


class TestEventTypeValidation:
    """Test TA-0034: Event type validation."""

    def test_page_view_accepted(self, client: TestClient) -> None:
        """page_view event type is accepted."""
        response = client.post(
            "/event",
            json={"event_type": "page_view", "path": "/test"},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_outbound_click_accepted(self, client: TestClient) -> None:
        """outbound_click event type is accepted."""
        response = client.post(
            "/event",
            json={"event_type": "outbound_click", "link_id": "link-1"},
        )
        assert response.status_code == 200

    def test_asset_download_accepted(self, client: TestClient) -> None:
        """asset_download event type is accepted."""
        response = client.post(
            "/event",
            json={"event_type": "asset_download", "asset_id": str(uuid4())},
        )
        assert response.status_code == 200

    def test_invalid_event_type_rejected(self, client: TestClient) -> None:
        """TA-0034: Invalid event type is rejected."""
        response = client.post(
            "/event",
            json={"event_type": "custom_event"},
        )
        assert response.status_code == 400
        data = response.json()["detail"]
        assert any(e["code"] == "invalid_event_type" for e in data["errors"])

    def test_missing_event_type_rejected(self, client: TestClient) -> None:
        """TA-0034: Missing event type is rejected."""
        response = client.post(
            "/event",
            json={"path": "/test"},
        )
        assert response.status_code == 422  # Pydantic validation error


# --- TA-0035: PII Prevention ---


class TestPIIPrevention:
    """Test TA-0035: PII prevention."""

    def test_ip_rejected(self, client: TestClient) -> None:
        """TA-0035: IP address is rejected."""
        response = client.post(
            "/event",
            json={"event_type": "page_view", "ip": "192.168.1.1"},
        )
        assert response.status_code == 400
        data = response.json()["detail"]
        assert any(e["code"] == "forbidden_field" for e in data["errors"])

    def test_ip_address_rejected(self, client: TestClient) -> None:
        """TA-0035: ip_address field is rejected."""
        response = client.post(
            "/event",
            json={"event_type": "page_view", "ip_address": "10.0.0.1"},
        )
        assert response.status_code == 400

    def test_user_agent_rejected(self, client: TestClient) -> None:
        """TA-0035: Full user agent is rejected."""
        response = client.post(
            "/event",
            json={"event_type": "page_view", "user_agent": "Mozilla/5.0..."},
        )
        assert response.status_code == 400

    def test_cookie_rejected(self, client: TestClient) -> None:
        """TA-0035: Cookie data is rejected."""
        response = client.post(
            "/event",
            json={"event_type": "page_view", "cookie": "session=abc"},
        )
        assert response.status_code == 400

    def test_visitor_id_rejected(self, client: TestClient) -> None:
        """TA-0035: Visitor ID is rejected."""
        response = client.post(
            "/event",
            json={"event_type": "page_view", "visitor_id": "v123"},
        )
        assert response.status_code == 400

    def test_email_rejected(self, client: TestClient) -> None:
        """TA-0035: Email is rejected."""
        response = client.post(
            "/event",
            json={"event_type": "page_view", "email": "user@example.com"},
        )
        assert response.status_code == 400


# --- UTM Parameters ---


class TestUTMParameters:
    """Test UTM parameter handling."""

    def test_all_utm_params_accepted(self, client: TestClient) -> None:
        """All UTM parameters are accepted."""
        response = client.post(
            "/event",
            json={
                "event_type": "page_view",
                "path": "/landing",
                "utm_source": "newsletter",
                "utm_medium": "email",
                "utm_campaign": "launch",
                "utm_content": "button",
                "utm_term": "signup",
            },
        )
        assert response.status_code == 200


# --- Content IDs ---


class TestContentIDs:
    """Test content ID handling."""

    def test_valid_content_id_accepted(self, client: TestClient) -> None:
        """Valid content UUID is accepted."""
        response = client.post(
            "/event",
            json={
                "event_type": "page_view",
                "content_id": str(uuid4()),
            },
        )
        assert response.status_code == 200

    def test_invalid_content_id_rejected(self, client: TestClient) -> None:
        """Invalid content UUID is rejected."""
        response = client.post(
            "/event",
            json={
                "event_type": "page_view",
                "content_id": "not-a-uuid",
            },
        )
        assert response.status_code == 400
        data = response.json()["detail"]
        assert any(e["code"] == "invalid_uuid" for e in data["errors"])


# --- Batch Ingestion ---


class TestBatchIngestion:
    """Test batch event ingestion."""

    def test_batch_all_valid(self, client: TestClient) -> None:
        """Batch with all valid events succeeds."""
        events = [
            {"event_type": "page_view", "path": "/page-1"},
            {"event_type": "page_view", "path": "/page-2"},
        ]

        response = client.post("/batch", json=events)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert len(data["results"]) == 2
        assert all(r["ok"] for r in data["results"])

    def test_batch_partial_failure(self, client: TestClient) -> None:
        """Batch with some invalid events returns partial results."""
        events = [
            {"event_type": "page_view", "path": "/valid"},
            {"event_type": "invalid_type"},  # This will fail
            {"event_type": "page_view", "path": "/also-valid"},
        ]

        response = client.post("/batch", json=events)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False  # Overall failure
        assert data["results"][0]["ok"] is True
        assert data["results"][1]["ok"] is False
        assert data["results"][2]["ok"] is True


# --- Edge Cases ---


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_request_rejected(self, client: TestClient) -> None:
        """Empty request is rejected."""
        response = client.post("/event", json={})
        assert response.status_code == 422

    def test_referrer_accepted(self, client: TestClient) -> None:
        """Referrer URL is accepted."""
        response = client.post(
            "/event",
            json={
                "event_type": "page_view",
                "referrer": "https://google.com",
            },
        )
        assert response.status_code == 200

    def test_ua_class_accepted(self, client: TestClient) -> None:
        """UA class is accepted."""
        for ua_class in ["real", "bot", "unknown"]:
            response = client.post(
                "/event",
                json={
                    "event_type": "page_view",
                    "ua_class": ua_class,
                },
            )
            assert response.status_code == 200

    def test_invalid_ua_class_rejected(self, client: TestClient) -> None:
        """Invalid UA class is rejected."""
        response = client.post(
            "/event",
            json={
                "event_type": "page_view",
                "ua_class": "crawler",
            },
        )
        assert response.status_code == 400
