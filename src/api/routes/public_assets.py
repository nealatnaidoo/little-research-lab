"""
Public Asset Serving Routes (E2.2) - Versioned asset serving with correct headers.

Serves immutable asset bytes with proper cache headers.

Spec refs: E2.2, TA-0009, TA-0010, TA-0011, R2
Test assertions:
- TA-0009: Headers correctness (ETag, Cache-Control, Content-Disposition)
- TA-0010: ETag stable (same content = same ETag)
- TA-0011: Download disposition (?download=1 triggers attachment)

Headers:
- ETag: Based on SHA256 hash (immutable)
- Cache-Control: Immutable, long max-age for versioned routes
- Content-Disposition: inline (default) or attachment (?download=1)
- X-Content-SHA256: SHA256 hash for integrity verification
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

router = APIRouter()


# --- Constants ---

# Cache for 1 year (immutable content)
CACHE_MAX_AGE = 31536000  # 365 days in seconds
CACHE_CONTROL_IMMUTABLE = f"public, max-age={CACHE_MAX_AGE}, immutable"

# Cache for /latest (short TTL since pointer can change)
CACHE_CONTROL_LATEST = "public, max-age=60, must-revalidate"


# --- Mock Storage (to be replaced with real implementation) ---


class MockStorage:
    """Mock storage for testing."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[bytes, str]] = {}  # key -> (data, mime_type)

    def get(self, key: str) -> tuple[bytes, str] | None:
        """Get data and mime type by key."""
        return self._data.get(key)

    def put(self, key: str, data: bytes, mime_type: str) -> None:
        """Store data."""
        self._data[key] = (data, mime_type)


class MockVersionRepo:
    """Mock version repository."""

    def __init__(self) -> None:
        self._versions: dict[UUID, Any] = {}
        self._latest: dict[UUID, UUID] = {}

    def get_by_id(self, version_id: UUID) -> Any:
        return self._versions.get(version_id)

    def get_latest(self, asset_id: UUID) -> Any:
        if asset_id in self._latest:
            return self._versions.get(self._latest[asset_id])
        return None

    def add(self, version: Any) -> None:
        self._versions[version.id] = version

    def set_latest(self, asset_id: UUID, version_id: UUID) -> None:
        self._latest[asset_id] = version_id


# Singleton mocks
_mock_storage = MockStorage()
_mock_version_repo = MockVersionRepo()


def get_storage() -> MockStorage:
    return _mock_storage


def get_version_repo() -> MockVersionRepo:
    return _mock_version_repo


# --- Helper Functions ---


def build_etag(sha256: str) -> str:
    """
    Build ETag from SHA256 hash (TA-0010).

    Uses weak ETag format with SHA256 for stability.
    """
    # Use first 16 chars of SHA256 for reasonable ETag length
    return f'"{sha256[:16]}"'


def build_content_disposition(
    filename: str,
    download: bool = False,
) -> str:
    """
    Build Content-Disposition header (TA-0011).

    - inline: Display in browser (default)
    - attachment: Prompt download (?download=1)
    """
    # Sanitize filename for header
    safe_filename = filename.replace('"', '\\"').replace("\n", "_")

    if download:
        return f'attachment; filename="{safe_filename}"'
    return f'inline; filename="{safe_filename}"'


def check_if_none_match(request: Request, etag: str) -> bool:
    """
    Check If-None-Match header for conditional GET.

    Returns True if client has cached version (304 should be returned).
    """
    if_none_match = request.headers.get("if-none-match")
    if if_none_match:
        # Handle multiple ETags (comma-separated)
        client_etags = [e.strip() for e in if_none_match.split(",")]
        return etag in client_etags or "*" in client_etags
    return False


# --- Endpoints ---


