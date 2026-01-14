"""
Tests for Resource(PDF) Service (E3.1).

Test assertions:
- TA-0014: Resource draft persistence (create, update, save)
- TA-0015: Pinned policy validation (pinned_version vs latest)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.components.render import (
    ResourcePDF,
    ResourcePDFService,
    validate_pinned_policy,
)

# --- Mock Repositories ---


class MockResourcePDFRepo:
    """In-memory resource repository for testing."""

    def __init__(self) -> None:
        self._resources: dict[UUID, ResourcePDF] = {}

    def get_by_id(self, resource_id: UUID) -> ResourcePDF | None:
        return self._resources.get(resource_id)

    def get_by_slug(self, slug: str) -> ResourcePDF | None:
        for r in self._resources.values():
            if r.slug == slug:
                return r
        return None

    def save(self, resource: ResourcePDF) -> ResourcePDF:
        self._resources[resource.id] = resource
        return resource

    def delete(self, resource_id: UUID) -> None:
        self._resources.pop(resource_id, None)

    def list_all(self) -> list[ResourcePDF]:
        return list(self._resources.values())


class MockAssetResolver:
    """Mock asset resolver for testing."""

    def __init__(self) -> None:
        self._assets: dict[UUID, dict[str, Any]] = {}
        self._versions: dict[UUID, dict[str, Any]] = {}

    def add_asset(
        self,
        asset_id: UUID,
        mime_type: str = "application/pdf",
    ) -> None:
        self._assets[asset_id] = {"id": asset_id, "mime_type": mime_type}

    def add_version(
        self,
        version_id: UUID,
        asset_id: UUID,
    ) -> None:
        self._versions[version_id] = {"id": version_id, "asset_id": asset_id}

    def get_asset(self, asset_id: UUID) -> dict[str, Any] | None:
        return self._assets.get(asset_id)

    def get_version(self, version_id: UUID) -> dict[str, Any] | None:
        return self._versions.get(version_id)

    def is_pdf(self, asset_id: UUID) -> bool:
        asset = self._assets.get(asset_id)
        return asset is not None and asset.get("mime_type") == "application/pdf"


# Mock version object with asset_id attribute
class MockVersion:
    def __init__(self, id: UUID, asset_id: UUID):
        self.id = id
        self.asset_id = asset_id


class MockAssetResolverWithAttr:
    """Mock asset resolver that returns objects with attributes."""

    def __init__(self) -> None:
        self._assets: dict[UUID, dict[str, Any]] = {}
        self._versions: dict[UUID, MockVersion] = {}

    def add_asset(self, asset_id: UUID, mime_type: str = "application/pdf") -> None:
        self._assets[asset_id] = {"id": asset_id, "mime_type": mime_type}

    def add_version(self, version_id: UUID, asset_id: UUID) -> None:
        self._versions[version_id] = MockVersion(version_id, asset_id)

    def get_asset(self, asset_id: UUID) -> dict[str, Any] | None:
        return self._assets.get(asset_id)

    def get_version(self, version_id: UUID) -> MockVersion | None:
        return self._versions.get(version_id)

    def is_pdf(self, asset_id: UUID) -> bool:
        asset = self._assets.get(asset_id)
        return asset is not None and asset.get("mime_type") == "application/pdf"


# --- Fixtures ---


@pytest.fixture
def mock_repo() -> MockResourcePDFRepo:
    return MockResourcePDFRepo()


@pytest.fixture
def mock_asset_resolver() -> MockAssetResolverWithAttr:
    resolver = MockAssetResolverWithAttr()
    # Add a default PDF asset
    asset_id = uuid4()
    version_id = uuid4()
    resolver.add_asset(asset_id, "application/pdf")
    resolver.add_version(version_id, asset_id)
    return resolver


@pytest.fixture
def service(
    mock_repo: MockResourcePDFRepo,
    mock_asset_resolver: MockAssetResolverWithAttr,
) -> ResourcePDFService:
    return ResourcePDFService(repo=mock_repo, asset_resolver=mock_asset_resolver)


@pytest.fixture
def service_no_resolver(mock_repo: MockResourcePDFRepo) -> ResourcePDFService:
    """Service without asset resolver."""
    return ResourcePDFService(repo=mock_repo)


@pytest.fixture
def owner_id() -> UUID:
    return uuid4()


# --- TA-0014: Resource Draft Persistence ---


class TestResourceDraftPersistence:
    """Test TA-0014: Resource draft creation and persistence."""

    def test_create_draft_basic(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """Create basic draft without asset."""
        resource, errors = service_no_resolver.create(
            title="Test PDF",
            slug="test-pdf",
            owner_user_id=owner_id,
        )

        assert errors == []
        assert resource is not None
        assert resource.title == "Test PDF"
        assert resource.slug == "test-pdf"
        assert resource.status == "draft"

    def test_create_draft_with_all_fields(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """Create draft with all optional fields."""
        resource, errors = service_no_resolver.create(
            title="Research Paper",
            slug="research-paper",
            owner_user_id=owner_id,
            summary="A detailed research paper on AI",
            display_title="AI Research Paper 2024",
            download_filename="ai-research-2024.pdf",
        )

        assert errors == []
        assert resource is not None
        assert resource.summary == "A detailed research paper on AI"
        assert resource.display_title == "AI Research Paper 2024"
        assert resource.download_filename == "ai-research-2024.pdf"

    def test_create_sets_timestamps(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """Created resource has timestamps set."""
        before = datetime.now(UTC)
        resource, _ = service_no_resolver.create(
            title="Test",
            slug="test",
            owner_user_id=owner_id,
        )
        after = datetime.now(UTC)

        assert resource is not None
        # Handle both timezone-aware and naive
        created = resource.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        assert before <= created <= after

    def test_create_requires_title(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """Title is required for creation."""
        resource, errors = service_no_resolver.create(
            title="",
            slug="test",
            owner_user_id=owner_id,
        )

        assert resource is None
        assert len(errors) > 0
        assert any(e.code == "title_required" for e in errors)

    def test_create_requires_slug(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """Slug is required for creation."""
        resource, errors = service_no_resolver.create(
            title="Test",
            slug="",
            owner_user_id=owner_id,
        )

        assert resource is None
        assert len(errors) > 0
        assert any(e.code == "slug_required" for e in errors)

    def test_create_validates_slug_format(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """Slug must be valid format."""
        resource, errors = service_no_resolver.create(
            title="Test",
            slug="Invalid Slug!",
            owner_user_id=owner_id,
        )

        assert resource is None
        assert len(errors) > 0
        assert any(e.code == "slug_invalid" for e in errors)

    def test_create_rejects_duplicate_slug(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """Duplicate slug is rejected."""
        # First creation succeeds
        service_no_resolver.create(
            title="First",
            slug="duplicate",
            owner_user_id=owner_id,
        )

        # Second creation with same slug fails
        resource, errors = service_no_resolver.create(
            title="Second",
            slug="duplicate",
            owner_user_id=owner_id,
        )

        assert resource is None
        assert len(errors) > 0
        assert any(e.code == "slug_exists" for e in errors)

    def test_update_persists_changes(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """Update persists field changes."""
        resource, _ = service_no_resolver.create(
            title="Original",
            slug="test",
            owner_user_id=owner_id,
        )

        updated, errors = service_no_resolver.update(
            resource.id,
            {"title": "Updated Title", "summary": "New summary"},
        )

        assert errors == []
        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.summary == "New summary"

    def test_get_retrieves_saved_resource(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """Get retrieves previously saved resource."""
        created, _ = service_no_resolver.create(
            title="Test",
            slug="test",
            owner_user_id=owner_id,
        )

        retrieved = service_no_resolver.get(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Test"

    def test_get_by_slug_retrieves_resource(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """Get by slug retrieves resource."""
        created, _ = service_no_resolver.create(
            title="Test",
            slug="my-resource",
            owner_user_id=owner_id,
        )

        retrieved = service_no_resolver.get_by_slug("my-resource")

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_delete_removes_resource(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """Delete removes resource."""
        resource, _ = service_no_resolver.create(
            title="Test",
            slug="test",
            owner_user_id=owner_id,
        )

        result = service_no_resolver.delete(resource.id)
        assert result is True

        retrieved = service_no_resolver.get(resource.id)
        assert retrieved is None


# --- TA-0015: Pinned Policy Validation ---


class TestPinnedPolicyValidation:
    """Test TA-0015: Pinned policy validation."""

    def test_latest_policy_without_version_valid(
        self,
        mock_repo: MockResourcePDFRepo,
        owner_id: UUID,
    ) -> None:
        """Latest policy without version_id is valid."""
        resource = ResourcePDF(
            id=uuid4(),
            title="Test",
            slug="test",
            summary="",
            status="draft",
            owner_user_id=owner_id,
            pdf_asset_id=uuid4(),
            pdf_version_id=None,
            pinned_policy="latest",
            display_title=None,
            download_filename=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        errors = validate_pinned_policy(resource)
        assert errors == []

    def test_latest_policy_with_version_invalid(
        self,
        mock_repo: MockResourcePDFRepo,
        owner_id: UUID,
    ) -> None:
        """Latest policy with version_id is invalid."""
        resource = ResourcePDF(
            id=uuid4(),
            title="Test",
            slug="test",
            summary="",
            status="draft",
            owner_user_id=owner_id,
            pdf_asset_id=uuid4(),
            pdf_version_id=uuid4(),  # Should be None for latest
            pinned_policy="latest",
            display_title=None,
            download_filename=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        errors = validate_pinned_policy(resource)
        assert len(errors) > 0
        assert any(e.code == "version_not_allowed_for_latest" for e in errors)

    def test_pinned_policy_with_version_valid(
        self,
        mock_asset_resolver: MockAssetResolverWithAttr,
        owner_id: UUID,
    ) -> None:
        """Pinned policy with version_id is valid."""
        # Get the existing asset and version from fixture
        asset_id = list(mock_asset_resolver._assets.keys())[0]
        version_id = list(mock_asset_resolver._versions.keys())[0]

        resource = ResourcePDF(
            id=uuid4(),
            title="Test",
            slug="test",
            summary="",
            status="draft",
            owner_user_id=owner_id,
            pdf_asset_id=asset_id,
            pdf_version_id=version_id,
            pinned_policy="pinned",
            display_title=None,
            download_filename=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        errors = validate_pinned_policy(resource, mock_asset_resolver)
        assert errors == []

    def test_pinned_policy_without_version_invalid(
        self,
        owner_id: UUID,
    ) -> None:
        """Pinned policy without version_id is invalid."""
        resource = ResourcePDF(
            id=uuid4(),
            title="Test",
            slug="test",
            summary="",
            status="draft",
            owner_user_id=owner_id,
            pdf_asset_id=uuid4(),
            pdf_version_id=None,  # Required for pinned
            pinned_policy="pinned",
            display_title=None,
            download_filename=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        errors = validate_pinned_policy(resource)
        assert len(errors) > 0
        assert any(e.code == "version_required_for_pinned" for e in errors)

    def test_set_pinned_policy_to_latest(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """Can set policy to latest."""
        resource, _ = service_no_resolver.create(
            title="Test",
            slug="test",
            owner_user_id=owner_id,
        )

        updated, errors = service_no_resolver.set_pinned_policy(
            resource.id,
            policy="latest",
        )

        assert errors == []
        assert updated is not None
        assert updated.pinned_policy == "latest"
        assert updated.pdf_version_id is None

    def test_set_pinned_policy_to_pinned(
        self,
        service: ResourcePDFService,
        mock_asset_resolver: MockAssetResolverWithAttr,
        owner_id: UUID,
    ) -> None:
        """Can set policy to pinned with version."""
        version_id = list(mock_asset_resolver._versions.keys())[0]

        resource, _ = service.create(
            title="Test",
            slug="test",
            owner_user_id=owner_id,
        )

        updated, errors = service.set_pinned_policy(
            resource.id,
            policy="pinned",
            version_id=version_id,
        )

        assert errors == []
        assert updated is not None
        assert updated.pinned_policy == "pinned"
        assert updated.pdf_version_id == version_id

    def test_asset_must_be_pdf(
        self,
        mock_repo: MockResourcePDFRepo,
        owner_id: UUID,
    ) -> None:
        """Asset must be PDF type."""
        resolver = MockAssetResolverWithAttr()
        asset_id = uuid4()
        resolver.add_asset(asset_id, "image/png")  # Not PDF!

        resource = ResourcePDF(
            id=uuid4(),
            title="Test",
            slug="test",
            summary="",
            status="draft",
            owner_user_id=owner_id,
            pdf_asset_id=asset_id,
            pdf_version_id=None,
            pinned_policy="latest",
            display_title=None,
            download_filename=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        errors = validate_pinned_policy(resource, resolver)
        assert len(errors) > 0
        assert any(e.code == "asset_not_pdf" for e in errors)

    def test_version_must_belong_to_asset(
        self,
        owner_id: UUID,
    ) -> None:
        """Version must belong to the specified asset."""
        resolver = MockAssetResolverWithAttr()
        asset_id = uuid4()
        other_asset_id = uuid4()
        version_id = uuid4()

        resolver.add_asset(asset_id, "application/pdf")
        resolver.add_asset(other_asset_id, "application/pdf")
        resolver.add_version(version_id, other_asset_id)  # Belongs to other asset

        resource = ResourcePDF(
            id=uuid4(),
            title="Test",
            slug="test",
            summary="",
            status="draft",
            owner_user_id=owner_id,
            pdf_asset_id=asset_id,  # Different asset
            pdf_version_id=version_id,  # Belongs to other_asset_id
            pinned_policy="pinned",
            display_title=None,
            download_filename=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        errors = validate_pinned_policy(resource, resolver)
        assert len(errors) > 0
        assert any(e.code == "version_asset_mismatch" for e in errors)


# --- Link Asset ---


class TestLinkAsset:
    """Test asset linking functionality."""

    def test_link_asset_with_latest_policy(
        self,
        service: ResourcePDFService,
        mock_asset_resolver: MockAssetResolverWithAttr,
        owner_id: UUID,
    ) -> None:
        """Can link asset with latest policy."""
        asset_id = list(mock_asset_resolver._assets.keys())[0]

        resource, _ = service.create(
            title="Test",
            slug="test",
            owner_user_id=owner_id,
        )

        updated, errors = service.link_asset(
            resource.id,
            asset_id=asset_id,
            policy="latest",
        )

        assert errors == []
        assert updated is not None
        assert updated.pdf_asset_id == asset_id
        assert updated.pinned_policy == "latest"

    def test_link_asset_with_pinned_policy(
        self,
        service: ResourcePDFService,
        mock_asset_resolver: MockAssetResolverWithAttr,
        owner_id: UUID,
    ) -> None:
        """Can link asset with pinned policy and version."""
        asset_id = list(mock_asset_resolver._assets.keys())[0]
        version_id = list(mock_asset_resolver._versions.keys())[0]

        resource, _ = service.create(
            title="Test",
            slug="test",
            owner_user_id=owner_id,
        )

        updated, errors = service.link_asset(
            resource.id,
            asset_id=asset_id,
            version_id=version_id,
            policy="pinned",
        )

        assert errors == []
        assert updated is not None
        assert updated.pdf_asset_id == asset_id
        assert updated.pdf_version_id == version_id
        assert updated.pinned_policy == "pinned"


# --- Edge Cases ---


class TestEdgeCases:
    """Test edge cases."""

    def test_update_nonexistent_resource(
        self,
        service_no_resolver: ResourcePDFService,
    ) -> None:
        """Update nonexistent resource returns error."""
        resource, errors = service_no_resolver.update(
            uuid4(),
            {"title": "New Title"},
        )

        assert resource is None
        assert len(errors) > 0
        assert any(e.code == "not_found" for e in errors)

    def test_delete_nonexistent_resource(
        self,
        service_no_resolver: ResourcePDFService,
    ) -> None:
        """Delete nonexistent resource returns False."""
        result = service_no_resolver.delete(uuid4())
        assert result is False

    def test_list_all_resources(
        self,
        service_no_resolver: ResourcePDFService,
        owner_id: UUID,
    ) -> None:
        """List all resources returns all created resources."""
        service_no_resolver.create(title="First", slug="first", owner_user_id=owner_id)
        service_no_resolver.create(title="Second", slug="second", owner_user_id=owner_id)
        service_no_resolver.create(title="Third", slug="third", owner_user_id=owner_id)

        resources = service_no_resolver.list_all()
        assert len(resources) == 3
