from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from src.api.deps import get_asset_service, get_current_user
from src.api.schemas import AssetResponse
from src.domain.entities import User
from src.services.asset import AssetService

router = APIRouter()


@router.post("", response_model=AssetResponse)
def upload_asset(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: AssetService = Depends(get_asset_service),
) -> AssetResponse:
    """Upload a new asset."""
    try:
        content = file.file.read()
        mime_type = file.content_type or "application/octet-stream"

        asset = service.upload_asset(
            user=current_user,
            filename=file.filename or "unnamed",
            mime_type=mime_type,
            data=content,
            visibility="private",
        )
        return asset  # type: ignore[return-value]
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not allowed to upload assets") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get("", response_model=list[AssetResponse])
def list_assets(
    current_user: User = Depends(get_current_user),
    service: AssetService = Depends(get_asset_service),
) -> list[AssetResponse]:
    """List all assets."""
    try:
        assets = service.list_assets(user=current_user)
        return assets  # type: ignore[return-value]
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not allowed to list assets") from None


@router.get("/{asset_id}/content")
def get_asset_content(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AssetService = Depends(get_asset_service),
) -> Response:
    """Get asset file content."""
    try:
        asset = service.get_asset_meta(current_user, asset_id)
        data = service.get_asset_content(current_user, asset_id)
        return Response(content=data, media_type=asset.mime_type)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not allowed to access asset") from None
    except ValueError:
        raise HTTPException(status_code=404, detail="Asset not found") from None
