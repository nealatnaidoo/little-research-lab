"""
v3 Object Storage Adapter Interface (P2).

Protocol-based interface for object storage operations.
Implementations: Local filesystem (now), S3-compatible (future).

Spec refs: P2, E3, E4, R2
Test assertions: TA-0104 (immutable key)

Invariants:
- I3: AssetVersion bytes are immutable; sha256 stored equals sha256 served
- Keys once written cannot be overwritten (immutability guarantee)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol


@dataclass
class StoredObject:
    """Metadata for a stored object."""

    key: str
    size_bytes: int
    content_type: str
    sha256: str
    etag: str


class StoragePort(Protocol):
    """
    Object storage port interface.

    Provides immutable blob storage with content-addressed keys.
    Supports local filesystem or S3-compatible backends.
    """

    def put(
        self,
        key: str,
        data: bytes | BinaryIO,
        content_type: str,
        *,
        expected_sha256: str | None = None,
    ) -> StoredObject:
        """
        Store object bytes under the given key.

        Args:
            key: Storage key (must be unique and immutable once written)
            data: Object bytes or file-like object
            content_type: MIME type
            expected_sha256: Optional hash to verify data integrity

        Returns:
            StoredObject with metadata including computed sha256

        Raises:
            KeyExistsError: If key already exists (immutability guarantee)
            IntegrityError: If expected_sha256 doesn't match actual hash
        """
        ...

    def get(self, key: str) -> tuple[bytes, StoredObject]:
        """
        Retrieve object bytes by key.

        Args:
            key: Storage key

        Returns:
            Tuple of (bytes, metadata)

        Raises:
            KeyNotFoundError: If key doesn't exist
        """
        ...

    def get_stream(self, key: str) -> tuple[BinaryIO, StoredObject]:
        """
        Get a streaming handle to object bytes.

        Useful for large files to avoid loading into memory.

        Args:
            key: Storage key

        Returns:
            Tuple of (file-like object, metadata)

        Raises:
            KeyNotFoundError: If key doesn't exist
        """
        ...

    def exists(self, key: str) -> bool:
        """Check if key exists in storage."""
        ...

    def delete(self, key: str) -> bool:
        """
        Delete object by key.

        Note: In production, this should be disabled for immutable versions.
        Only enabled for cleanup of orphaned/draft files.

        Returns:
            True if deleted, False if key didn't exist
        """
        ...

    def get_metadata(self, key: str) -> StoredObject | None:
        """
        Get object metadata without fetching bytes.

        Returns:
            StoredObject metadata or None if key doesn't exist
        """
        ...

    def get_public_url(self, key: str) -> str | None:
        """
        Get public URL for the object if available.

        For local storage, this returns None (use app routes instead).
        For S3, this returns the object URL.

        Returns:
            Public URL or None if not applicable
        """
        ...


class StorageError(Exception):
    """Base class for storage errors."""


class KeyExistsError(StorageError):
    """Raised when attempting to write to an existing key (immutability violation)."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Key already exists (immutable): {key}")


class KeyNotFoundError(StorageError):
    """Raised when key doesn't exist."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Key not found: {key}")


class IntegrityError(StorageError):
    """Raised when data integrity check fails."""

    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"Integrity check failed: expected {expected}, got {actual}")