@router.get(
    "/{asset_id}/v/{version_id}",
    summary="Get versioned asset",
    description="Serve asset by version ID with immutable cache headers (TA-0009, TA-0010).",
    responses={
        200: {
            "description": "Asset content with proper headers",
            "headers": {
                "ETag": {"description": "Content hash for caching"},
                "Cache-Control": {"description": "Immutable cache directive"},
                "Content-Disposition": {"description": "Inline or attachment"},
                "X-Content-SHA256": {"description": "Full SHA256 hash"},
            },
        },
        304: {"description": "Not modified (client has cached version)"},
        404: {"description": "Version not found"},
    },
)
def get_versioned_asset(
    request: Request,
    asset_id: UUID,
    version_id: UUID,
    download: bool = Query(False, description="Trigger download (TA-0011)"),
    storage: MockStorage = Depends(get_storage),
    version_repo: MockVersionRepo = Depends(get_version_repo),
) -> Response:
    """
    Serve asset version with proper headers.

    Headers (TA-0009):
    - ETag: Based on SHA256 (stable per TA-0010)
    - Cache-Control: immutable for versioned routes
    - Content-Disposition: inline or attachment (TA-0011)
    - X-Content-SHA256: Full hash for verification
    """
    # Get version metadata
    version = version_repo.get_by_id(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Verify version belongs to asset
    if version.asset_id != asset_id:
        raise HTTPException(status_code=404, detail="Version not found")

    # Build ETag (TA-0010: stable based on content hash)
    etag = build_etag(version.sha256)

    # Check conditional GET (304 Not Modified)
    if check_if_none_match(request, etag):
        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": CACHE_CONTROL_IMMUTABLE,
            },
        )

    # Get content from storage
    stored = storage.get(version.storage_key)
    if not stored:
        raise HTTPException(status_code=404, detail="Asset content not found")

    data, _ = stored

    # Build headers (TA-0009)
    headers = {
        "ETag": etag,
        "Cache-Control": CACHE_CONTROL_IMMUTABLE,
        "Content-Disposition": build_content_disposition(
            version.filename_original, download=download
        ),
        "X-Content-SHA256": version.sha256,
        "Content-Length": str(len(data)),
    }

    return Response(
        content=data,
        media_type=version.mime_type,
        headers=headers,
    )


@router.get(
    "/{asset_id}/latest",
    summary="Get latest asset version",
    description="Serve latest version of asset (shorter cache).",
    responses={
        200: {"description": "Asset content"},
        304: {"description": "Not modified"},
        404: {"description": "Asset or version not found"},
    },
)
def get_latest_asset(
    request: Request,
    asset_id: UUID,
    download: bool = Query(False, description="Trigger download"),
    storage: MockStorage = Depends(get_storage),
    version_repo: MockVersionRepo = Depends(get_version_repo),
) -> Response:
    """
    Serve latest version of asset.

    Uses shorter cache TTL since /latest pointer can change.
    """
    # Get latest version
    version = version_repo.get_latest(asset_id)
    if not version:
        raise HTTPException(status_code=404, detail="No versions found")

    # Build ETag
    etag = build_etag(version.sha256)

    # Check conditional GET
    if check_if_none_match(request, etag):
        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": CACHE_CONTROL_LATEST,
            },
        )

    # Get content from storage
    stored = storage.get(version.storage_key)
    if not stored:
        raise HTTPException(status_code=404, detail="Asset content not found")

    data, _ = stored

    # Headers for /latest (shorter cache)
    headers = {
        "ETag": etag,
        "Cache-Control": CACHE_CONTROL_LATEST,
        "Content-Disposition": build_content_disposition(
            version.filename_original, download=download
        ),
        "X-Content-SHA256": version.sha256,
        "Content-Length": str(len(data)),
    }

    return Response(
        content=data,
        media_type=version.mime_type,
        headers=headers,
    )


# --- Utility Functions for Testing ---


def get_asset_headers(
    sha256: str,
    filename: str,
    download: bool = False,
    is_latest: bool = False,
) -> dict[str, str]:
    """
    Get expected headers for asset serving.

    Useful for testing header correctness (TA-0009).
    """
    return {
        "ETag": build_etag(sha256),
        "Cache-Control": CACHE_CONTROL_LATEST if is_latest else CACHE_CONTROL_IMMUTABLE,
        "Content-Disposition": build_content_disposition(filename, download),
        "X-Content-SHA256": sha256,
    }
