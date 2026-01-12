"""
TA-0006, TA-0007, TA-0008: AssetService upload pipeline tests.

TA-0006: MIME type allowlist enforcement
TA-0007: Size limit enforcement
TA-0008: SHA256 integrity verification

Spec refs: E2.1, R2
"""

from __future__ import annotations

import hashlib
from io import BytesIO
from uuid import UUID, uuid4

import pytest

from src.components.assets import (
    DEFAULT_ASSET_KINDS,
    AssetKindConfig,
    AssetService,
    compute_sha256,
    create_asset_service,
    generate_storage_key,
    get_asset_kind,
    mime_to_extension,
    validate_integrity,
    validate_mime_type,
    validate_size,
)
from src.core.entities import Asset, AssetVersion

# --- Mock Repositories ---


class MockAssetRepo:
    """Mock asset repository."""

    def __init__(self) -> None:
        self.assets: dict[UUID, Asset] = {}

    def get_by_id(self, asset_id: UUID) -> Asset | None:
        return self.assets.get(asset_id)

    def save(self, asset: Asset) -> Asset:
        self.assets[asset.id] = asset
        return asset

    def get_latest_version(self, asset_id: UUID) -> AssetVersion | None:
        return None  # Delegated to version repo


class MockAssetVersionRepo:
    """Mock asset version repository."""

    def __init__(self) -> None:
        self.versions: dict[UUID, AssetVersion] = {}
        self._latest: dict[UUID, UUID] = {}  # asset_id -> version_id

    def get_by_id(self, version_id: UUID) -> AssetVersion | None:
        return self.versions.get(version_id)

    def get_by_storage_key(self, key: str) -> AssetVersion | None:
        for v in self.versions.values():
            if v.storage_key == key:
                return v
        return None

    def save(self, version: AssetVersion) -> AssetVersion:
        self.versions[version.id] = version
        return version

    def get_versions(self, asset_id: UUID) -> list[AssetVersion]:
        return [v for v in self.versions.values() if v.asset_id == asset_id]

    def get_latest(self, asset_id: UUID) -> AssetVersion | None:
        version_id = self._latest.get(asset_id)
        if version_id:
            return self.versions.get(version_id)
        return None

    def set_latest(self, asset_id: UUID, version_id: UUID) -> None:
        self._latest[asset_id] = version_id
        # Update is_latest flags
        for v in self.versions.values():
            if v.asset_id == asset_id:
                v.is_latest = v.id == version_id

    def get_next_version_number(self, asset_id: UUID) -> int:
        versions = self.get_versions(asset_id)
        if not versions:
            return 1
        return max(v.version_number for v in versions) + 1


