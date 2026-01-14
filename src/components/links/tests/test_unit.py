"""
Links component unit tests.

Tests for link CRUD operations and validation.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from src.components.links import (
    CreateLinkInput,
    DeleteLinkInput,
    GetLinkInput,
    LinkService,
    UpdateLinkInput,
    run_create,
    run_delete,
    run_get,
    run_list,
    run_update,
)
from src.domain.entities import LinkItem

# --- Mock Repository ---


class MockLinkRepo:
    """In-memory link repository for testing."""

    def __init__(self) -> None:
        self._links: dict[UUID, LinkItem] = {}

    def save(self, link: LinkItem) -> LinkItem:
        self._links[link.id] = link
        return link

    def get_all(self) -> list[LinkItem]:
        return list(self._links.values())

    def get_by_id(self, link_id: UUID) -> LinkItem | None:
        return self._links.get(link_id)

    def delete(self, link_id: UUID) -> None:
        self._links.pop(link_id, None)


@pytest.fixture
def repo() -> MockLinkRepo:
    return MockLinkRepo()


@pytest.fixture
def service(repo: MockLinkRepo) -> LinkService:
    return LinkService(repo=repo)


# --- Creation Tests ---


class TestCreateLink:
    """Test link creation."""

    def test_create_link_success(self, service: LinkService) -> None:
        """Creates link with valid data."""
        inp = CreateLinkInput(
            title="Test Link",
            slug="test-link",
            url="https://example.com",
        )
        result = run_create(inp, service)

        assert result.success is True
        assert result.link is not None
        assert result.link.title == "Test Link"
        assert result.link.slug == "test-link"
        assert result.link.url == "https://example.com"
        assert len(result.errors) == 0

    def test_create_link_duplicate_slug(self, service: LinkService) -> None:
        """Rejects duplicate slug."""
        inp1 = CreateLinkInput(
            title="First Link",
            slug="my-slug",
            url="https://example.com/1",
        )
        run_create(inp1, service)

        inp2 = CreateLinkInput(
            title="Second Link",
            slug="my-slug",  # Same slug
            url="https://example.com/2",
        )
        result = run_create(inp2, service)

        assert result.success is False
        assert result.link is None
        assert len(result.errors) == 1
        assert result.errors[0].code == "slug_duplicate"

    def test_create_link_invalid_url(self, service: LinkService) -> None:
        """Rejects invalid URL scheme."""
        inp = CreateLinkInput(
            title="Bad Link",
            slug="bad-link",
            url="ftp://example.com",  # Invalid scheme
        )
        result = run_create(inp, service)

        assert result.success is False
        assert result.link is None
        assert len(result.errors) == 1
        assert result.errors[0].code == "url_invalid_scheme"

    def test_create_link_missing_title(self, service: LinkService) -> None:
        """Rejects missing title."""
        inp = CreateLinkInput(
            title="",
            slug="no-title",
            url="https://example.com",
        )
        result = run_create(inp, service)

        assert result.success is False
        assert result.errors[0].code == "title_required"

    def test_create_link_title_too_long(self, service: LinkService) -> None:
        """Rejects title over 200 characters."""
        inp = CreateLinkInput(
            title="x" * 201,
            slug="long-title",
            url="https://example.com",
        )
        result = run_create(inp, service)

        assert result.success is False
        assert result.errors[0].code == "title_too_long"


# --- Update Tests ---


class TestUpdateLink:
    """Test link updates."""

    def test_update_link_success(self, service: LinkService) -> None:
        """Updates existing link."""
        # Create first
        create_inp = CreateLinkInput(
            title="Original",
            slug="original",
            url="https://example.com",
        )
        created = run_create(create_inp, service)
        assert created.link is not None

        # Update
        update_inp = UpdateLinkInput(
            link_id=created.link.id,
            title="Updated",
        )
        result = run_update(update_inp, service)

        assert result.success is True
        assert result.link is not None
        assert result.link.title == "Updated"
        assert result.link.slug == "original"  # Unchanged

    def test_update_link_not_found(self, service: LinkService) -> None:
        """Returns error for missing link."""
        update_inp = UpdateLinkInput(
            link_id=uuid4(),
            title="Updated",
        )
        result = run_update(update_inp, service)

        assert result.success is False
        assert result.link is None
        assert result.errors[0].code == "link_not_found"


# --- Delete Tests ---


class TestDeleteLink:
    """Test link deletion."""

    def test_delete_link_success(self, service: LinkService) -> None:
        """Deletes existing link."""
        # Create first
        create_inp = CreateLinkInput(
            title="To Delete",
            slug="to-delete",
            url="https://example.com",
        )
        created = run_create(create_inp, service)
        assert created.link is not None

        # Delete
        delete_inp = DeleteLinkInput(link_id=created.link.id)
        result = run_delete(delete_inp, service)

        assert result.success is True
        assert len(result.errors) == 0

        # Verify deleted
        get_inp = GetLinkInput(link_id=created.link.id)
        get_result = run_get(get_inp, service)
        assert get_result.success is False

    def test_delete_link_not_found(self, service: LinkService) -> None:
        """Returns error for missing link."""
        delete_inp = DeleteLinkInput(link_id=uuid4())
        result = run_delete(delete_inp, service)

        assert result.success is False
        assert result.errors[0].code == "link_not_found"


# --- Get/List Tests ---


class TestGetAndListLinks:
    """Test link retrieval."""

    def test_get_link_by_id(self, service: LinkService) -> None:
        """Returns link by ID."""
        create_inp = CreateLinkInput(
            title="Test",
            slug="test",
            url="https://example.com",
        )
        created = run_create(create_inp, service)
        assert created.link is not None

        get_inp = GetLinkInput(link_id=created.link.id)
        result = run_get(get_inp, service)

        assert result.success is True
        assert result.link is not None
        assert result.link.id == created.link.id

    def test_list_links(self, service: LinkService) -> None:
        """Returns all links with count."""
        # Create multiple links
        for i in range(3):
            inp = CreateLinkInput(
                title=f"Link {i}",
                slug=f"link-{i}",
                url=f"https://example.com/{i}",
            )
            run_create(inp, service)

        result = run_list(service)

        assert result.total == 3
        assert len(result.links) == 3

    def test_list_links_empty(self, service: LinkService) -> None:
        """Returns empty list when no links exist."""
        result = run_list(service)

        assert result.total == 0
        assert len(result.links) == 0
