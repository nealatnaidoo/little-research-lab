"""
TA-0104: Object Storage immutable key tests.

Verifies that the storage adapter enforces immutability and integrity guarantees.
These tests ensure R2 invariant: AssetVersion bytes are immutable.
"""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

import pytest

from src.adapters.local_storage import LocalFileStorage, create_local_storage
from src.core.ports.storage import IntegrityError, KeyExistsError, KeyNotFoundError


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    """Create a test storage instance."""
    return LocalFileStorage(tmp_path, allow_delete=True)


@pytest.fixture
def immutable_storage(tmp_path: Path) -> LocalFileStorage:
    """Create a test storage instance with delete disabled (production mode)."""
    return LocalFileStorage(tmp_path, allow_delete=False)


class TestImmutableKeyGuarantee:
    """TA-0104: Immutable key guarantee tests (R2)."""

    def test_key_cannot_be_overwritten(self, storage: LocalFileStorage) -> None:
        """Once a key is written, it cannot be overwritten (I3, R2)."""
        key = "assets/test/v1"
        data1 = b"original content"
        data2 = b"different content"

        # First write succeeds
        storage.put(key, data1, "text/plain")

        # Second write to same key raises KeyExistsError
        with pytest.raises(KeyExistsError) as exc_info:
            storage.put(key, data2, "text/plain")

        assert exc_info.value.key == key

    def test_stored_bytes_match_retrieved_bytes(self, storage: LocalFileStorage) -> None:
        """Stored bytes exactly match retrieved bytes (I3)."""
        key = "assets/integrity/v1"
        original_data = b"test content for integrity check" * 100

        stored = storage.put(key, original_data, "application/octet-stream")
        retrieved_data, metadata = storage.get(key)

        assert retrieved_data == original_data
        assert metadata.sha256 == stored.sha256
        assert metadata.size_bytes == len(original_data)

    def test_sha256_computed_correctly(self, storage: LocalFileStorage) -> None:
        """SHA-256 hash is computed correctly (I3)."""
        key = "assets/hash/v1"
        data = b"content to hash"
        expected_sha256 = hashlib.sha256(data).hexdigest()

        result = storage.put(key, data, "text/plain")

        assert result.sha256 == expected_sha256

    def test_integrity_verified_on_read(self, storage: LocalFileStorage) -> None:
        """Integrity is verified when reading (I3)."""
        key = "assets/corrupt/v1"
        data = b"original content"
        storage.put(key, data, "text/plain")

        # Manually corrupt the file
        data_path = storage.base_path / f"{key}.bin"
        with open(data_path, "wb") as f:
            f.write(b"corrupted content")

        # Read should detect corruption
        with pytest.raises(IntegrityError):
            storage.get(key)

    def test_expected_sha256_verified_on_write(self, storage: LocalFileStorage) -> None:
        """Expected SHA-256 is verified during write."""
        key = "assets/verify/v1"
        data = b"test content"
        correct_sha256 = hashlib.sha256(data).hexdigest()
        wrong_sha256 = "0" * 64

        # Correct hash succeeds
        result = storage.put(key, data, "text/plain", expected_sha256=correct_sha256)
        assert result.sha256 == correct_sha256

        # Wrong hash fails
        key2 = "assets/verify/v2"
        with pytest.raises(IntegrityError) as exc_info:
            storage.put(key2, data, "text/plain", expected_sha256=wrong_sha256)

        assert exc_info.value.expected == wrong_sha256
        assert exc_info.value.actual == correct_sha256


