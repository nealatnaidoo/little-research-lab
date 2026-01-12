"""
Tests for Public Visibility Guard (R1, T-0046).

Test assertions:
- Only published content is served on public routes
- Draft content returns 404
- Scheduled content returns 404
- None content returns 404
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.deps import get_published_content_or_404, require_published

# --- Mock Content Objects ---


@dataclass
class MockContent:
    """Mock content for testing visibility guard."""

    id: str
    status: str
    title: str = "Test Content"


@dataclass
class MockContentWithoutStatus:
    """Mock object without status attribute."""

    id: str
    title: str


# --- Test require_published ---


class TestRequirePublished:
    """Test require_published guard function."""

    def test_published_content_passes(self) -> None:
        """Published content passes the guard."""
        content = MockContent(id="123", status="published")

        result = require_published(content)

        assert result is content

    def test_draft_content_raises_404(self) -> None:
        """Draft content raises 404."""
        content = MockContent(id="123", status="draft")

        with pytest.raises(HTTPException) as exc:
            require_published(content)

        assert exc.value.status_code == 404
        assert exc.value.detail == "Content not found"

    def test_scheduled_content_raises_404(self) -> None:
        """Scheduled content raises 404."""
        content = MockContent(id="123", status="scheduled")

        with pytest.raises(HTTPException) as exc:
            require_published(content)

        assert exc.value.status_code == 404

    def test_none_content_raises_404(self) -> None:
        """None content raises 404."""
        with pytest.raises(HTTPException) as exc:
            require_published(None)

        assert exc.value.status_code == 404
        assert exc.value.detail == "Content not found"

    def test_content_without_status_raises_404(self) -> None:
        """Content without status attribute raises 404."""
        content = MockContentWithoutStatus(id="123", title="Test")

        with pytest.raises(HTTPException) as exc:
            require_published(content)

        assert exc.value.status_code == 404

    def test_empty_status_raises_404(self) -> None:
        """Empty status raises 404."""
        content = MockContent(id="123", status="")

        with pytest.raises(HTTPException) as exc:
            require_published(content)

        assert exc.value.status_code == 404

    def test_archived_status_raises_404(self) -> None:
        """Archived status raises 404."""
        content = MockContent(id="123", status="archived")

        with pytest.raises(HTTPException) as exc:
            require_published(content)

        assert exc.value.status_code == 404


# --- Test get_published_content_or_404 ---


class TestGetPublishedContentOr404:
    """Test get_published_content_or_404 with custom messages."""

    def test_published_content_passes(self) -> None:
        """Published content passes."""
        content = MockContent(id="123", status="published")

        result = get_published_content_or_404(content)

        assert result is content

    def test_draft_with_custom_message(self) -> None:
        """Draft with custom error message."""
        content = MockContent(id="123", status="draft")

        with pytest.raises(HTTPException) as exc:
            get_published_content_or_404(content, detail="Post not found")

        assert exc.value.status_code == 404
        assert exc.value.detail == "Post not found"

    def test_none_with_custom_message(self) -> None:
        """None with custom error message."""
        with pytest.raises(HTTPException) as exc:
            get_published_content_or_404(None, detail="Resource not found")

        assert exc.value.status_code == 404
        assert exc.value.detail == "Resource not found"


# --- Integration Tests with Real Content Types ---


class TestVisibilityWithRealEntities:
    """Test visibility guard with real domain entities."""

    def test_published_post(self) -> None:
        """Published post passes visibility guard."""
        from src.domain.entities import ContentItem

        post = ContentItem(
            id=uuid4(),
            type="post",
            slug="test-post",
            title="Test Post",
            summary="Summary",
            status="published",
            owner_user_id=uuid4(),
            published_at=datetime.now(UTC),
        )

        result = require_published(post)
        assert result is post

    def test_draft_post(self) -> None:
        """Draft post fails visibility guard."""
        from src.domain.entities import ContentItem

        post = ContentItem(
            id=uuid4(),
            type="post",
            slug="draft-post",
            title="Draft Post",
            summary="Summary",
            status="draft",
            owner_user_id=uuid4(),
        )

        with pytest.raises(HTTPException) as exc:
            require_published(post)

        assert exc.value.status_code == 404

    def test_scheduled_post(self) -> None:
        """Scheduled post fails visibility guard."""
        from src.domain.entities import ContentItem

        post = ContentItem(
            id=uuid4(),
            type="post",
            slug="scheduled-post",
            title="Scheduled Post",
            summary="Summary",
            status="scheduled",
            owner_user_id=uuid4(),
        )

        with pytest.raises(HTTPException) as exc:
            require_published(post)

        assert exc.value.status_code == 404


# --- Rule Enforcement Tests ---


class TestR1RuleEnforcement:
    """Test R1 rule: public_visibility.only_status = published."""

    def test_only_published_allowed(self) -> None:
        """
        R1: Public routes only serve content with status='published'.

        All other statuses should return 404 to hide existence.
        """
        allowed_statuses = ["published"]
        denied_statuses = ["draft", "scheduled", "archived", "pending", "review"]

        for status in allowed_statuses:
            content = MockContent(id="123", status=status)
            result = require_published(content)
            assert result is content, f"Status '{status}' should be allowed"

        for status in denied_statuses:
            content = MockContent(id="123", status=status)
            with pytest.raises(HTTPException) as exc:
                require_published(content)
            assert exc.value.status_code == 404, f"Status '{status}' should be denied"

    def test_404_hides_existence(self) -> None:
        """
        Security: 404 response should not reveal content existence.

        Both non-existent and non-published content return same 404.
        """
        # Non-existent
        with pytest.raises(HTTPException) as exc1:
            require_published(None)

        # Draft (exists but not published)
        with pytest.raises(HTTPException) as exc2:
            require_published(MockContent(id="123", status="draft"))

        # Both should have same error response
        assert exc1.value.status_code == exc2.value.status_code == 404
        assert exc1.value.detail == exc2.value.detail == "Content not found"
