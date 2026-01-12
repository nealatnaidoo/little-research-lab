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

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from src.components.redirects import (
    Redirect,
    RedirectConfig,
    RedirectService,
)

router = APIRouter()


# --- Mock Repository for Dependencies ---


class InMemoryRedirectRepo:
    """In-memory redirect repository."""

    def __init__(self) -> None:
        self._redirects: dict[Any, Redirect] = {}
        self._by_source: dict[str, Redirect] = {}

    def get_by_id(self, redirect_id: Any) -> Redirect | None:
        return self._redirects.get(redirect_id)

    def get_by_source(self, source_path: str) -> Redirect | None:
        return self._by_source.get(source_path.lower())

    def save(self, redirect: Redirect) -> Redirect:
        self._redirects[redirect.id] = redirect
        self._by_source[redirect.source_path.lower()] = redirect
        return redirect

    def delete(self, redirect_id: Any) -> None:
        redirect = self._redirects.pop(redirect_id, None)
        if redirect:
            self._by_source.pop(redirect.source_path.lower(), None)

    def list_all(self) -> list[Redirect]:
        return list(self._redirects.values())


# --- Configuration ---


UTM_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
    }
)


# --- Dependencies ---


# Shared repository (in production, inject from DI container)
_redirect_repo = InMemoryRedirectRepo()
_redirect_service = RedirectService(
    repo=_redirect_repo,
    config=RedirectConfig(preserve_utm_params=True),
)


def get_redirect_service() -> RedirectService:
    """Get redirect service."""
    return _redirect_service


def get_redirect_repo() -> InMemoryRedirectRepo:
    """Get redirect repository for testing."""
    return _redirect_repo


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
    svc = service or _redirect_service

    result = svc.resolve(path)
    if result is None:
        return None

    target_path, status_code = result

    # Preserve UTM params
    original_url = f"{path}?{query_string}" if query_string else path
    final_target = preserve_query_params(original_url, target_path)

    return final_target, status_code


# --- Routes ---


@router.get("/{path:path}")
async def handle_redirect(
    path: str,
    request: Request,
) -> RedirectResponse:
    """
    Handle public redirects (TA-0046).

    Checks if the path has a redirect configured and returns
    the appropriate redirect response.
    """
    # Normalize path
    if not path.startswith("/"):
        path = "/" + path

    # Get query string
    query_string = str(request.query_params) if request.query_params else ""

    # Resolve redirect
    result = resolve_redirect(path, query_string)

    if result is None:
        # No redirect - in a real app, this would fall through to
        # the next route handler. For now, return 404.
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not found")

    target_url, status_code = result

    return RedirectResponse(
        url=target_url,
        status_code=status_code,
    )


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
