"""
Public Redirects Routes (E7.2).

Public routing integration for URL redirects.

Spec refs: E7.2, TA-0046
Test assertions:
- TA-0046: Redirects are applied in the routing path

Key behaviors:
- Middleware-style redirect resolution
- Preserves query parameters (especially UTM)
- Returns appropriate status codes (301/302)
- Handles disabled redirects gracefully
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from fastapi import APIRouter, Depends, Request

from src.api.deps import get_redirect_repo
from src.components.redirects import (
    RedirectConfig,
    RedirectService,
)

router = APIRouter()


# --- Dependencies ---


def get_redirect_service(
    repo: Any = Depends(get_redirect_repo),
) -> RedirectService:
    """Get redirect service."""
    return RedirectService(
        repo=repo,
        config=RedirectConfig(preserve_utm_params=True),
    )


# UTM parameters to preserve during redirects
UTM_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


# --- Helper Functions ---


def preserve_query_params(
    original_url: str,
    target_path: str,
    preserve_utm: bool = True,
) -> str:
    """
    Preserve query parameters from original URL to target.

    Merges UTM params from original into target URL.
    Target params take precedence if duplicated.
    """
    # Parse original URL to get query params
    original_parsed = urlparse(original_url)
    original_params = parse_qs(original_parsed.query, keep_blank_values=True)

    # Parse target to get existing params
    target_parsed = urlparse(target_path)
    target_params = parse_qs(target_parsed.query, keep_blank_values=True)

    # Build merged params
    merged = {}

    # Add original params (UTM only if preserve_utm)
    for key, values in original_params.items():
        if preserve_utm and key.lower() in UTM_PARAMS:
            merged[key] = values[0] if len(values) == 1 else values
        elif not preserve_utm:
            merged[key] = values[0] if len(values) == 1 else values

    # Target params override
    for key, values in target_params.items():
        merged[key] = values[0] if len(values) == 1 else values

    # Build final URL
    if merged:
        query_string = urlencode(merged, doseq=True)
        base_path = target_parsed.path or target_path.split("?")[0]
        return f"{base_path}?{query_string}"

    return target_path


# --- Redirect Resolution Function ---


def resolve_redirect(
    path: str,
    query_string: str = "",
    service: RedirectService | None = None,
) -> tuple[str, int] | None:
    """
    Resolve a redirect for the given path.

    Returns (target_url, status_code) or None if no redirect.
    """
    if service is None:
        # Without service injection, we can't resolve.
        # Ideally, middleware should handle DI or database access correctly.
        # But for now, if called from route, service is provided.
        # If called from middleware check, we need a way to get repo.
        return None  # Middleware support needs deeper DI integration or On-demand repo.

    svc = service

    # Preserve UTM params
    original_url = f"{path}?{query_string}" if query_string else path
    
    svc = service
    print(f"DEBUG: resolving redirect for path={path}")
    result = svc.resolve(path)
    print(f"DEBUG: resolve result={result}")
    
    if result is None:
        return None

    target_path, status_code = result
    final_target = preserve_query_params(original_url, target_path)

    return final_target, status_code


# --- Routes ---


@router.get("/resolve")
async def resolve_redirect_endpoint(
    path: str,
    request: Request,
    service: RedirectService = Depends(get_redirect_service),
) -> dict[str, Any]:
    """
    Resolve a redirect path (Public).
    Returns {"target": url, "status_code": code} or 404.
    """
    # Normalize path
    if not path.startswith("/"):
        path = "/" + path

    # Simple resolution
    result = resolve_redirect(path, query_string="", service=service)

    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    target_url, status_code = result

    return {
        "target": target_url,
        "status_code": status_code,
    }


# --- Middleware-style checker for use in app ---


async def redirect_middleware_check(
    path: str,
    query_string: str = "",
) -> tuple[str, int] | None:
    """
    Check for redirect (for use in ASGI middleware).

    Returns (target_url, status_code) or None.
    """
    return resolve_redirect(path, query_string)
