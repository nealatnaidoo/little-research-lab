"""
Assets component port definitions.

Spec refs: E2.1, E2.2, E2.3
"""

from __future__ import annotations

from typing import Any, BinaryIO, Protocol
from uuid import UUID

from src.core.entities import Asset, AssetVersion


class AssetRepoPort(Protocol):
    """Repository interface for asset metadata."""

    def get_by_id(self, asset_id: UUID) -> Asset | None:
        """Get asset by ID."""
        ...

    def save(self, asset: Asset) -> Asset:
        """Save or update asset."""
        ...

    def list(
        self,
        *,
        user_id: UUID | None = None,
        mime_type_prefix: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Asset], int]:
        """List assets with filters. Returns (items, total_count)."""
        ...


class VersionRepoPort(Protocol):
    """Repository interface for asset versions."""

    def get_by_id(self, version_id: UUID) -> AssetVersion | None:
        """Get version by ID."""
        ...

    def get_by_storage_key(self, key: str) -> AssetVersion | None:
        """Get version by storage key."""
        ...

    def save(self, version: AssetVersion) -> AssetVersion:
        """Save version."""
        ...

    def get_versions(self, asset_id: UUID) -> list[AssetVersion]:
        """Get all versions of an asset."""
        ...

    def get_latest(self, asset_id: UUID) -> AssetVersion | None:
        """Get the version marked as latest."""
        ...

    def set_latest(self, asset_id: UUID, version_id: UUID) -> None:
        """Set a version as the latest."""
        ...

    def get_next_version_number(self, asset_id: UUID) -> int:
        """Get the next version number for an asset."""
        ...


class StoragePort(Protocol):
    """Object storage interface for blob data."""

    def put(
        self,
        key: str,
        data: bytes | BinaryIO,
        content_type: str,
        *,
        expected_sha256: str | None = None,
    ) -> Any:
        """Store data under key."""
        ...

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...

    def get(self, key: str) -> bytes | None:
        """Get data by key."""
        ...


class RulesPort(Protocol):
    """Port for accessing asset rules configuration."""

    def get_allowed_mime_types(self, kind: str) -> list[str]:
        """Get allowed MIME types for an asset kind."""
        ...

    def get_max_upload_bytes(self, kind: str) -> int:
        """Get max upload size for an asset kind."""
        ...

    def get_asset_kinds(self) -> dict[str, Any]:
        """Get all asset kind configurations."""
        ...
