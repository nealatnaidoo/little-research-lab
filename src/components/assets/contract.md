## COMPONENT_ID
C3-assets

## PURPOSE
Manage asset upload, storage, and versioning with immutable blob storage.
Handles MIME type validation, size limits, and SHA256 integrity verification.

## INPUTS
- `UploadAssetInput`: Upload new asset (data, filename, content_type)
- `GetAssetInput`: Retrieve asset by ID
- `ListAssetsInput`: List assets with filters
- `CreateVersionInput`: Create new version of existing asset
- `SetLatestVersionInput`: Set a specific version as the latest

## OUTPUTS
- `AssetOutput`: Asset metadata with storage path
- `AssetListOutput`: List of assets with pagination
- `UploadOutput`: Upload result with SHA256 and version info
- `SetLatestOutput`: Result of setting latest version

## DEPENDENCIES (PORTS)
- `AssetRepoPort`: Database access for asset metadata
- `VersionRepoPort`: Database access for version tracking
- `StoragePort`: Object storage for blob data
- `RulesPort`: Asset rules (MIME types, size limits)

## SIDE EFFECTS
- Database write for metadata
- Object storage write for blob data
- Version increment on new uploads

## INVARIANTS
- I1: MIME type must be in allowlist (TA-0006)
- I2: Size must not exceed limit (TA-0007)
- I3: SHA256 verified on upload (TA-0008)
- I4: Blobs are immutable once stored
- I5: Versions are append-only

## ERROR SEMANTICS
- Returns errors for validation failures (MIME, size)
- Throws for storage/infrastructure errors
- SHA256 mismatch returns specific error

## TESTS
- `tests/unit/test_assets.py`: TA-0006, TA-0007, TA-0008 (tests)
  - MIME type allowlist enforcement
  - Size limit enforcement
  - SHA256 integrity verification

## EVIDENCE
- `artifacts/pytest-assets-report.json`
