"""
Local Filesystem Storage Adapter (P2 Implementation).

Implements the StoragePort interface using local filesystem.
Provides immutable blob storage for development and single-server deployments.

Spec refs: P2, E3, E4, R2
Test assertions: TA-0104 (immutable key)

Invariants:
- I3: AssetVersion bytes are immutable; sha256 stored equals sha256 served
- Keys once written cannot be overwritten
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import BinaryIO

from src.core.ports.storage import (
    IntegrityError,
    KeyExistsError,
    KeyNotFoundError,
    StorageError,
    StoredObject,
)


class LocalFileStorage:
    """
    Local filesystem implementation of StoragePort.

    Stores objects as files with accompanying metadata JSON.
    Directory structure: {base_path}/{key_prefix}/{key_suffix}

    Example key: "assets/abc123/v1" -> {base_path}/assets/abc123/v1.bin + .meta.json
    """

    def __init__(
        self,
        base_path: str | Path,
        *,
        create_dirs: bool = True,
        allow_delete: bool = False,
    ) -> None:
        """
        Initialize local file storage.

        Args:
            base_path: Root directory for storage
            create_dirs: Whether to create directories if they don't exist
            allow_delete: Whether to allow deletion (disabled for production immutability)
        """
        self.base_path = Path(base_path)
        self.allow_delete = allow_delete

        if create_dirs:
            self.base_path.mkdir(parents=True, exist_ok=True)

    def _key_to_paths(self, key: str) -> tuple[Path, Path]:
        """Convert storage key to file paths (data and metadata)."""
        # Sanitize key to prevent directory traversal
        safe_key = key.replace("..", "").lstrip("/")
        data_path = self.base_path / f"{safe_key}.bin"
        meta_path = self.base_path / f"{safe_key}.meta.json"
        return data_path, meta_path

    def _compute_sha256(self, data: bytes | BinaryIO) -> tuple[bytes, str]:
        """Compute SHA-256 hash of data, returning (bytes, hex_hash)."""
        hasher = hashlib.sha256()

        if isinstance(data, bytes):
            hasher.update(data)
            return data, hasher.hexdigest()

        # Stream from file-like object
        chunks = []
        while True:
            chunk = data.read(8192)
            if not chunk:
                break
            chunks.append(chunk)
            hasher.update(chunk)

        return b"".join(chunks), hasher.hexdigest()

    def _compute_etag(self, sha256_hex: str) -> str:
        """Compute ETag from sha256 hash."""
        return f'"{sha256_hex[:32]}"'

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

        Enforces immutability: raises KeyExistsError if key already exists.
        """
        data_path, meta_path = self._key_to_paths(key)

        # Immutability check: key must not exist
        if data_path.exists():
            raise KeyExistsError(key)

        # Compute hash and verify integrity
        data_bytes, sha256_hex = self._compute_sha256(data)

        if expected_sha256 and sha256_hex != expected_sha256:
            raise IntegrityError(expected_sha256, sha256_hex)

        # Create parent directories
        data_path.parent.mkdir(parents=True, exist_ok=True)

        # Write data file
        with open(data_path, "wb") as f:
            f.write(data_bytes)

        # Write metadata
        metadata = StoredObject(
            key=key,
            size_bytes=len(data_bytes),
            content_type=content_type,
            sha256=sha256_hex,
            etag=self._compute_etag(sha256_hex),
        )

        with open(meta_path, "w") as f:
            json.dump(
                {
                    "key": metadata.key,
                    "size_bytes": metadata.size_bytes,
                    "content_type": metadata.content_type,
                    "sha256": metadata.sha256,
                    "etag": metadata.etag,
                },
                f,
            )

        return metadata

    def get(self, key: str) -> tuple[bytes, StoredObject]:
        """Retrieve object bytes by key."""
        data_path, meta_path = self._key_to_paths(key)

        if not data_path.exists():
            raise KeyNotFoundError(key)

        with open(data_path, "rb") as f:
            data = f.read()

        metadata = self._load_metadata(meta_path, key)

        # Verify integrity on read (I3)
        actual_sha256 = hashlib.sha256(data).hexdigest()
        if actual_sha256 != metadata.sha256:
            raise IntegrityError(metadata.sha256, actual_sha256)

        return data, metadata

    def get_stream(self, key: str) -> tuple[BinaryIO, StoredObject]:
        """Get a streaming handle to object bytes."""
        data_path, meta_path = self._key_to_paths(key)

        if not data_path.exists():
            raise KeyNotFoundError(key)

        metadata = self._load_metadata(meta_path, key)

        # Return file handle (caller responsible for closing)
        return open(data_path, "rb"), metadata

    def exists(self, key: str) -> bool:
        """Check if key exists in storage."""
        data_path, _ = self._key_to_paths(key)
        return data_path.exists()

    def delete(self, key: str) -> bool:
        """
        Delete object by key.

        Only allowed if allow_delete=True (development/cleanup use only).
        Production should keep immutability.
        """
        if not self.allow_delete:
            raise StorageError("Delete not allowed: storage is configured as immutable")

        data_path, meta_path = self._key_to_paths(key)

        if not data_path.exists():
            return False

        data_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

        return True

    def get_metadata(self, key: str) -> StoredObject | None:
        """Get object metadata without fetching bytes."""
        data_path, meta_path = self._key_to_paths(key)

        if not data_path.exists():
            return None

        return self._load_metadata(meta_path, key)

    def get_public_url(self, key: str) -> str | None:
        """
        Get public URL for the object.

        Local storage doesn't have public URLs; use app routes instead.
        """
        return None

    def _load_metadata(self, meta_path: Path, key: str) -> StoredObject:
        """Load metadata from JSON file."""
        if not meta_path.exists():
            # Reconstruct metadata if missing (backward compatibility)
            data_path = meta_path.with_suffix(".bin")
            with open(data_path, "rb") as f:
                data = f.read()
            sha256_hex = hashlib.sha256(data).hexdigest()
            return StoredObject(
                key=key,
                size_bytes=len(data),
                content_type="application/octet-stream",
                sha256=sha256_hex,
                etag=self._compute_etag(sha256_hex),
            )

        with open(meta_path) as f:
            meta = json.load(f)

        return StoredObject(
            key=meta["key"],
            size_bytes=meta["size_bytes"],
            content_type=meta["content_type"],
            sha256=meta["sha256"],
            etag=meta["etag"],
        )


def create_local_storage(
    base_path: str | Path | None = None,
    *,
    env_var: str = "STORAGE_PATH",
    default_path: str = "./storage",
    allow_delete: bool = False,
) -> LocalFileStorage:
    """
    Factory function to create LocalFileStorage from config.

    Args:
        base_path: Explicit base path (overrides env var)
        env_var: Environment variable name for storage path
        default_path: Default path if not configured
        allow_delete: Whether to allow deletion

    Returns:
        Configured LocalFileStorage instance
    """
    if base_path is None:
        base_path = os.environ.get(env_var, default_path)

    return LocalFileStorage(base_path, allow_delete=allow_delete)
