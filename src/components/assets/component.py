"""
Assets component - Asset upload, storage, and versioning.

Spec refs: E2.1, E2.2, E2.3
Test assertions: TA-0006, TA-0007, TA-0008

Provides asset upload with validation, version management, and immutable storage.

Invariants:
- I1: MIME type must be in allowlist (TA-0006)
- I2: Size must not exceed limit (TA-0007)
- I3: SHA256 verified on upload (TA-0008)
- I4: Blobs are immutable once stored
- I5: Versions are append-only
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, BinaryIO
from uuid import UUID, uuid4

from src.core.entities import Asset, AssetVersion

from .models import (
    AssetKindConfig,
    AssetListOutput,
    AssetOutput,
    AssetValidationError,
    GetAssetInput,
    GetVersionInput,
    ListAssetsInput,
    ListVersionsInput,
    SetLatestOutput,
    SetLatestVersionInput,
    UploadAssetInput,
    UploadOutput,
    VersionListOutput,
    VersionOutput,
)
from .ports import AssetRepoPort, RulesPort, StoragePort, VersionRepoPort

# --- Default Configuration ---

DEFAULT_ASSET_KINDS: dict[str, AssetKindConfig] = {
    "image": AssetKindConfig(
        kind="image",
        allowed_mime_types=["image/jpeg", "image/png", "image/webp", "image/gif"],
        max_upload_bytes=10_000_000,  # 10MB
    ),
    "pdf": AssetKindConfig(
        kind="pdf",
        allowed_mime_types=["application/pdf"],
        max_upload_bytes=50_000_000,  # 50MB
    ),
}


# --- Helper Functions ---


def compute_sha256(data: bytes | BinaryIO) -> tuple[bytes, str]:
    """
    Compute SHA256 hash of data (TA-0008).

    Returns tuple of (data_bytes, sha256_hex).
    """
    if isinstance(data, bytes):
        data_bytes = data
    else:
        # Read from file-like object
        data_bytes = data.read()
        if hasattr(data, "seek"):
            data.seek(0)

    sha256_hex = hashlib.sha256(data_bytes).hexdigest()
    return data_bytes, sha256_hex


def get_asset_kind(
    mime_type: str,
    kinds: dict[str, AssetKindConfig],
) -> str | None:
    """Determine asset kind from MIME type."""
    for kind, config in kinds.items():
        if mime_type in config.allowed_mime_types:
            return kind
    return None


def generate_storage_key(
    asset_id: UUID,
    version_number: int,
    extension: str,
) -> str:
    """
    Generate immutable storage key for a version.

    Format: assets/{asset_id}/v{version}/{asset_id}_v{version}.{ext}
    """
    return f"assets/{asset_id}/v{version_number}/{asset_id}_v{version_number}.{extension}"


def mime_to_extension(mime_type: str) -> str:
    """Get file extension from MIME type."""
    mapping = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
        "application/pdf": "pdf",
    }
    return mapping.get(mime_type, "bin")


# --- Validation Functions ---


def validate_mime_type(
    mime_type: str,
    kinds: dict[str, AssetKindConfig],
) -> list[AssetValidationError]:
    """
    Validate MIME type against allowlist (TA-0006).

    Returns list of errors (empty if valid).
    """
    errors: list[AssetValidationError] = []

    all_allowed: list[str] = []
    for config in kinds.values():
        all_allowed.extend(config.allowed_mime_types)

    if mime_type not in all_allowed:
        errors.append(
            AssetValidationError(
                code="invalid_mime_type",
                message=(
                    f"MIME type '{mime_type}' is not allowed. "
                    f"Allowed types: {', '.join(sorted(set(all_allowed)))}"
                ),
                field="content_type",
            )
        )

    return errors


def validate_size(
    size: int,
    mime_type: str,
    kinds: dict[str, AssetKindConfig],
) -> list[AssetValidationError]:
    """
    Validate file size against limits (TA-0007).

    Returns list of errors (empty if valid).
    """
    errors: list[AssetValidationError] = []

    kind_name = get_asset_kind(mime_type, kinds)
    if kind_name and kind_name in kinds:
        max_size = kinds[kind_name].max_upload_bytes
        if size > max_size:
            errors.append(
                AssetValidationError(
                    code="file_too_large",
                    message=(
                        f"File size {size} bytes exceeds maximum of "
                        f"{max_size} bytes for {kind_name}"
                    ),
                    field="file",
                )
            )

    return errors


def validate_integrity(
    expected_sha256: str | None,
    actual_sha256: str,
) -> list[AssetValidationError]:
    """
    Validate SHA256 integrity (TA-0008).

    Returns list of errors (empty if valid).
    """
    errors: list[AssetValidationError] = []

    if expected_sha256 and expected_sha256 != actual_sha256:
        errors.append(
            AssetValidationError(
                code="integrity_mismatch",
                message=f"SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}",
                field="sha256",
            )
        )

    return errors


def _get_kinds_config(rules: RulesPort | None) -> dict[str, AssetKindConfig]:
    """Build asset kinds configuration from rules or defaults."""
    if rules is None:
        return DEFAULT_ASSET_KINDS.copy()

    try:
        kinds_config = rules.get_asset_kinds()
        result: dict[str, AssetKindConfig] = {}
        for kind_name, config in kinds_config.items():
            result[kind_name] = AssetKindConfig(
                kind=kind_name,
                allowed_mime_types=config.get("allowed_mime_types", []),
                max_upload_bytes=config.get("max_upload_bytes", 10_000_000),
            )
        return result if result else DEFAULT_ASSET_KINDS.copy()
    except (AttributeError, TypeError):
        return DEFAULT_ASSET_KINDS.copy()


# --- Component Entry Points ---


def run_get(
    inp: GetAssetInput,
    *,
    asset_repo: AssetRepoPort,
) -> AssetOutput:
    """
    Get asset by ID.

    Args:
        inp: Input containing asset_id.
        asset_repo: Asset repository port.

    Returns:
        AssetOutput with asset or error.
    """
    asset = asset_repo.get_by_id(inp.asset_id)
    if asset is None:
        return AssetOutput(
            asset=None,
            errors=[
                AssetValidationError(
                    code="not_found",
                    message=f"Asset {inp.asset_id} not found",
                    field="asset_id",
                )
            ],
            success=False,
        )

    return AssetOutput(asset=asset, errors=[], success=True)


def run_list(
    inp: ListAssetsInput,
    *,
    asset_repo: AssetRepoPort,
) -> AssetListOutput:
    """
    List assets with filters.

    Args:
        inp: Input containing filters.
        asset_repo: Asset repository port.

    Returns:
        AssetListOutput with items and pagination.
    """
    items, total = asset_repo.list(
        user_id=inp.user_id,
        mime_type_prefix=inp.mime_type_prefix,
        limit=inp.limit,
        offset=inp.offset,
    )

    return AssetListOutput(
        items=items,
        total=total,
        limit=inp.limit,
        offset=inp.offset,
        errors=[],
        success=True,
    )


def run_get_version(
    inp: GetVersionInput,
    *,
    version_repo: VersionRepoPort,
) -> VersionOutput:
    """
    Get a specific version by ID.

    Args:
        inp: Input containing version_id.
        version_repo: Version repository port.

    Returns:
        VersionOutput with version or error.
    """
    version = version_repo.get_by_id(inp.version_id)
    if version is None:
        return VersionOutput(
            version=None,
            errors=[
                AssetValidationError(
                    code="not_found",
                    message=f"Version {inp.version_id} not found",
                    field="version_id",
                )
            ],
            success=False,
        )

    return VersionOutput(version=version, errors=[], success=True)


def run_list_versions(
    inp: ListVersionsInput,
    *,
    version_repo: VersionRepoPort,
) -> VersionListOutput:
    """
    List all versions of an asset.

    Args:
        inp: Input containing asset_id.
        version_repo: Version repository port.

    Returns:
        VersionListOutput with versions.
    """
    versions = version_repo.get_versions(inp.asset_id)
    return VersionListOutput(items=versions, errors=[], success=True)


def run_upload(
    inp: UploadAssetInput,
    *,
    asset_repo: AssetRepoPort,
    version_repo: VersionRepoPort,
    storage: StoragePort,
    rules: RulesPort | None = None,
) -> UploadOutput:
    """
    Upload an asset or create a new version.

    Args:
        inp: Input containing data, filename, content_type, etc.
        asset_repo: Asset repository port.
        version_repo: Version repository port.
        storage: Storage port for blob data.
        rules: Optional rules port for configuration.

    Returns:
        UploadOutput with asset, version, and metadata.
    """
    kinds = _get_kinds_config(rules)

    # Read data and compute hash
    data_bytes, sha256 = compute_sha256(inp.data)
    size = len(data_bytes)

    errors: list[AssetValidationError] = []

    # Validate MIME type (TA-0006)
    errors.extend(validate_mime_type(inp.content_type, kinds))

    # Validate size (TA-0007)
    errors.extend(validate_size(size, inp.content_type, kinds))

    # Validate integrity (TA-0008)
    errors.extend(validate_integrity(inp.expected_sha256, sha256))

    if errors:
        return UploadOutput(errors=errors, success=False)

    is_new_asset = inp.asset_id is None
    asset_id: UUID

    # Create or get asset
    if is_new_asset:
        asset = Asset(
            id=uuid4(),
            filename_original=inp.filename,
            mime_type=inp.content_type,
            size_bytes=size,
            sha256=sha256,
            storage_path="",  # Will be set after version creation
            created_by_user_id=inp.user_id,
        )
        asset = asset_repo.save(asset)
        asset_id = asset.id
    else:
        asset_id = inp.asset_id  # type: ignore[assignment]
        existing = asset_repo.get_by_id(asset_id)
        if existing is None:
            return UploadOutput(
                errors=[
                    AssetValidationError(
                        code="asset_not_found",
                        message=f"Asset {asset_id} not found",
                        field="asset_id",
                    )
                ],
                success=False,
            )
        asset = existing

    # Get next version number
    version_number = version_repo.get_next_version_number(asset_id)

    # Generate storage key
    extension = mime_to_extension(inp.content_type)
    storage_key = generate_storage_key(asset_id, version_number, extension)

    # Store in object storage (TA-0008: integrity verified during storage)
    storage.put(
        storage_key,
        data_bytes,
        inp.content_type,
        expected_sha256=sha256,
    )

    # Create version record
    version = AssetVersion(
        id=uuid4(),
        asset_id=asset_id,
        version_number=version_number,
        storage_key=storage_key,
        sha256=sha256,
        size_bytes=size,
        mime_type=inp.content_type,
        filename_original=inp.filename,
        is_latest=True,  # New version becomes latest
        created_by_user_id=inp.user_id,
        created_at=datetime.now(UTC),
    )
    version = version_repo.save(version)

    # Update /latest pointer
    version_repo.set_latest(asset_id, version.id)

    # Update asset storage_path to latest
    asset.storage_path = storage_key
    asset.sha256 = sha256
    asset.size_bytes = size
    asset_repo.save(asset)

    return UploadOutput(
        asset=asset,
        version=version,
        is_new_asset=is_new_asset,
        sha256=sha256,
        storage_key=storage_key,
        errors=[],
        success=True,
    )


def run_set_latest(
    inp: SetLatestVersionInput,
    *,
    asset_repo: AssetRepoPort,
    version_repo: VersionRepoPort,
) -> SetLatestOutput:
    """
    Set a specific version as the latest.

    Args:
        inp: Input containing asset_id and version_id.
        asset_repo: Asset repository port.
        version_repo: Version repository port.

    Returns:
        SetLatestOutput indicating success or failure.
    """
    version = version_repo.get_by_id(inp.version_id)
    if version is None or version.asset_id != inp.asset_id:
        return SetLatestOutput(
            success=False,
            errors=[
                AssetValidationError(
                    code="version_not_found",
                    message=f"Version {inp.version_id} not found for asset {inp.asset_id}",
                    field="version_id",
                )
            ],
        )

    version_repo.set_latest(inp.asset_id, inp.version_id)

    # Update asset storage_path
    asset = asset_repo.get_by_id(inp.asset_id)
    if asset:
        asset.storage_path = version.storage_key
        asset.sha256 = version.sha256
        asset.size_bytes = version.size_bytes
        asset_repo.save(asset)

    return SetLatestOutput(success=True, errors=[])


def run(
    inp: (
        GetAssetInput
        | ListAssetsInput
        | GetVersionInput
        | ListVersionsInput
        | UploadAssetInput
        | SetLatestVersionInput
    ),
    *,
    asset_repo: AssetRepoPort,
    version_repo: VersionRepoPort | None = None,
    storage: StoragePort | None = None,
    rules: RulesPort | None = None,
) -> (
    AssetOutput
    | AssetListOutput
    | VersionOutput
    | VersionListOutput
    | UploadOutput
    | SetLatestOutput
):
    """
    Main entry point for the assets component.

    Dispatches to appropriate handler based on input type.

    Args:
        inp: Input object determining the operation.
        asset_repo: Asset repository port.
        version_repo: Version repository port (required for version operations).
        storage: Storage port (required for upload).
        rules: Optional rules port for configuration.

    Returns:
        Appropriate output object based on input type.
    """
    if isinstance(inp, GetAssetInput):
        return run_get(inp, asset_repo=asset_repo)

    elif isinstance(inp, ListAssetsInput):
        return run_list(inp, asset_repo=asset_repo)

    elif isinstance(inp, GetVersionInput):
        if version_repo is None:
            raise ValueError("VersionRepoPort is required for version operations")
        return run_get_version(inp, version_repo=version_repo)

    elif isinstance(inp, ListVersionsInput):
        if version_repo is None:
            raise ValueError("VersionRepoPort is required for version operations")
        return run_list_versions(inp, version_repo=version_repo)

    elif isinstance(inp, UploadAssetInput):
        if version_repo is None:
            raise ValueError("VersionRepoPort is required for upload operations")
        if storage is None:
            raise ValueError("StoragePort is required for upload operations")
        return run_upload(
            inp,
            asset_repo=asset_repo,
            version_repo=version_repo,
            storage=storage,
            rules=rules,
        )

    elif isinstance(inp, SetLatestVersionInput):
        if version_repo is None:
            raise ValueError("VersionRepoPort is required for set_latest operations")
        return run_set_latest(inp, asset_repo=asset_repo, version_repo=version_repo)

    else:
        raise ValueError(f"Unknown input type: {type(inp)}")


# --- Service Class (Backward Compatibility) ---


class UploadResult:
    """Result from upload operation."""

    def __init__(
        self,
        asset: Asset,
        version: AssetVersion,
        is_new_asset: bool,
        storage_key: str,
        sha256: str,
    ) -> None:
        self.asset = asset
        self.version = version
        self.is_new_asset = is_new_asset
        self.storage_key = storage_key
        self.sha256 = sha256


class AssetService:
    """
    Asset service wrapper for backward compatibility.

    Wraps the functional component API in a class-based interface.
    """

    def __init__(
        self,
        asset_repo: AssetRepoPort,
        version_repo: VersionRepoPort,
        storage: StoragePort,
        kinds: dict[str, AssetKindConfig] | None = None,
    ) -> None:
        self._asset_repo = asset_repo
        self._version_repo = version_repo
        self._storage = storage
        self._kinds = kinds or DEFAULT_ASSET_KINDS.copy()

    def validate_upload(
        self,
        data: bytes,
        content_type: str,
        expected_sha256: str | None = None,
    ) -> tuple[bytes, str, list[AssetValidationError]]:
        """
        Validate upload data.

        Returns (data_bytes, sha256, errors).
        """
        data_bytes, sha256 = compute_sha256(data)
        size = len(data_bytes)

        errors: list[AssetValidationError] = []
        errors.extend(validate_mime_type(content_type, self._kinds))
        errors.extend(validate_size(size, content_type, self._kinds))
        errors.extend(validate_integrity(expected_sha256, sha256))

        return data_bytes, sha256, errors

    def upload(
        self,
        data: bytes,
        mime_type: str,
        filename: str,
        user_id: UUID,
        asset_id: UUID | None = None,
        expected_sha256: str | None = None,
    ) -> tuple[UploadResult | None, list[AssetValidationError]]:
        """
        Upload an asset.

        Returns (result, errors).
        """
        inp = UploadAssetInput(
            data=data,
            content_type=mime_type,
            filename=filename,
            user_id=user_id,
            asset_id=asset_id,
            expected_sha256=expected_sha256,
        )

        output = run_upload(
            inp,
            asset_repo=self._asset_repo,
            version_repo=self._version_repo,
            storage=self._storage,
        )

        if not output.success or output.asset is None or output.version is None:
            return None, output.errors

        result = UploadResult(
            asset=output.asset,
            version=output.version,
            is_new_asset=output.is_new_asset or False,
            storage_key=output.storage_key or "",
            sha256=output.sha256 or "",
        )
        return result, output.errors

    def get_latest_version(self, asset_id: UUID) -> AssetVersion | None:
        """Get the latest version of an asset."""
        return self._version_repo.get_latest(asset_id)

    def set_latest_version(self, asset_id: UUID, version_id: UUID) -> bool:
        """Set a specific version as latest."""
        inp = SetLatestVersionInput(asset_id=asset_id, version_id=version_id)
        output = run_set_latest(
            inp,
            asset_repo=self._asset_repo,
            version_repo=self._version_repo,
        )
        return output.success

    def get_versions(self, asset_id: UUID) -> list[AssetVersion]:
        """Get all versions of an asset."""
        return self._version_repo.get_versions(asset_id)


def create_asset_service(
    asset_repo: AssetRepoPort,
    version_repo: VersionRepoPort,
    storage: StoragePort,
    rules_config: dict[str, Any] | None = None,
) -> AssetService:
    """
    Factory function to create an asset service.

    Args:
        asset_repo: Asset repository.
        version_repo: Version repository.
        storage: Object storage.
        rules_config: Optional rules configuration dict.

    Returns:
        Configured AssetService.
    """
    kinds = DEFAULT_ASSET_KINDS.copy()

    if rules_config and "kinds" in rules_config:
        for kind_name, config in rules_config["kinds"].items():
            kinds[kind_name] = AssetKindConfig(
                kind=kind_name,
                allowed_mime_types=config.get("allowed_mime_types", []),
                max_upload_bytes=config.get("max_upload_bytes", 10_000_000),
            )

    return AssetService(asset_repo, version_repo, storage, kinds)
