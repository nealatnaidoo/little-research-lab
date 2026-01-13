"""
Unit tests for LinkService.

Tests the functional core business logic without HTTP concerns.
"""

from uuid import UUID, uuid4

import pytest

from src.components.links import (
    LinkService,
)
from src.domain.entities import LinkItem


class MockLinkRepo:
    """Mock repository for testing."""

    def __init__(self):
        self.links: dict[UUID, LinkItem] = {}

    def save(self, link: LinkItem) -> LinkItem:
        """Save link."""
        self.links[link.id] = link
        return link

    def get_all(self) -> list[LinkItem]:
        """Get all links."""
        return list(self.links.values())

    def delete(self, link_id: UUID) -> None:
        """Delete link."""
        if link_id in self.links:
            del self.links[link_id]


@pytest.fixture
def repo():
    """Create mock repository."""
    return MockLinkRepo()


@pytest.fixture
def service(repo):
    """Create service with mock repo."""
    return LinkService(repo=repo)


# --- Create Tests ---


def test_create_link_success(service: LinkService):
    """Test successful link creation."""
    link, errors = service.create(
        title="GitHub",
        slug="github",
        url="https://github.com/user",
        icon="github",
        status="active",
        position=1,
        visibility="public",
    )

    assert link is not None
    assert errors == []
    assert link.title == "GitHub"
    assert link.slug == "github"
    assert link.url == "https://github.com/user"
    assert link.icon == "github"
    assert link.status == "active"
    assert link.position == 1
    assert link.visibility == "public"


def test_create_link_strips_whitespace(service: LinkService):
    """Test that whitespace is stripped from fields."""
    link, errors = service.create(
        title="  GitHub  ",
        slug="  github  ",
        url="  https://github.com/user  ",
        icon="  github  ",
    )

    assert link is not None
    assert link.title == "GitHub"
    assert link.slug == "github"
    assert link.url == "https://github.com/user"
    assert link.icon == "github"


def test_create_link_title_required(service: LinkService):
    """Test that title is required."""
    link, errors = service.create(
        title="",
        slug="github",
        url="https://github.com",
    )

    assert link is None
    assert len(errors) == 1
    assert errors[0].code == "title_required"
    assert errors[0].field == "title"


def test_create_link_title_too_long(service: LinkService):
    """Test that title has max length."""
    link, errors = service.create(
        title="a" * 201,
        slug="github",
        url="https://github.com",
    )

    assert link is None
    assert len(errors) == 1
    assert errors[0].code == "title_too_long"
    assert errors[0].field == "title"


def test_create_link_slug_required(service: LinkService):
    """Test that slug is required."""
    link, errors = service.create(
        title="GitHub",
        slug="",
        url="https://github.com",
    )

    assert link is None
    assert len(errors) == 1
    assert errors[0].code == "slug_required"
    assert errors[0].field == "slug"


def test_create_link_slug_too_long(service: LinkService):
    """Test that slug has max length."""
    link, errors = service.create(
        title="GitHub",
        slug="a" * 101,
        url="https://github.com",
    )

    assert link is None
    assert len(errors) == 1
    assert errors[0].code == "slug_too_long"
    assert errors[0].field == "slug"


def test_create_link_url_required(service: LinkService):
    """Test that URL is required."""
    link, errors = service.create(
        title="GitHub",
        slug="github",
        url="",
    )

    assert link is None
    assert len(errors) == 1
    assert errors[0].code == "url_required"
    assert errors[0].field == "url"


def test_create_link_url_invalid_scheme(service: LinkService):
    """Test that URL must start with http:// or https://."""
    link, errors = service.create(
        title="GitHub",
        slug="github",
        url="ftp://github.com",
    )

    assert link is None
    assert len(errors) == 1
    assert errors[0].code == "url_invalid_scheme"
    assert errors[0].field == "url"


def test_create_link_duplicate_slug(service: LinkService):
    """Test that slug must be unique."""
    # Create first link
    service.create(
        title="GitHub",
        slug="github",
        url="https://github.com/user1",
    )

    # Try to create second link with same slug
    link, errors = service.create(
        title="GitHub 2",
        slug="github",
        url="https://github.com/user2",
    )

    assert link is None
    assert len(errors) == 1
    assert errors[0].code == "slug_duplicate"
    assert "github" in errors[0].message


