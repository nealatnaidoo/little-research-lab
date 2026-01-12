"""
Tests for Admin Assets API (E2.1).

Test assertions:
- TA-0006: MIME type allowlist enforcement
- TA-0007: Size limit enforcement
- TA-0008: SHA256 integrity verification

These tests verify the AssetService validation logic through the API layer.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from src.components.assets import (
    DEFAULT_ASSET_KINDS,
    AssetService,
    compute_sha256,
    generate_storage_key,
    mime_to_extension,
    validate_integrity,
    validate_mime_type,
    validate_size,
)
from src.core.entities import Asset, AssetVersion

# --- Mock Repositories ---


class MockAssetRepo:
    """In-memory asset repository for testing."""

    def __init__(self) -> None:
        self._assets: dict[UUID, Asset] = {}

    def get_by_id(self, asset_id: UUID) -> Asset | None:
        return self._assets.get(asset_id)

    def save(self, asset: Asset) -> Asset:
        self._assets[asset.id] = asset
        return asset

    def list_all(self) -> list[Asset]:
        return list(self._assets.values())

    def get_latest_version(self, asset_id: UUID) -> AssetVersion | None:
        return None


class MockVersionRepo:
    """In-memory version repository for testing."""

    def __init__(self) -> None:
        self._versions: dict[UUID, AssetVersion] = {}
        self._latest: dict[UUID, UUID] = {}
        self._version_counts: dict[UUID, int] = {}

    def get_by_id(self, version_id: UUID) -> AssetVersion | None:
        return self._versions.get(version_id)

    def get_by_storage_key(self, key: str) -> AssetVersion | None:
        for v in self._versions.values():
            if v.storage_key == key:
                return v
        return None

    def save(self, version: AssetVersion) -> AssetVersion:
        self._versions[version.id] = version
        return version

    def get_versions(self, asset_id: UUID) -> list[AssetVersion]:
        return [v for v in self._versions.values() if v.asset_id == asset_id]

    def get_latest(self, asset_id: UUID) -> AssetVersion | None:
        if asset_id in self._latest:
            return self._versions.get(self._latest[asset_id])
        return None

    def set_latest(self, asset_id: UUID, version_id: UUID) -> None:
        self._latest[asset_id] = version_id
        for v in self._versions.values():
            if v.asset_id == asset_id:
                v.is_latest = v.id == version_id

    def get_next_version_number(self, asset_id: UUID) -> int:
        count = self._version_counts.get(asset_id, 0)
        self._version_counts[asset_id] = count + 1
        return count + 1


class MockStorage:
    """In-memory storage for testing."""

    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}

    def put(
        self,
        key: str,
        data: bytes | Any,
        content_type: str,
        *,
        expected_sha256: str | None = None,
    ) -> None:
        self._data[key] = data if isinstance(data, bytes) else bytes(data)

    def exists(self, key: str) -> bool:
        return key in self._data

    def get(self, key: str) -> bytes | None:
        return self._data.get(key)


# --- Fixtures ---


@pytest.fixture
def mock_asset_repo() -> MockAssetRepo:
    return MockAssetRepo()


@pytest.fixture
def mock_version_repo() -> MockVersionRepo:
    return MockVersionRepo()


@pytest.fixture
def mock_storage() -> MockStorage:
    return MockStorage()


@pytest.fixture
def asset_service(
    mock_asset_repo: MockAssetRepo,
    mock_version_repo: MockVersionRepo,
    mock_storage: MockStorage,
) -> AssetService:
    return AssetService(
        asset_repo=mock_asset_repo,
        version_repo=mock_version_repo,
        storage=mock_storage,
    )


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def valid_image_data() -> bytes:
    """Small valid image data."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Minimal PNG header + padding


@pytest.fixture
def valid_pdf_data() -> bytes:
    """Small valid PDF data."""
    return b"%PDF-1.4" + b"\x00" * 100


# --- TA-0006: MIME Type Allowlist ---


class TestMimeTypeValidation:
    """Test TA-0006: MIME type allowlist enforcement."""

    def test_valid_image_mime_types_accepted(self) -> None:
        """Valid image MIME types are accepted."""
        valid_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
        for mime_type in valid_types:
            errors = validate_mime_type(mime_type, DEFAULT_ASSET_KINDS)
            assert errors == [], f"{mime_type} should be valid"

    def test_valid_pdf_mime_type_accepted(self) -> None:
        """application/pdf is accepted."""
        errors = validate_mime_type("application/pdf", DEFAULT_ASSET_KINDS)
        assert errors == []

    def test_invalid_mime_type_rejected(self) -> None:
        """Invalid MIME types are rejected with error."""
        errors = validate_mime_type("application/javascript", DEFAULT_ASSET_KINDS)
        assert len(errors) == 1
        assert errors[0].code == "invalid_mime_type"

    def test_upload_with_invalid_mime_type_fails(
        self,
        asset_service: AssetService,
        user_id: UUID,
    ) -> None:
        """Upload with invalid MIME type returns validation error."""
        result, errors = asset_service.upload(
            data=b"test data",
            mime_type="text/html",  # Not allowed
            filename="test.html",
            user_id=user_id,
        )

        assert result is None
        assert len(errors) > 0
        assert any(e.code == "invalid_mime_type" for e in errors)

    def test_upload_with_valid_mime_type_succeeds(
        self,
        asset_service: AssetService,
        user_id: UUID,
        valid_image_data: bytes,
    ) -> None:
        """Upload with valid MIME type succeeds."""
        result, errors = asset_service.upload(
            data=valid_image_data,
            mime_type="image/png",
            filename="test.png",
            user_id=user_id,
        )

        assert errors == []
        assert result is not None
        assert result.asset.mime_type == "image/png"


