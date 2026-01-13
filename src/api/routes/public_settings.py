"""Public settings endpoint for exposing site configuration to visitors."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.adapters.sqlite.repos import SQLiteSiteSettingsRepo
from src.api.deps import get_site_settings_repo
from src.components.settings.component import run_get
from src.components.settings.models import GetSettingsInput

router = APIRouter()


class PublicSettingsResponse(BaseModel):
    """Public subset of site settings - safe to expose without authentication."""

    site_title: str
    site_subtitle: str
    theme: str
    social_links_json: dict[str, str]


@router.get("/settings", response_model=PublicSettingsResponse)
def get_public_settings(
    repo: SQLiteSiteSettingsRepo = Depends(get_site_settings_repo),
) -> PublicSettingsResponse:
    """
    Get public site settings.

    Returns site configuration that is safe to expose to unauthenticated visitors:
    - site_title: Display name of the site
    - site_subtitle: Tagline/description
    - theme: Default theme preference (light/dark/system)
    - social_links_json: Social media links for footer

    Does NOT return sensitive fields like avatar_asset_id or internal configuration.
    """
    # Use settings component to get settings (with defaults if not configured)
    result = run_get(GetSettingsInput(), repo=repo)

    settings = result.settings

    return PublicSettingsResponse(
        site_title=settings.site_title,
        site_subtitle=settings.site_subtitle,
        theme=settings.theme,
        social_links_json=settings.social_links_json,
    )
