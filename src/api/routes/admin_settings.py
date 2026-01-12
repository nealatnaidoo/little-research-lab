"""
Admin Settings API (E1.1).

Provides GET/PUT endpoints for site settings.

Spec refs: E1.1, TA-0001, TA-0002
Test assertions:
- TA-0001: GET returns settings (fallback defaults if DB row missing)
- TA-0002: PUT validates fields, returns 400 with actionable messages on failure
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.deps import get_current_user, get_site_settings_repo
from src.components.settings import (
    NoOpCacheInvalidator,
    SettingsService,
    ValidationError,
)
from src.domain.entities import SiteSettings, User

router = APIRouter()


# --- Request/Response Models ---


class SettingsResponse(BaseModel):
    """Settings response model."""

    site_title: str
    site_subtitle: str
    avatar_asset_id: str | None
    theme: str
    social_links_json: dict[str, str]
    updated_at: str


class SettingsUpdateRequest(BaseModel):
    """Settings update request model."""

    site_title: str | None = None
    site_subtitle: str | None = None
    avatar_asset_id: str | None = None
    theme: str | None = None
    social_links_json: dict[str, str] | None = None


class ValidationErrorResponse(BaseModel):
    """Validation error response."""

    field: str
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Error response with validation errors."""

    detail: str
    errors: list[ValidationErrorResponse]


# --- Helper Functions ---


def settings_to_response(settings: SiteSettings) -> SettingsResponse:
    """Convert SiteSettings entity to response model."""
    return SettingsResponse(
        site_title=settings.site_title,
        site_subtitle=settings.site_subtitle,
        avatar_asset_id=str(settings.avatar_asset_id) if settings.avatar_asset_id else None,
        theme=settings.theme,
        social_links_json=settings.social_links_json,
        updated_at=settings.updated_at.isoformat(),
    )


def validation_errors_to_response(errors: list[ValidationError]) -> list[ValidationErrorResponse]:
    """Convert validation errors to response models."""
    return [
        ValidationErrorResponse(
            field=e.field,
            code=e.code,
            message=e.message,
        )
        for e in errors
    ]


# --- Dependency Injection ---


def get_settings_service(
    repo: Any = Depends(get_site_settings_repo),
) -> SettingsService:
    """Create SettingsService with dependencies."""
    return SettingsService(
        repo=repo,
        cache_invalidator=NoOpCacheInvalidator(),
    )


# --- Endpoints ---


@router.get(
    "",
    response_model=SettingsResponse,
    summary="Get site settings",
    description="Get current site settings. Returns defaults if not configured (TA-0001).",
)
def get_settings(
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    """
    Get site settings.

    Returns current settings, or fallback defaults if DB row doesn't exist.
    Requires authenticated admin.
    """
    settings = service.get()
    return settings_to_response(settings)


@router.put(
    "",
    response_model=SettingsResponse,
    summary="Update site settings",
    description="Update site settings with validation (TA-0002).",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Validation errors with actionable messages",
        },
    },
)
def update_settings(
    request: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> Any:
    """
    Update site settings.

    Validates fields before persisting. Returns 400 with actionable
    error messages if validation fails (TA-0002).
    """
    # Build updates dict from request (only include provided fields)
    updates: dict[str, Any] = {}
    if request.site_title is not None:
        updates["site_title"] = request.site_title
    if request.site_subtitle is not None:
        updates["site_subtitle"] = request.site_subtitle
    if request.avatar_asset_id is not None:
        # Convert string to UUID or None
        from uuid import UUID

        try:
            avatar_id = UUID(request.avatar_asset_id) if request.avatar_asset_id else None
            updates["avatar_asset_id"] = avatar_id
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid avatar_asset_id format",
            ) from err
    if request.theme is not None:
        updates["theme"] = request.theme
    if request.social_links_json is not None:
        updates["social_links_json"] = request.social_links_json

    # Apply updates
    settings, errors = service.update(updates)

    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Validation failed",
            headers={"X-Validation-Errors": "true"},
        )

    return settings_to_response(settings)
