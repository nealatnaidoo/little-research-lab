"""
Assets component input/output models.

Spec refs: E2.1, E2.2, E2.3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import BinaryIO
from uuid import UUID

from src.core.entities import Asset, AssetVersion

# --- Validation Error ---


@dataclass(frozen=True)
class AssetValidationError:
    """Asset validation error with actionable message."""

    code: str
    message: str
    field: str = "file"


# --- Input Models ---


@dataclass(frozen=True)
class UploadAssetInput:
    """Input for uploading an asset."""

    data: bytes | BinaryIO
    filename: str
    content_type: str
    user_id: UUID
    asset_id: UUID | None = None  # None for new asset, UUID for new version
    expected_sha256: str | None = None


@dataclass(frozen=True)
class GetAssetInput:
    """Input for retrieving an asset."""

    asset_id: UUID


@dataclass(frozen=True)
class ListAssetsInput:
    """Input for listing assets."""

    user_id: UUID | None = None  # Filter by creator
    mime_type_prefix: str | None = None  # e.g., "image/" for all images
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetVersionInput:
    """Input for retrieving a specific version."""

    version_id: UUID


@dataclass(frozen=True)
class ListVersionsInput:
    """Input for listing versions of an asset."""

    asset_id: UUID


@dataclass(frozen=True)
class SetLatestVersionInput:
    """Input for setting the latest version."""

    asset_id: UUID
    version_id: UUID


# --- Configuration Models ---


@dataclass(frozen=True)
class AssetKindConfig:
    """Configuration for an asset kind (image, pdf, etc.)."""

    kind: str
    allowed_mime_types: list[str]
    max_upload_bytes: int


# --- Output Models ---


@dataclass(frozen=True)
class AssetOutput:
    """Output containing a single asset."""

    asset: Asset | None
    errors: list[AssetValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class AssetListOutput:
    """Output containing a list of assets."""

    items: list[Asset]
    total: int
    limit: int
    offset: int
    errors: list[AssetValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class VersionOutput:
    """Output containing a single version."""

    version: AssetVersion | None
    errors: list[AssetValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class VersionListOutput:
    """Output containing a list of versions."""

    items: list[AssetVersion]
    errors: list[AssetValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class UploadOutput:
    """Output from upload operation."""

    asset: Asset | None = None
    version: AssetVersion | None = None
    is_new_asset: bool = False
    sha256: str = ""
    storage_key: str = ""
    errors: list[AssetValidationError] = field(default_factory=list)
    success: bool = True


@dataclass(frozen=True)
class SetLatestOutput:
    """Output from set latest version operation."""

    success: bool = True
    errors: list[AssetValidationError] = field(default_factory=list)
