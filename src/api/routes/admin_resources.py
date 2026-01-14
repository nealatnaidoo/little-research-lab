"""
Admin Resource PDF Routes (E3.1) - PDF resource management.

Provides CRUD operations for PDF resources with pinned policy support.

Spec refs: E3.1, TA-0014, TA-0015
Test assertions:
- TA-0014: Resource draft persistence
- TA-0015: Pinned policy validation
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_asset_repo, get_current_user, get_policy, get_resource_pdf_repo
from src.api.schemas import (
    ResourcePDFCreateRequest,
    ResourcePDFResponse,
    ResourcePDFUpdateRequest,
)
from src.components.render import (
    ResourcePDFService,
    create_resource_pdf_service,
)
from src.domain.entities import User

router = APIRouter()


# --- Asset Resolver Adapter ---


class AssetResolverAdapter:
    """Adapter to check PDF assets."""

    def __init__(self, asset_repo: Any) -> None:
        self._repo = asset_repo

    def get_asset(self, asset_id: UUID) -> Any | None:
        """Get asset by ID."""
        return self._repo.get_by_id(asset_id)

    def get_version(self, version_id: UUID) -> Any | None:
        """Get version by ID - stub for now."""
        # TODO: Implement when version repo is available
        return None

    def is_pdf(self, asset_id: UUID) -> bool:
        """Check if asset is a PDF."""
        asset = self._repo.get_by_id(asset_id)
        if asset is None:
            return False
        return bool(asset.mime_type == "application/pdf")


# --- Dependencies ---


def get_resource_service(
    repo: Any = Depends(get_resource_pdf_repo),
    asset_repo: Any = Depends(get_asset_repo),
) -> ResourcePDFService:
    """Create ResourcePDFService with dependencies."""
    resolver = AssetResolverAdapter(asset_repo)
    return create_resource_pdf_service(repo=repo, asset_resolver=resolver)


# --- Endpoints ---


@router.get("", response_model=list[ResourcePDFResponse])
def list_resources(
    current_user: User = Depends(get_current_user),
    service: ResourcePDFService = Depends(get_resource_service),
    policy: Any = Depends(get_policy),
) -> list[ResourcePDFResponse]:
    """List all PDF resources."""
    if not policy.check_permission(current_user, current_user.roles, "content:list"):
        raise HTTPException(status_code=403, detail="Access denied")

    resources = service.list_all()
    return [_to_response(r) for r in resources]


@router.get("/{resource_id}", response_model=ResourcePDFResponse)
def get_resource(
    resource_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ResourcePDFService = Depends(get_resource_service),
    policy: Any = Depends(get_policy),
) -> ResourcePDFResponse:
    """Get a specific PDF resource."""
    resource = service.get(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not policy.check_permission(current_user, current_user.roles, "content:read"):
        raise HTTPException(status_code=403, detail="Access denied")

    return _to_response(resource)


@router.post("", response_model=ResourcePDFResponse, status_code=201)
def create_resource(
    req: ResourcePDFCreateRequest,
    current_user: User = Depends(get_current_user),
    service: ResourcePDFService = Depends(get_resource_service),
    policy: Any = Depends(get_policy),
) -> ResourcePDFResponse:
    """Create a new PDF resource draft (TA-0014)."""
    if not policy.check_permission(current_user, current_user.roles, "content:create"):
        raise HTTPException(status_code=403, detail="Not allowed to create content")

    resource, errors = service.create(
        title=req.title,
        slug=req.slug,
        owner_user_id=current_user.id,
        summary=req.summary or "",
        pdf_asset_id=req.pdf_asset_id,
        pdf_version_id=req.pdf_version_id,
        pinned_policy=req.pinned_policy,
        display_title=req.display_title,
        download_filename=req.download_filename,
    )

    if errors:
        raise HTTPException(status_code=400, detail=errors[0].message)

    return _to_response(resource)


@router.put("/{resource_id}", response_model=ResourcePDFResponse)
def update_resource(
    resource_id: UUID,
    req: ResourcePDFUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: ResourcePDFService = Depends(get_resource_service),
    policy: Any = Depends(get_policy),
) -> ResourcePDFResponse:
    """Update an existing PDF resource."""
    existing = service.get(resource_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not policy.check_permission(current_user, current_user.roles, "content:edit"):
        raise HTTPException(status_code=403, detail="Access denied")

    updates = req.model_dump(exclude_unset=True)
    resource, errors = service.update(resource_id, updates)

    if errors:
        raise HTTPException(status_code=400, detail=errors[0].message)

    return _to_response(resource)


@router.post("/{resource_id}/pinned-policy", response_model=ResourcePDFResponse)
def set_pinned_policy(
    resource_id: UUID,
    policy_type: str,  # "pinned" or "latest"
    version_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    service: ResourcePDFService = Depends(get_resource_service),
    policy: Any = Depends(get_policy),
) -> ResourcePDFResponse:
    """Set pinned policy for a resource (TA-0015)."""
    existing = service.get(resource_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not policy.check_permission(current_user, current_user.roles, "content:edit"):
        raise HTTPException(status_code=403, detail="Access denied")

    if policy_type not in ("pinned", "latest"):
        raise HTTPException(status_code=400, detail="Invalid policy type")

    resource, errors = service.set_pinned_policy(
        resource_id,
        policy=policy_type,  # type: ignore
        version_id=version_id,
    )

    if errors:
        raise HTTPException(status_code=400, detail=errors[0].message)

    return _to_response(resource)


@router.delete("/{resource_id}", status_code=204)
def delete_resource(
    resource_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ResourcePDFService = Depends(get_resource_service),
    policy: Any = Depends(get_policy),
) -> None:
    """Delete a PDF resource."""
    existing = service.get(resource_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not policy.check_permission(current_user, current_user.roles, "content:delete"):
        raise HTTPException(status_code=403, detail="Access denied")

    deleted = service.delete(resource_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resource not found")


# --- Helpers ---


def _to_response(resource: Any) -> ResourcePDFResponse:
    """Convert ResourcePDF to response model."""
    return ResourcePDFResponse(
        id=resource.id,
        title=resource.title,
        slug=resource.slug,
        summary=resource.summary,
        status=resource.status,
        owner_user_id=resource.owner_user_id,
        pdf_asset_id=resource.pdf_asset_id,
        pdf_version_id=resource.pdf_version_id,
        pinned_policy=resource.pinned_policy,
        display_title=resource.display_title,
        download_filename=resource.download_filename,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
        published_at=resource.published_at,
    )