def test_create_link_multiple_validation_errors(service: LinkService):
    """Test that multiple validation errors are returned."""
    link, errors = service.create(
        title="",
        slug="",
        url="",
    )

    assert link is None
    assert len(errors) == 3
    error_codes = {err.code for err in errors}
    assert "title_required" in error_codes
    assert "slug_required" in error_codes
    assert "url_required" in error_codes


# --- Update Tests ---


def test_update_link_success(service: LinkService):
    """Test successful link update."""
    # Create link
    link, _ = service.create(
        title="GitHub",
        slug="github",
        url="https://github.com/user",
    )
    assert link is not None

    # Update link
    updated, errors = service.update(
        link.id,
        {"title": "GitHub Updated", "url": "https://github.com/newuser"},
    )

    assert updated is not None
    assert errors == []
    assert updated.title == "GitHub Updated"
    assert updated.url == "https://github.com/newuser"
    assert updated.slug == "github"  # unchanged


def test_update_link_not_found(service: LinkService):
    """Test updating non-existent link."""
    link_id = uuid4()
    updated, errors = service.update(link_id, {"title": "New Title"})

    assert updated is None
    assert len(errors) == 1
    assert errors[0].code == "link_not_found"


def test_update_link_validation_error(service: LinkService):
    """Test update with invalid data."""
    # Create link
    link, _ = service.create(
        title="GitHub",
        slug="github",
        url="https://github.com/user",
    )
    assert link is not None

    # Try to update with invalid URL
    updated, errors = service.update(link.id, {"url": "not-a-url"})

    assert updated is None
    assert len(errors) == 1
    assert errors[0].code == "url_invalid_scheme"


def test_update_link_duplicate_slug(service: LinkService):
    """Test updating slug to existing slug."""
    # Create two links
    link1, _ = service.create(
        title="GitHub",
        slug="github",
        url="https://github.com/user",
    )
    link2, _ = service.create(
        title="Twitter",
        slug="twitter",
        url="https://twitter.com/user",
    )
    assert link1 is not None
    assert link2 is not None

    # Try to update link2 to have link1's slug
    updated, errors = service.update(link2.id, {"slug": "github"})

    assert updated is None
    assert len(errors) == 1
    assert errors[0].code == "slug_duplicate"


def test_update_link_same_slug_allowed(service: LinkService):
    """Test that updating with same slug is allowed."""
    # Create link
    link, _ = service.create(
        title="GitHub",
        slug="github",
        url="https://github.com/user",
    )
    assert link is not None

    # Update with same slug (should succeed)
    updated, errors = service.update(
        link.id,
        {"slug": "github", "title": "GitHub Updated"},
    )

    assert updated is not None
    assert errors == []
    assert updated.slug == "github"
    assert updated.title == "GitHub Updated"


# --- Delete Tests ---


def test_delete_link_success(service: LinkService):
    """Test successful link deletion."""
    # Create link
    link, _ = service.create(
        title="GitHub",
        slug="github",
        url="https://github.com/user",
    )
    assert link is not None

    # Delete link
    success, errors = service.delete(link.id)

    assert success is True
    assert errors == []

    # Verify link is gone
    found = service.get_by_id(link.id)
    assert found is None


def test_delete_link_not_found(service: LinkService):
    """Test deleting non-existent link."""
    link_id = uuid4()
    success, errors = service.delete(link_id)

    assert success is False
    assert len(errors) == 1
    assert errors[0].code == "link_not_found"


# --- Get Tests ---


def test_get_by_id_success(service: LinkService):
    """Test getting link by ID."""
    # Create link
    link, _ = service.create(
        title="GitHub",
        slug="github",
        url="https://github.com/user",
    )
    assert link is not None

    # Get link
    found = service.get_by_id(link.id)

    assert found is not None
    assert found.id == link.id
    assert found.title == "GitHub"


def test_get_by_id_not_found(service: LinkService):
    """Test getting non-existent link."""
    link_id = uuid4()
    found = service.get_by_id(link_id)

    assert found is None


def test_get_all_empty(service: LinkService):
    """Test getting all links when none exist."""
    links = service.get_all()

    assert links == []


def test_get_all_with_links(service: LinkService):
    """Test getting all links."""
    # Create multiple links
    link1, _ = service.create(
        title="GitHub",
        slug="github",
        url="https://github.com/user",
    )
    link2, _ = service.create(
        title="Twitter",
        slug="twitter",
        url="https://twitter.com/user",
    )

    # Get all
    links = service.get_all()

    assert len(links) == 2
    link_ids = {link.id for link in links}
    assert link1.id in link_ids
    assert link2.id in link_ids