# --- TA-0007: Size Limit Enforcement ---


class TestSizeLimitValidation:
    """Test TA-0007: Size limit enforcement."""

    def test_image_under_limit_accepted(self) -> None:
        """Image under 10MB limit is accepted."""
        size = 5_000_000  # 5MB
        errors = validate_size(size, "image/png", DEFAULT_ASSET_KINDS)
        assert errors == []

    def test_image_over_limit_rejected(self) -> None:
        """Image over 10MB limit is rejected."""
        size = 15_000_000  # 15MB
        errors = validate_size(size, "image/png", DEFAULT_ASSET_KINDS)
        assert len(errors) == 1
        assert errors[0].code == "file_too_large"

    def test_pdf_under_limit_accepted(self) -> None:
        """PDF under 50MB limit is accepted."""
        size = 30_000_000  # 30MB
        errors = validate_size(size, "application/pdf", DEFAULT_ASSET_KINDS)
        assert errors == []

    def test_pdf_over_limit_rejected(self) -> None:
        """PDF over 50MB limit is rejected."""
        size = 60_000_000  # 60MB
        errors = validate_size(size, "application/pdf", DEFAULT_ASSET_KINDS)
        assert len(errors) == 1
        assert errors[0].code == "file_too_large"

    def test_upload_oversized_file_fails(
        self,
        asset_service: AssetService,
        user_id: UUID,
    ) -> None:
        """Upload of oversized file returns validation error."""
        large_data = b"\x00" * 15_000_001  # > 10MB

        result, errors = asset_service.upload(
            data=large_data,
            mime_type="image/png",
            filename="large.png",
            user_id=user_id,
        )

        assert result is None
        assert len(errors) > 0
        assert any(e.code == "file_too_large" for e in errors)


# --- TA-0008: SHA256 Integrity Verification ---


class TestIntegrityVerification:
    """Test TA-0008: SHA256 integrity verification."""

    def test_compute_sha256_consistent(self) -> None:
        """SHA256 computation is consistent."""
        data = b"test data for hashing"
        _, hash1 = compute_sha256(data)
        _, hash2 = compute_sha256(data)
        assert hash1 == hash2

    def test_compute_sha256_different_for_different_data(self) -> None:
        """Different data produces different hashes."""
        _, hash1 = compute_sha256(b"data 1")
        _, hash2 = compute_sha256(b"data 2")
        assert hash1 != hash2

    def test_integrity_check_passes_on_match(self) -> None:
        """Integrity check passes when hashes match."""
        data = b"test data"
        _, actual_hash = compute_sha256(data)
        errors = validate_integrity(actual_hash, actual_hash)
        assert errors == []

    def test_integrity_check_fails_on_mismatch(self) -> None:
        """Integrity check fails when hashes don't match."""
        errors = validate_integrity("expected_hash", "actual_hash")
        assert len(errors) == 1
        assert errors[0].code == "integrity_mismatch"

    def test_integrity_check_skipped_when_no_expected(self) -> None:
        """Integrity check is skipped when no expected hash provided."""
        errors = validate_integrity(None, "any_hash")
        assert errors == []

    def test_upload_with_correct_sha256_succeeds(
        self,
        asset_service: AssetService,
        user_id: UUID,
        valid_image_data: bytes,
    ) -> None:
        """Upload with matching SHA256 succeeds."""
        _, expected_hash = compute_sha256(valid_image_data)

        result, errors = asset_service.upload(
            data=valid_image_data,
            mime_type="image/png",
            filename="test.png",
            user_id=user_id,
            expected_sha256=expected_hash,
        )

        assert errors == []
        assert result is not None
        assert result.sha256 == expected_hash

    def test_upload_with_wrong_sha256_fails(
        self,
        asset_service: AssetService,
        user_id: UUID,
        valid_image_data: bytes,
    ) -> None:
        """Upload with mismatched SHA256 fails."""
        result, errors = asset_service.upload(
            data=valid_image_data,
            mime_type="image/png",
            filename="test.png",
            user_id=user_id,
            expected_sha256="wrong_hash_value",
        )

        assert result is None
        assert len(errors) > 0
        assert any(e.code == "integrity_mismatch" for e in errors)


# --- Upload and Versioning ---


