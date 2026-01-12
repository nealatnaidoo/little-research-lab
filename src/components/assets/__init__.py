"""
Assets component - Asset upload, storage, and versioning.

Spec refs: E2.1, E2.2, E2.3
"""

from .component import (
    DEFAULT_ASSET_KINDS,
    AssetService,
    compute_sha256,
    create_asset_service,
    generate_storage_key,
    get_asset_kind,
    mime_to_extension,
    run,
    run_get,
    run_get_version,
    run_list,
    run_list_versions,
    run_set_latest,
    run_upload,
    validate_integrity,
    validate_mime_type,
    validate_size,
)
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
from .ports import (
    AssetRepoPort,
    RulesPort,
    StoragePort,
    VersionRepoPort,
)

__all__ = [
    # Entry points
    "run",
    "run_get",
    "run_get_version",
    "run_list",
    "run_list_versions",
    "run_set_latest",
    "run_upload",
    # Helper functions
    "compute_sha256",
    "generate_storage_key",
    "get_asset_kind",
    "mime_to_extension",
    "validate_integrity",
    "validate_mime_type",
    "validate_size",
    # Configuration
    "DEFAULT_ASSET_KINDS",
    # Service class (backward compatibility)
    "AssetService",
    "create_asset_service",
    # Input models
    "GetAssetInput",
    "GetVersionInput",
    "ListAssetsInput",
    "ListVersionsInput",
    "SetLatestVersionInput",
    "UploadAssetInput",
    # Output models
    "AssetKindConfig",
    "AssetListOutput",
    "AssetOutput",
    "AssetValidationError",
    "SetLatestOutput",
    "UploadOutput",
    "VersionListOutput",
    "VersionOutput",
    # Ports
    "AssetRepoPort",
    "RulesPort",
    "StoragePort",
    "VersionRepoPort",
]