class MockStorage:
    """Mock object storage."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.put_count = 0

    def put(
        self,
        key: str,
        data: bytes | BytesIO,
        content_type: str,
        *,
        expected_sha256: str | None = None,
    ) -> dict[str, str]:
        if isinstance(data, BytesIO):
            data = data.read()
        self.objects[key] = data
        self.put_count += 1
        return {"key": key, "sha256": hashlib.sha256(data).hexdigest()}

    def exists(self, key: str) -> bool:
        return key in self.objects


# --- Fixtures ---


@pytest.fixture
def asset_repo() -> MockAssetRepo:
    """Create mock asset repository."""
    return MockAssetRepo()


@pytest.fixture
def version_repo() -> MockAssetVersionRepo:
    """Create mock asset version repository."""
    return MockAssetVersionRepo()


@pytest.fixture
def storage() -> MockStorage:
    """Create mock storage."""
    return MockStorage()


@pytest.fixture
def service(
    asset_repo: MockAssetRepo,
    version_repo: MockAssetVersionRepo,
    storage: MockStorage,
) -> AssetService:
    """Create asset service with mocks."""
    return AssetService(asset_repo, version_repo, storage)


@pytest.fixture
def test_image_data() -> bytes:
    """Create test image data."""
    return b"fake image data" * 100  # ~1.5KB


@pytest.fixture
def test_pdf_data() -> bytes:
    """Create test PDF data."""
    return b"%PDF-1.4 fake pdf content" * 1000  # ~25KB


# --- TA-0006: MIME Type Allowlist Tests ---


class TestTA0006MIMETypeAllowlist:
    """TA-0006: MIME type allowlist enforcement."""

    def test_jpeg_allowed(self, service: AssetService, test_image_data: bytes) -> None:
        """JPEG images are allowed."""
        _, _, errors = service.validate_upload(test_image_data, "image/jpeg")
        mime_errors = [e for e in errors if e.code == "invalid_mime_type"]
        assert len(mime_errors) == 0

    def test_png_allowed(self, service: AssetService, test_image_data: bytes) -> None:
        """PNG images are allowed."""
        _, _, errors = service.validate_upload(test_image_data, "image/png")
        mime_errors = [e for e in errors if e.code == "invalid_mime_type"]
        assert len(mime_errors) == 0

    def test_webp_allowed(self, service: AssetService, test_image_data: bytes) -> None:
        """WebP images are allowed."""
        _, _, errors = service.validate_upload(test_image_data, "image/webp")
        mime_errors = [e for e in errors if e.code == "invalid_mime_type"]
        assert len(mime_errors) == 0

    def test_gif_allowed(self, service: AssetService, test_image_data: bytes) -> None:
        """GIF images are allowed."""
        _, _, errors = service.validate_upload(test_image_data, "image/gif")
        mime_errors = [e for e in errors if e.code == "invalid_mime_type"]
        assert len(mime_errors) == 0

    def test_pdf_allowed(self, service: AssetService, test_pdf_data: bytes) -> None:
        """PDF files are allowed."""
        _, _, errors = service.validate_upload(test_pdf_data, "application/pdf")
        mime_errors = [e for e in errors if e.code == "invalid_mime_type"]
        assert len(mime_errors) == 0

    def test_executable_rejected(self, service: AssetService, test_image_data: bytes) -> None:
        """Executable files are rejected."""
        _, _, errors = service.validate_upload(test_image_data, "application/x-msdownload")
        mime_errors = [e for e in errors if e.code == "invalid_mime_type"]
        assert len(mime_errors) == 1
        assert "not allowed" in mime_errors[0].message.lower()

    def test_html_rejected(self, service: AssetService, test_image_data: bytes) -> None:
        """HTML files are rejected."""
        _, _, errors = service.validate_upload(test_image_data, "text/html")
        mime_errors = [e for e in errors if e.code == "invalid_mime_type"]
        assert len(mime_errors) == 1

    def test_javascript_rejected(self, service: AssetService, test_image_data: bytes) -> None:
        """JavaScript files are rejected."""
        _, _, errors = service.validate_upload(test_image_data, "application/javascript")
        mime_errors = [e for e in errors if e.code == "invalid_mime_type"]
        assert len(mime_errors) == 1

    def test_validate_mime_type_helper(self) -> None:
        """validate_mime_type helper works correctly."""
        kinds = {
            "image": AssetKindConfig(
                kind="image",
                allowed_mime_types=["image/png"],
                max_upload_bytes=1000,
            )
        }

        # Allowed
        errors = validate_mime_type("image/png", kinds)
        assert len(errors) == 0

        # Not allowed
        errors = validate_mime_type("image/bmp", kinds)
        assert len(errors) == 1
        assert errors[0].code == "invalid_mime_type"


# --- TA-0007: Size Limit Tests ---


class TestTA0007SizeLimits:
    """TA-0007: Size limit enforcement."""

    def test_small_image_accepted(self, service: AssetService, test_image_data: bytes) -> None:
        """Small images within limit are accepted."""
        _, _, errors = service.validate_upload(test_image_data, "image/jpeg")
        size_errors = [e for e in errors if e.code == "file_too_large"]
        assert len(size_errors) == 0

    def test_image_over_10mb_rejected(self, service: AssetService) -> None:
        """Images over 10MB are rejected."""
        large_data = b"x" * (10_000_001)  # Just over 10MB
        _, _, errors = service.validate_upload(large_data, "image/jpeg")
        size_errors = [e for e in errors if e.code == "file_too_large"]
        assert len(size_errors) == 1
        assert "10000000" in size_errors[0].message  # Max size in message

    def test_pdf_up_to_50mb_accepted(self, service: AssetService) -> None:
        """PDFs up to 50MB are accepted."""
        large_pdf = b"x" * 49_000_000  # Just under 50MB
        _, _, errors = service.validate_upload(large_pdf, "application/pdf")
        size_errors = [e for e in errors if e.code == "file_too_large"]
        assert len(size_errors) == 0

    def test_pdf_over_50mb_rejected(self, service: AssetService) -> None:
        """PDFs over 50MB are rejected."""
        huge_pdf = b"x" * 50_000_001  # Just over 50MB
        _, _, errors = service.validate_upload(huge_pdf, "application/pdf")
        size_errors = [e for e in errors if e.code == "file_too_large"]
        assert len(size_errors) == 1

    def test_validate_size_helper(self) -> None:
        """validate_size helper works correctly."""
        kinds = {
            "image": AssetKindConfig(
                kind="image",
                allowed_mime_types=["image/png"],
                max_upload_bytes=1000,
            )
        }

        # Within limit
        errors = validate_size(500, "image/png", kinds)
        assert len(errors) == 0

        # Over limit
        errors = validate_size(1500, "image/png", kinds)
        assert len(errors) == 1
        assert errors[0].code == "file_too_large"


# --- TA-0008: SHA256 Integrity Tests ---


class TestTA0008Integrity:
    """TA-0008: SHA256 integrity verification."""

    def test_sha256_computed_on_upload(self, service: AssetService, test_image_data: bytes) -> None:
        """SHA256 is computed during upload."""
        _, sha256, _ = service.validate_upload(test_image_data, "image/jpeg")
        expected = hashlib.sha256(test_image_data).hexdigest()
        assert sha256 == expected

    def test_correct_expected_sha256_passes(
        self, service: AssetService, test_image_data: bytes
    ) -> None:
        """Correct expected SHA256 passes validation."""
        expected = hashlib.sha256(test_image_data).hexdigest()
        _, _, errors = service.validate_upload(
            test_image_data, "image/jpeg", expected_sha256=expected
        )
        integrity_errors = [e for e in errors if e.code == "integrity_mismatch"]
        assert len(integrity_errors) == 0

    def test_wrong_expected_sha256_fails(
        self, service: AssetService, test_image_data: bytes
    ) -> None:
        """Wrong expected SHA256 fails validation."""
        wrong_hash = "0" * 64
        _, _, errors = service.validate_upload(
            test_image_data, "image/jpeg", expected_sha256=wrong_hash
        )
        integrity_errors = [e for e in errors if e.code == "integrity_mismatch"]
        assert len(integrity_errors) == 1
        assert "mismatch" in integrity_errors[0].message.lower()

    def test_compute_sha256_from_bytes(self, test_image_data: bytes) -> None:
        """compute_sha256 works with bytes."""
        data_bytes, sha256 = compute_sha256(test_image_data)
        assert data_bytes == test_image_data
        assert sha256 == hashlib.sha256(test_image_data).hexdigest()

    def test_compute_sha256_from_file_like(self, test_image_data: bytes) -> None:
        """compute_sha256 works with file-like objects."""
        file_like = BytesIO(test_image_data)
        data_bytes, sha256 = compute_sha256(file_like)
        assert data_bytes == test_image_data
        assert sha256 == hashlib.sha256(test_image_data).hexdigest()

    def test_validate_integrity_helper(self) -> None:
        """validate_integrity helper works correctly."""
        actual = "abc123"

        # No expected - always passes
        errors = validate_integrity(None, actual)
        assert len(errors) == 0

        # Matching
        errors = validate_integrity("abc123", actual)
        assert len(errors) == 0

        # Mismatch
        errors = validate_integrity("different", actual)
        assert len(errors) == 1
        assert errors[0].code == "integrity_mismatch"


# --- Upload Integration Tests ---


class TestUploadIntegration:
    """Full upload flow tests."""

    def test_upload_creates_asset_and_version(
        self,
        service: AssetService,
        asset_repo: MockAssetRepo,
        version_repo: MockAssetVersionRepo,
        storage: MockStorage,
        test_image_data: bytes,
    ) -> None:
        """Upload creates asset and version records."""
        user_id = uuid4()

        result, errors = service.upload(
            test_image_data,
            "image/jpeg",
            "test.jpg",
            user_id,
        )

        assert len(errors) == 0
        assert result is not None
        assert result.is_new_asset is True
        assert result.asset.id in asset_repo.assets
        assert len(version_repo.versions) == 1

    def test_upload_stores_in_object_storage(
        self,
        service: AssetService,
        storage: MockStorage,
        test_image_data: bytes,
    ) -> None:
        """Upload stores data in object storage."""
        user_id = uuid4()

        result, _ = service.upload(
            test_image_data,
            "image/jpeg",
            "test.jpg",
            user_id,
        )

        assert result is not None
        assert storage.put_count == 1
        assert result.storage_key in storage.objects

    def test_upload_new_version_increments_number(
        self,
        service: AssetService,
        version_repo: MockAssetVersionRepo,
        test_image_data: bytes,
    ) -> None:
        """New version increments version number."""
        user_id = uuid4()

        # First upload
        result1, _ = service.upload(
            test_image_data,
            "image/jpeg",
            "test.jpg",
            user_id,
        )

        # Second upload to same asset
        result2, _ = service.upload(
            test_image_data + b"modified",
            "image/jpeg",
            "test.jpg",
            user_id,
            asset_id=result1.asset.id,
        )

        assert result1.version.version_number == 1
        assert result2.version.version_number == 2

    def test_upload_sets_latest_pointer(
        self,
        service: AssetService,
        version_repo: MockAssetVersionRepo,
        test_image_data: bytes,
    ) -> None:
        """Upload sets the latest version pointer."""
        user_id = uuid4()

        result, _ = service.upload(
            test_image_data,
            "image/jpeg",
            "test.jpg",
            user_id,
        )

        latest = version_repo.get_latest(result.asset.id)
        assert latest is not None
        assert latest.id == result.version.id

    def test_upload_validation_failure_returns_errors(
        self, service: AssetService, test_image_data: bytes
    ) -> None:
        """Upload validation failure returns errors without storing."""
        user_id = uuid4()

        result, errors = service.upload(
            test_image_data,
            "text/html",  # Invalid MIME type
            "test.html",
            user_id,
        )

        assert result is None
        assert len(errors) > 0

    def test_upload_to_nonexistent_asset_returns_error(
        self, service: AssetService, test_image_data: bytes
    ) -> None:
        """Upload to non-existent asset returns error."""
        user_id = uuid4()
        fake_asset_id = uuid4()

        result, errors = service.upload(
            test_image_data,
            "image/jpeg",
            "test.jpg",
            user_id,
            asset_id=fake_asset_id,
        )

        assert result is None
        assert len(errors) == 1
        assert errors[0].code == "asset_not_found"


# --- Helper Function Tests ---


class TestHelperFunctions:
    """Helper function tests."""

    def test_get_asset_kind_image(self) -> None:
        """get_asset_kind returns 'image' for image MIME types."""
        assert get_asset_kind("image/jpeg", DEFAULT_ASSET_KINDS) == "image"
        assert get_asset_kind("image/png", DEFAULT_ASSET_KINDS) == "image"

    def test_get_asset_kind_pdf(self) -> None:
        """get_asset_kind returns 'pdf' for PDF MIME type."""
        assert get_asset_kind("application/pdf", DEFAULT_ASSET_KINDS) == "pdf"

    def test_get_asset_kind_unknown(self) -> None:
        """get_asset_kind returns None for unknown MIME types."""
        assert get_asset_kind("text/plain", DEFAULT_ASSET_KINDS) is None

    def test_generate_storage_key(self) -> None:
        """generate_storage_key creates correct format."""
        asset_id = uuid4()
        key = generate_storage_key(asset_id, 1, "jpg")

        assert str(asset_id) in key
        assert "v1" in key
        assert key.endswith(".jpg")

    def test_mime_to_extension(self) -> None:
        """mime_to_extension maps correctly."""
        assert mime_to_extension("image/jpeg") == "jpg"
        assert mime_to_extension("image/png") == "png"
        assert mime_to_extension("application/pdf") == "pdf"
        assert mime_to_extension("unknown/type") == "bin"


# --- Version Management Tests ---


class TestVersionManagement:
    """Version management tests."""

    def test_get_latest_version(
        self,
        service: AssetService,
        test_image_data: bytes,
    ) -> None:
        """get_latest_version returns the latest version."""
        user_id = uuid4()

        result, _ = service.upload(
            test_image_data,
            "image/jpeg",
            "test.jpg",
            user_id,
        )

        latest = service.get_latest_version(result.asset.id)
        assert latest is not None
        assert latest.id == result.version.id

    def test_set_latest_version(
        self,
        service: AssetService,
        version_repo: MockAssetVersionRepo,
        test_image_data: bytes,
    ) -> None:
        """set_latest_version changes the latest pointer."""
        user_id = uuid4()

        # Create two versions
        result1, _ = service.upload(
            test_image_data,
            "image/jpeg",
            "test.jpg",
            user_id,
        )
        result2, _ = service.upload(
            test_image_data + b"v2",
            "image/jpeg",
            "test.jpg",
            user_id,
            asset_id=result1.asset.id,
        )

        # Set v1 as latest
        success = service.set_latest_version(result1.asset.id, result1.version.id)
        assert success is True

        latest = service.get_latest_version(result1.asset.id)
        assert latest.id == result1.version.id

    def test_get_versions(
        self,
        service: AssetService,
        test_image_data: bytes,
    ) -> None:
        """get_versions returns all versions."""
        user_id = uuid4()

        result1, _ = service.upload(
            test_image_data,
            "image/jpeg",
            "test.jpg",
            user_id,
        )
        service.upload(
            test_image_data + b"v2",
            "image/jpeg",
            "test.jpg",
            user_id,
            asset_id=result1.asset.id,
        )

        versions = service.get_versions(result1.asset.id)
        assert len(versions) == 2


# --- Factory Tests ---


class TestFactory:
    """Factory function tests."""

    def test_create_asset_service(
        self,
        asset_repo: MockAssetRepo,
        version_repo: MockAssetVersionRepo,
        storage: MockStorage,
    ) -> None:
        """create_asset_service creates configured service."""
        service = create_asset_service(asset_repo, version_repo, storage)
        assert service is not None

    def test_create_asset_service_with_rules(
        self,
        asset_repo: MockAssetRepo,
        version_repo: MockAssetVersionRepo,
        storage: MockStorage,
    ) -> None:
        """create_asset_service accepts rules config."""
        rules = {
            "kinds": {
                "custom": {
                    "allowed_mime_types": ["custom/type"],
                    "max_upload_bytes": 5000,
                }
            }
        }

        service = create_asset_service(asset_repo, version_repo, storage, rules_config=rules)

        # Custom kind should be available
        assert "custom" in service._kinds
