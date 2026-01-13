"""
Admin Redirects API Routes (E7.1).

Admin endpoints for managing URL redirects.

Spec refs: E7.1, TA-0043, TA-0044, TA-0045
Test assertions:
- TA-0043: Loop detection prevents circular redirects
- TA-0044: Open redirect prevention (internal targets only)
- TA-0045: Chain length validation (max 3)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import get_redirect_repo
from src.components.redirects import (
    Redirect,
    RedirectConfig,
    RedirectService,
    RedirectValidationError,
)

router = APIRouter()


# Shared repository (in production, inject from DI container)
# _redirect_repo = InMemoryRedirectRepo()


class CreateRedirectRequest(BaseModel):
    """Request to create a redirect."""

    source_path: str = Field(..., description="Source path (e.g., /old-page)")
    target_path: str = Field(..., description="Target path (e.g., /new-page)")
    status_code: int | None = Field(None, description="HTTP status code (301/302)")
    notes: str | None = Field(None, description="Admin notes")


class UpdateRedirectRequest(BaseModel):
    """Request to update a redirect."""

    source_path: str | None = Field(None, description="New source path")
    target_path: str | None = Field(None, description="New target path")
    status_code: int | None = Field(None, description="HTTP status code")
    enabled: bool | None = Field(None, description="Enable/disable redirect")
    notes: str | None = Field(None, description="Admin notes")


class RedirectResponse(BaseModel):
    """Redirect response."""

    id: str
    source_path: str
    target_path: str
    status_code: int
    enabled: bool
    created_at: str
    updated_at: str
    notes: str | None = None


class RedirectListResponse(BaseModel):
    """List of redirects response."""

    redirects: list[RedirectResponse]
    count: int


class ValidationErrorResponse(BaseModel):
    """Validation error response."""

    errors: list[dict[str, Any]]


# --- Helper Functions ---


def _redirect_to_response(redirect: Redirect) -> RedirectResponse:
    """Convert Redirect to response model."""
    return RedirectResponse(
        id=str(redirect.id),
        source_path=redirect.source_path,
        target_path=redirect.target_path,
        status_code=redirect.status_code,
        enabled=redirect.enabled,
        created_at=redirect.created_at.isoformat(),
        updated_at=redirect.updated_at.isoformat(),
        notes=redirect.notes,
    )


def _serialize_errors(
    errors: list[RedirectValidationError],
) -> list[dict[str, Any]]:
    """Serialize validation errors."""
    return [
        {
            "code": e.code,
            "message": e.message,
            "field": e.field,
        }
        for e in errors
    ]


# --- Dependencies ---


# Shared repository (in production, inject from DI container)
# Shared repository (in production, inject from DI container)
# _redirect_repo = InMemoryRedirectRepo()


def get_redirect_service(
    repo: Any = Depends(get_redirect_repo),
) -> RedirectService:
    """Get redirect service dependency."""
    return RedirectService(
        repo=repo,
        config=RedirectConfig(),
    )


# --- Routes ---


@router.post(
    "/redirects",
    response_model=RedirectResponse,
    responses={400: {"model": ValidationErrorResponse}},
)
def create_redirect(
    request: CreateRedirectRequest,
    service: RedirectService = Depends(get_redirect_service),
) -> RedirectResponse:
    """
    Create a new redirect.

    Validates:
    - TA-0043: No loops
    - TA-0044: Internal targets only
    - TA-0045: Chain length <= 3
    """
    redirect, errors = service.create(
        source_path=request.source_path,
        target_path=request.target_path,
        status_code=request.status_code,
        notes=request.notes,
    )

    if errors:
        raise HTTPException(
            status_code=400,
            detail={"errors": _serialize_errors(errors)},
        )

    assert redirect is not None
    return _redirect_to_response(redirect)


@router.get("/redirects", response_model=RedirectListResponse)
def list_redirects(
    service: RedirectService = Depends(get_redirect_service),
) -> RedirectListResponse:
    """List all redirects."""
    redirects = service.list_all()
    return RedirectListResponse(
        redirects=[_redirect_to_response(r) for r in redirects],
        count=len(redirects),
    )


@router.get(
    "/redirects/{redirect_id}",
    response_model=RedirectResponse,
    responses={404: {"description": "Redirect not found"}},
)
def get_redirect(
    redirect_id: UUID,
    service: RedirectService = Depends(get_redirect_service),
) -> RedirectResponse:
    """Get a redirect by ID."""
    redirect = service.get(redirect_id)
    if redirect is None:
        raise HTTPException(status_code=404, detail="Redirect not found")
    return _redirect_to_response(redirect)


@router.put(
    "/redirects/{redirect_id}",
    response_model=RedirectResponse,
    responses={
        400: {"model": ValidationErrorResponse},
        404: {"description": "Redirect not found"},
    },
)
def update_redirect(
    redirect_id: UUID,
    request: UpdateRedirectRequest,
    service: RedirectService = Depends(get_redirect_service),
) -> RedirectResponse:
    """
    Update a redirect.

    Validates same constraints as create.
    """
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    redirect, errors = service.update(redirect_id, updates)

    if errors:
        if any(e.code == "not_found" for e in errors):
            raise HTTPException(status_code=404, detail="Redirect not found")
        raise HTTPException(
            status_code=400,
            detail={"errors": _serialize_errors(errors)},
        )

    assert redirect is not None
    return _redirect_to_response(redirect)


@router.delete(
    "/redirects/{redirect_id}",
    responses={404: {"description": "Redirect not found"}},
)
def delete_redirect(
    redirect_id: UUID,
    service: RedirectService = Depends(get_redirect_service),
) -> dict[str, bool]:
    """Delete a redirect."""
    result = service.delete(redirect_id)
    if not result:
        raise HTTPException(status_code=404, detail="Redirect not found")
    return {"deleted": True}


@router.get(
    "/redirects/resolve/{path:path}",
    responses={404: {"description": "No redirect for this path"}},
)
def resolve_redirect(
    path: str,
    service: RedirectService = Depends(get_redirect_service),
) -> dict[str, Any]:
    """
    Resolve a redirect path.

    Returns the final target and status code after following chains.
    """
    # Ensure path starts with /
    if not path.startswith("/"):
        path = "/" + path

    result = service.resolve(path)
    if result is None:
        raise HTTPException(status_code=404, detail="No redirect for this path")

    target, status_code = result
    return {
        "source": path,
        "target": target,
        "status_code": status_code,
    }


@router.post("/redirects/validate")
def validate_redirects(
    service: RedirectService = Depends(get_redirect_service),
) -> dict[str, Any]:
    """
    Validate all existing redirects.

    Returns any redirects with validation issues.
    """
    results = service.validate_all()

    issues = []
    for redirect, errors in results:
        issues.append(
            {
                "redirect_id": str(redirect.id),
                "source_path": redirect.source_path,
                "errors": _serialize_errors(errors),
            }
        )

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "total_checked": len(service.list_all()),
    }