class TestStorageOperations:
    """Basic storage operation tests."""

    def test_put_and_get_bytes(self, storage: LocalFileStorage) -> None:
        """Put and get operations work with byte arrays."""
        key = "test/bytes"
        data = b"hello world"

        result = storage.put(key, data, "text/plain")
        assert result.key == key
        assert result.size_bytes == len(data)

        retrieved, metadata = storage.get(key)
        assert retrieved == data

    def test_put_and_get_stream(self, storage: LocalFileStorage) -> None:
        """Put works with file-like objects."""
        key = "test/stream"
        data = b"streamed content"
        stream = BytesIO(data)

        result = storage.put(key, stream, "application/octet-stream")
        assert result.size_bytes == len(data)

        retrieved, _ = storage.get(key)
        assert retrieved == data

    def test_get_stream(self, storage: LocalFileStorage) -> None:
        """get_stream returns a file handle."""
        key = "test/get-stream"
        data = b"content for streaming"
        storage.put(key, data, "text/plain")

        handle, metadata = storage.get_stream(key)
        try:
            content = handle.read()
            assert content == data
        finally:
            handle.close()

    def test_exists(self, storage: LocalFileStorage) -> None:
        """Exists check works correctly."""
        key = "test/exists"
        data = b"test"

        assert storage.exists(key) is False

        storage.put(key, data, "text/plain")

        assert storage.exists(key) is True

    def test_get_metadata(self, storage: LocalFileStorage) -> None:
        """Metadata can be retrieved without fetching bytes."""
        key = "test/metadata"
        data = b"test content"
        content_type = "application/json"

        storage.put(key, data, content_type)

        metadata = storage.get_metadata(key)
        assert metadata is not None
        assert metadata.content_type == content_type
        assert metadata.size_bytes == len(data)

    def test_get_metadata_missing_key(self, storage: LocalFileStorage) -> None:
        """get_metadata returns None for missing key."""
        metadata = storage.get_metadata("nonexistent/key")
        assert metadata is None

    def test_get_missing_key_raises(self, storage: LocalFileStorage) -> None:
        """Getting a missing key raises KeyNotFoundError."""
        with pytest.raises(KeyNotFoundError):
            storage.get("nonexistent/key")

    def test_delete_when_allowed(self, storage: LocalFileStorage) -> None:
        """Delete works when allowed."""
        key = "test/delete"
        storage.put(key, b"test", "text/plain")

        assert storage.exists(key)
        result = storage.delete(key)
        assert result is True
        assert not storage.exists(key)

    def test_delete_missing_key(self, storage: LocalFileStorage) -> None:
        """Deleting a missing key returns False."""
        result = storage.delete("nonexistent/key")
        assert result is False

    def test_delete_disabled_raises(self, immutable_storage: LocalFileStorage) -> None:
        """Delete raises when disabled (production mode)."""
        key = "test/immutable"
        immutable_storage.put(key, b"test", "text/plain")

        from src.core.ports.storage import StorageError

        with pytest.raises(StorageError, match="Delete not allowed"):
            immutable_storage.delete(key)


class TestKeyPathSafety:
    """Key path safety tests."""

    def test_key_with_path_traversal_blocked(self, storage: LocalFileStorage) -> None:
        """Path traversal attempts are sanitized."""
        # Attempting to write outside base_path
        key = "../../../tmp/test_traversal"
        data = b"should be inside base_path"

        # Should sanitize to safe path
        storage.put(key, data, "text/plain")
        # Key is sanitized - file should be retrievable
        retrieved, _ = storage.get(key)
        assert retrieved == data

        # Verify file is stored inside base_path, not at traversal target
        # The sanitized path should be inside storage base_path
        data_path = storage.base_path / "tmp/test_traversal.bin"
        assert data_path.exists() or (storage.base_path / "test_traversal.bin").exists()

    def test_key_with_nested_path(self, storage: LocalFileStorage) -> None:
        """Nested paths are created correctly."""
        key = "assets/images/2026/01/test.png"
        data = b"image data"

        storage.put(key, data, "image/png")
        assert storage.exists(key)

        retrieved, _ = storage.get(key)
        assert retrieved == data


class TestEtagGeneration:
    """ETag generation tests."""

    def test_etag_format(self, storage: LocalFileStorage) -> None:
        """ETag is properly formatted."""
        key = "test/etag"
        data = b"test content"

        result = storage.put(key, data, "text/plain")

        # ETag should be quoted string
        assert result.etag.startswith('"')
        assert result.etag.endswith('"')
        # ETag should be derived from sha256
        assert result.etag.strip('"') == result.sha256[:32]

    def test_etag_stable_for_same_content(self, storage: LocalFileStorage) -> None:
        """Same content produces same ETag."""
        data = b"consistent content"

        result1 = storage.put("test/etag1", data, "text/plain")
        result2 = storage.put("test/etag2", data, "text/plain")

        assert result1.etag == result2.etag


class TestFactoryFunction:
    """Factory function tests."""

    def test_create_local_storage_with_path(self, tmp_path: Path) -> None:
        """Factory creates storage with explicit path."""
        storage = create_local_storage(tmp_path, allow_delete=True)
        assert storage.base_path == tmp_path

    def test_create_local_storage_from_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Factory creates storage from environment variable."""
        monkeypatch.setenv("STORAGE_PATH", str(tmp_path))

        storage = create_local_storage()
        assert storage.base_path == tmp_path
