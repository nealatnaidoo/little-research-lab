"""
Public sharing endpoint for generating share URLs with UTM tracking.

Spec refs: E15.2
Test assertions: TA-0070, TA-0071

Endpoint: POST /api/public/share/generate
- Public route (no auth required)
- Generates platform-specific share URLs with UTM params
"""

from __future__ import annotations

import os
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.adapters.sqlite.repos import SQLiteContentRepo, SQLiteSiteSettingsRepo
from src.api.deps import get_content_repo, get_site_settings_repo
from src.components.content.component import run_get
from src.components.content.models import GetContentInput
from src.components.settings.component import run_get as run_get_settings
from src.components.settings.models import GetSettingsInput
from src.components.sharing import GenerateShareUrlOutput
from src.components.sharing.models import SharingPlatform

router = APIRouter()


# --- Request/Response Models ---


class GenerateShareUrlRequest(BaseModel):
    """Request body for share URL generation."""

    content_id: UUID = Field(..., description="ID of the content to share")
    platform: Literal["twitter", "linkedin", "facebook", "native"] = Field(
        ..., description="Target sharing platform"
    )


class GenerateShareUrlResponse(BaseModel):
    """Response containing the generated share URL."""

    share_url: str = Field(..., description="Platform-specific share URL with UTM params")
    platform: str = Field(..., description="Target platform")
    utm_source: str = Field(..., description="UTM source value")
    utm_medium: str = Field(..., description="UTM medium value")
    utm_campaign: str = Field(..., description="UTM campaign value (content slug)")


class ShareUrlErrorResponse(BaseModel):
    """Error response for share URL generation."""

    detail: str
    code: str


# --- Endpoint ---


@router.post(
    "/share/generate",
    response_model=GenerateShareUrlResponse,
    responses={
        404: {"model": ShareUrlErrorResponse, "description": "Content not found"},
        400: {"model": ShareUrlErrorResponse, "description": "Invalid request"},
    },
    summary="Generate share URL",
    description="Generate a platform-specific share URL with UTM tracking parameters.",
)
def generate_share_url_endpoint(
    request: GenerateShareUrlRequest,
    content_repo: SQLiteContentRepo = Depends(get_content_repo),
    settings_repo: SQLiteSiteSettingsRepo = Depends(get_site_settings_repo),
) -> GenerateShareUrlResponse:
    """
    Generate a share URL for content.

    Creates a platform-specific share URL with UTM parameters for attribution tracking.
    The URL can be used to share content on Twitter, LinkedIn, Facebook, or via
    the native share API.

    - **content_id**: UUID of the content item to share
    - **platform**: Target platform (twitter, linkedin, facebook, native)

    Returns a share URL that includes:
    - UTM source (platform name)
    - UTM medium (social)
    - UTM campaign (content slug)
    """
    # 1. Look up content
    content_result = run_get(GetContentInput(content_id=request.content_id), repo=content_repo)

    if not content_result.success or not content_result.content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    content = content_result.content

    # 2. Get site settings for base URL
    settings_result = run_get_settings(GetSettingsInput(), repo=settings_repo)
    settings = settings_result.settings

    # Get base URL from settings or environment
    base_url = settings.social_links_json.get("base_url") if settings.social_links_json else None
    if not base_url:
        # Fallback to environment variable
        base_url = os.environ.get("BASE_URL", "http://localhost:8000")

    # 3. Determine content path prefix based on type
    content_path_prefix = "/r" if content.type == "resource_pdf" else "/p"

    # 4. Generate share URL via atomic component run()
    from src.components.sharing.component import run
    from src.components.sharing.models import GenerateShareUrlInput

    # Simple adapter since we don't have injected rules port in API yet
    # In a full DI setup, we'd inject SharingRulesPort.
    # For now, we rely on default rules behavior or construct a simple port.
    class DefaultSharingRules:
        def is_enabled(self) -> bool:
            return True

        def get_platforms(self) -> tuple[SharingPlatform, ...]:
            return ("twitter", "linkedin", "facebook", "native")

        def get_utm_medium(self) -> str:
            return "social"

        def get_utm_source_for_platform(self, platform: SharingPlatform) -> str:
            return platform

        def get_utm_campaign_source(self) -> str:
            return "slug"

        def prefer_native_share_on_mobile(self) -> bool:
            return False

    rules_port = DefaultSharingRules()

    platform: SharingPlatform = request.platform
    
    inp = GenerateShareUrlInput(
        content_slug=content.slug,
        platform=platform,
        base_url=base_url,
        content_path_prefix=content_path_prefix,
        title=content.title,
        description=content.summary or "",
    )
    
    result = run(inp, rules=rules_port)

    if not isinstance(result, GenerateShareUrlOutput) or not result.success:
        error_messages = [e.message for e in result.errors] if hasattr(result, 'errors') else []
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(error_messages) if error_messages else "Failed to generate share URL",
        )

    return GenerateShareUrlResponse(
        share_url=result.share_url or "",
        platform=result.platform,
        utm_source=result.utm_source,
        utm_medium=result.utm_medium,
        utm_campaign=result.utm_campaign,
    )


# --- Additional endpoint for getting shareable platforms ---


class SharePlatformsResponse(BaseModel):
    """Response containing available sharing platforms."""

    platforms: list[str] = Field(..., description="List of supported sharing platforms")


@router.get(
    "/share/platforms",
    response_model=SharePlatformsResponse,
    summary="Get available share platforms",
    description="Get list of supported sharing platforms.",
)
def get_share_platforms() -> SharePlatformsResponse:
    """
    Get available sharing platforms.

    Returns the list of platforms supported for share URL generation.
    """
    return SharePlatformsResponse(
        platforms=["twitter", "linkedin", "facebook", "native"]
    )