class TestUploadVersioning:
    """Test asset upload and versioning behavior."""

    def test_new_upload_creates_asset_and_version(
        self,
        asset_service: AssetService,
        user_id: UUID,
        valid_image_data: bytes,
    ) -> None:
        """New upload creates both asset and first version."""
        result, errors = asset_service.upload(
            data=valid_image_data,
            mime_type="image/png",
            filename="test.png",
            user_id=user_id,
        )

        assert errors == []
        assert result is not None
        assert result.is_new_asset is True
        assert result.version.version_number == 1
        assert result.version.is_latest is True

    def test_upload_to_existing_asset_creates_new_version(
        self,
        asset_service: AssetService,
        user_id: UUID,
        valid_image_data: bytes,
    ) -> None:
        """Upload to existing asset creates new version."""
        # First upload
        result1, _ = asset_service.upload(
            data=valid_image_data,
            mime_type="image/png",
            filename="v1.png",
            user_id=user_id,
        )
        asset_id = result1.asset.id

        # Second upload to same asset
        result2, errors = asset_service.upload(
            data=valid_image_data + b"modified",
            mime_type="image/png",
            filename="v2.png",
            user_id=user_id,
            asset_id=asset_id,
        )

        assert errors == []
        assert result2 is not None
        assert result2.is_new_asset is False
        assert result2.version.version_number == 2
        assert result2.asset.id == asset_id

    def test_version_number_increments(
        self,
        asset_service: AssetService,
        user_id: UUID,
        valid_image_data: bytes,
    ) -> None:
        """Version numbers increment correctly."""
        result1, _ = asset_service.upload(
            data=valid_image_data,
            mime_type="image/png",
            filename="test.png",
            user_id=user_id,
        )
        asset_id = result1.asset.id

        result2, _ = asset_service.upload(
            data=valid_image_data + b"v2",
            mime_type="image/png",
            filename="test.png",
            user_id=user_id,
            asset_id=asset_id,
        )

        result3, _ = asset_service.upload(
            data=valid_image_data + b"v3",
            mime_type="image/png",
            filename="test.png",
            user_id=user_id,
            asset_id=asset_id,
        )

        assert result1.version.version_number == 1
        assert result2.version.version_number == 2
        assert result3.version.version_number == 3


# --- Storage Key Generation ---


class TestStorageKeyGeneration:
    """Test storage key generation."""

    def test_storage_key_format(self) -> None:
        """Storage key has expected format."""
        asset_id = uuid4()
        key = generate_storage_key(asset_id, 1, "png")
        assert f"assets/{asset_id}" in key
        assert "v1" in key
        assert ".png" in key

    def test_storage_key_unique_per_version(self) -> None:
        """Different versions have different storage keys."""
        asset_id = uuid4()
        key1 = generate_storage_key(asset_id, 1, "png")
        key2 = generate_storage_key(asset_id, 2, "png")
        assert key1 != key2


# --- MIME to Extension ---


class TestMimeToExtension:
    """Test MIME type to extension mapping."""

    def test_known_mime_types(self) -> None:
        """Known MIME types map to correct extensions."""
        assert mime_to_extension("image/jpeg") == "jpg"
        assert mime_to_extension("image/png") == "png"
        assert mime_to_extension("image/webp") == "webp"
        assert mime_to_extension("image/gif") == "gif"
        assert mime_to_extension("application/pdf") == "pdf"

    def test_unknown_mime_type(self) -> None:
        """Unknown MIME types default to 'bin'."""
        assert mime_to_extension("application/unknown") == "bin"


# --- Latest Version Management ---


class TestLatestVersionManagement:
    """Test /latest pointer management."""

    def test_new_version_becomes_latest(
        self,
        asset_service: AssetService,
        user_id: UUID,
        valid_image_data: bytes,
    ) -> None:
        """Newly uploaded version becomes latest."""
        result, _ = asset_service.upload(
            data=valid_image_data,
            mime_type="image/png",
            filename="test.png",
            user_id=user_id,
        )

        assert result.version.is_latest is True

        latest = asset_service.get_latest_version(result.asset.id)
        assert latest is not None
        assert latest.id == result.version.id

    def test_set_latest_version(
        self,
        asset_service: AssetService,
        user_id: UUID,
        valid_image_data: bytes,
    ) -> None:
        """Can set a specific version as latest."""
        # Create first version
        result1, _ = asset_service.upload(
            data=valid_image_data,
            mime_type="image/png",
            filename="test.png",
            user_id=user_id,
        )
        asset_id = result1.asset.id
        v1_id = result1.version.id

        # Create second version (becomes latest)
        result2, _ = asset_service.upload(
            data=valid_image_data + b"v2",
            mime_type="image/png",
            filename="test.png",
            user_id=user_id,
            asset_id=asset_id,
        )

        # Set v1 as latest
        success = asset_service.set_latest_version(asset_id, v1_id)
        assert success is True

        latest = asset_service.get_latest_version(asset_id)
        assert latest is not None
        assert latest.id == v1_id

    def test_set_latest_invalid_version_fails(
        self,
        asset_service: AssetService,
        user_id: UUID,
        valid_image_data: bytes,
    ) -> None:
        """Setting non-existent version as latest fails."""
        result, _ = asset_service.upload(
            data=valid_image_data,
            mime_type="image/png",
            filename="test.png",
            user_id=user_id,
        )

        success = asset_service.set_latest_version(result.asset.id, uuid4())
        assert success is False
