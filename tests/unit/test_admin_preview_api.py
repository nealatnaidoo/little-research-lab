"""
Tests for Admin Preview API (E4.4).

Test assertions:
- TA-0025: Preview renders same as public (content parity)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.routes.admin_preview import router

# --- Test Client Setup ---


@pytest.fixture
def client() -> TestClient:
    """Test client."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    return TestClient(app)


@pytest.fixture
def simple_doc() -> dict:
    """Simple rich text document."""
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Hello, world!"}]}],
    }


@pytest.fixture
def complex_doc() -> dict:
    """Complex document with multiple elements."""
    return {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "Main Title"}],
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "This is a paragraph with "},
                    {"type": "text", "text": "bold", "marks": [{"type": "bold"}]},
                    {"type": "text", "text": " and "},
                    {
                        "type": "text",
                        "text": "a link",
                        "marks": [{"type": "link", "attrs": {"href": "https://example.com"}}],
                    },
                    {"type": "text", "text": "."},
                ],
            },
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Section One"}],
            },
            {"type": "paragraph", "content": [{"type": "text", "text": "More content here."}]},
        ],
    }


# --- TA-0025: Preview Content Parity ---


class TestPreviewEndpoint:
    """Test TA-0025: Preview renders same as public."""

    def test_preview_simple_doc(self, client: TestClient, simple_doc: dict) -> None:
        """Preview simple document."""
        response = client.post(
            "/preview",
            json={"rich_text_json": simple_doc},
        )

        assert response.status_code == 200
        data = response.json()
        assert "<p>Hello, world!</p>" in data["html"]
        assert data["plain_text"] == "Hello, world!"
        assert data["word_count"] == 2

    def test_preview_complex_doc(self, client: TestClient, complex_doc: dict) -> None:
        """Preview complex document."""
        response = client.post(
            "/preview",
            json={"rich_text_json": complex_doc},
        )

        assert response.status_code == 200
        data = response.json()

        # Check HTML contains expected elements
        assert "<h1" in data["html"]
        assert "<h2" in data["html"]
        assert "<strong>bold</strong>" in data["html"]
        assert "<a href=" in data["html"]
        assert "noopener" in data["html"]

        # Check headings extracted
        assert len(data["headings"]) == 2
        assert data["headings"][0]["text"] == "Main Title"
        assert data["headings"][0]["level"] == 1
        assert data["headings"][1]["text"] == "Section One"

        # Check link count
        assert data["link_count"] == 1

    def test_preview_with_article_wrapper(
        self,
        client: TestClient,
        simple_doc: dict,
    ) -> None:
        """Preview with article wrapper enabled."""
        response = client.post(
            "/preview",
            json={"rich_text_json": simple_doc, "wrap_in_article": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["html"].startswith("<article>")
        assert data["html"].endswith("</article>")

    def test_preview_without_article_wrapper(
        self,
        client: TestClient,
        simple_doc: dict,
    ) -> None:
        """Preview without article wrapper."""
        response = client.post(
            "/preview",
            json={"rich_text_json": simple_doc, "wrap_in_article": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert not data["html"].startswith("<article>")

    def test_preview_with_heading_ids(
        self,
        client: TestClient,
        complex_doc: dict,
    ) -> None:
        """Preview with heading IDs enabled."""
        response = client.post(
            "/preview",
            json={"rich_text_json": complex_doc, "add_heading_ids": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert 'id="main-title"' in data["html"]
        assert 'id="section-one"' in data["html"]

    def test_preview_without_heading_ids(
        self,
        client: TestClient,
        complex_doc: dict,
    ) -> None:
        """Preview without heading IDs."""
        response = client.post(
            "/preview",
            json={"rich_text_json": complex_doc, "add_heading_ids": False},
        )

        assert response.status_code == 200
        data = response.json()
        # Headings should not have IDs
        assert 'id="main-title"' not in data["html"]


class TestValidateEndpoint:
    """Test validation endpoint."""

    def test_validate_valid_doc(self, client: TestClient, simple_doc: dict) -> None:
        """Valid document passes validation."""
        response = client.post(
            "/preview/validate",
            json={"rich_text_json": simple_doc},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["errors"]) == 0

    def test_validate_invalid_node(self, client: TestClient) -> None:
        """Invalid node type is reported."""
        doc = {"type": "doc", "content": [{"type": "script", "content": []}]}

        response = client.post(
            "/preview/validate",
            json={"rich_text_json": doc},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        assert any(e["code"] == "invalid_node_type" for e in data["errors"])


class TestSanitizeEndpoint:
    """Test sanitization endpoint."""

    def test_sanitize_clean_doc(self, client: TestClient, simple_doc: dict) -> None:
        """Clean document passes through unchanged."""
        response = client.post(
            "/preview/sanitize",
            json={"rich_text_json": simple_doc},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["changes"]) == 0
        assert "<p>Hello, world!</p>" in data["html"]

    def test_sanitize_removes_invalid(self, client: TestClient) -> None:
        """Invalid content is stripped."""
        doc = {
            "type": "doc",
            "content": [
                {"type": "script", "content": []},
                {"type": "paragraph", "content": [{"type": "text", "text": "Safe"}]},
            ],
        }

        response = client.post(
            "/preview/sanitize",
            json={"rich_text_json": doc},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["changes"]) > 0
        assert "<p>Safe</p>" in data["html"]
        # Script should be stripped
        assert "<script>" not in data["html"]


class TestHeadingsEndpoint:
    """Test headings extraction endpoint."""

    def test_extract_headings(self, client: TestClient, complex_doc: dict) -> None:
        """Extract headings for ToC."""
        response = client.post(
            "/preview/headings",
            json={"rich_text_json": complex_doc},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["headings"]) == 2
        assert data["headings"][0]["text"] == "Main Title"
        assert data["headings"][0]["id"] == "main-title"

    def test_extract_no_headings(self, client: TestClient, simple_doc: dict) -> None:
        """Document with no headings."""
        response = client.post(
            "/preview/headings",
            json={"rich_text_json": simple_doc},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["headings"]) == 0


class TestStatsEndpoint:
    """Test content statistics endpoint."""

    def test_get_stats(self, client: TestClient, complex_doc: dict) -> None:
        """Get content statistics."""
        response = client.post(
            "/preview/stats",
            json={"rich_text_json": complex_doc},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["word_count"] > 0
        assert data["char_count"] > 0
        assert data["link_count"] == 1
        assert data["heading_count"] == 2
        assert data["reading_time_minutes"] >= 1

    def test_stats_empty_doc(self, client: TestClient) -> None:
        """Stats for empty document."""
        doc = {"type": "doc", "content": []}

        response = client.post(
            "/preview/stats",
            json={"rich_text_json": doc},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["word_count"] == 0
        assert data["link_count"] == 0


# --- Edge Cases ---


class TestEdgeCases:
    """Test edge cases."""

    def test_missing_rich_text(self, client: TestClient) -> None:
        """Missing rich_text_json returns error."""
        response = client.post("/preview", json={})
        assert response.status_code == 422

    def test_invalid_json_structure(self, client: TestClient) -> None:
        """Invalid JSON structure handled gracefully."""
        response = client.post(
            "/preview",
            json={"rich_text_json": "not a dict"},
        )
        assert response.status_code == 422

    def test_empty_document(self, client: TestClient) -> None:
        """Empty document renders."""
        doc = {"type": "doc", "content": []}

        response = client.post(
            "/preview",
            json={"rich_text_json": doc},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["html"] == "<article></article>"
        assert data["word_count"] == 0
