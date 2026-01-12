"""
Assets API routes.

Provides endpoints for asset upload, listing, and content retrieval.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from src.api.deps import (
    get_asset_repo,
    get_asset_rules,
    get_current_user,
    get_file_store,
    get_version_repo,
)
from src.api.schemas import AssetResponse
from src.components.assets.component import run_get, run_list, run_set_latest, run_upload
from src.components.assets.models import (
    GetAssetInput,
    ListAssetsInput,
    SetLatestVersionInput,
    UploadAssetInput,
)
from src.domain.entities import User

router = APIRouter()


@router.post("", response_model=AssetResponse)
def upload_asset(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    asset_repo: Any = Depends(get_asset_repo),
    version_repo: Any = Depends(get_version_repo),
    storage: Any = Depends(get_file_store),
    rules: Any = Depends(get_asset_rules),
) -> AssetResponse:
    """Upload a new asset."""
    content = file.file.read()
    mime_type = file.content_type or "application/octet-stream"

    inp = UploadAssetInput(
        data=content,
        filename=file.filename or "unnamed",
        content_type=mime_type,
        user_id=current_user.id,
    )

    result = run_upload(
        inp,
        asset_repo=asset_repo,
        version_repo=version_repo,
        storage=storage,
        rules=rules,
    )

    if not result.success:
        err = result.errors[0]
        status_code = 403 if "not allowed" in err.message else 400
        raise HTTPException(status_code=status_code, detail=err.message)

    return result.asset  # type: ignore


@router.get("", response_model=list[AssetResponse])
def list_assets(
    current_user: User = Depends(get_current_user),
    asset_repo: Any = Depends(get_asset_repo),
) -> list[AssetResponse]:
    """List all assets."""
    inp = ListAssetsInput()
    result = run_list(inp, asset_repo=asset_repo)

    if not result.success:
        raise HTTPException(status_code=400, detail="Failed to list assets")

    return result.items  # type: ignore


@router.get("/{asset_id}/content")
def get_asset_content(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    asset_repo: Any = Depends(get_asset_repo),
    storage: Any = Depends(get_file_store),
) -> Response:
    """Get asset file content."""
    inp = GetAssetInput(asset_id=asset_id)

    # Get asset metadata
    result = run_get(inp, asset_repo=asset_repo)

    if not result.success or not result.asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset = result.asset

    # Retrieve content from storage
    try:
        data = storage.get(asset.storage_path)
        if data is None:
            raise HTTPException(status_code=404, detail="Asset content not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving asset: {e}") from e

    return Response(content=data, media_type=asset.mime_type)


class SetLatestRequest(BaseModel):
    """Request body for setting latest version."""

    version_id: UUID


class SetLatestResponse(BaseModel):
    """Response for set_latest operation."""

    success: bool
    message: str


@router.post("/{asset_id}/set_latest", response_model=SetLatestResponse)
def set_latest_version(
    asset_id: UUID,
    request: SetLatestRequest,
    current_user: User = Depends(get_current_user),
    asset_repo: Any = Depends(get_asset_repo),
    version_repo: Any = Depends(get_version_repo),
) -> SetLatestResponse:
    """
    Set a specific version as the latest for an asset.

    Spec refs: E2.3, TA-0012, TA-0013

    This allows admins to rollback the /latest pointer to a previous version,
    ensuring stable versioned URLs while enabling flexibility in what /latest serves.
    """
    inp = SetLatestVersionInput(
        asset_id=asset_id,
        version_id=request.version_id,
    )

    result = run_set_latest(
        inp,
        asset_repo=asset_repo,
        version_repo=version_repo,
    )

    if not result.success:
        err = result.errors[0] if result.errors else None
        detail = err.message if err else "Failed to set latest version"
        raise HTTPException(status_code=404, detail=detail)

    return SetLatestResponse(
        success=True,
        message=f"Version {request.version_id} is now the latest for asset {asset_id}",
    )
