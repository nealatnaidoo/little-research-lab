"""
Outbound Click Measurement Route (E6.2).

Handles outbound link tracking with UTM preservation.

Spec refs: E6.2, TA-0038
Test assertions:
- TA-0038: Outbound clicks are tracked and UTM params preserved

Key behaviors:
- Track outbound clicks for analytics
- Preserve UTM params in redirect
- Validate target URLs (no open redirects)
- Support optional link IDs for attribution
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

router = APIRouter()


# --- Configuration ---


ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_DOMAINS = {"localhost", "127.0.0.1", "0.0.0.0"}  # Block internal redirects

# UTM parameters to preserve
UTM_PARAMS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")


# --- Validation ---


def is_safe_url(url: str) -> bool:
    """
    Check if URL is safe for redirect.

    Prevents:
    - javascript: URLs
    - data: URLs
    - Internal redirects
    - Missing scheme
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # Must have http/https scheme
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False

    # Must have netloc (domain)
    if not parsed.netloc:
        return False

    # Block internal domains
    domain = parsed.netloc.lower().split(":")[0]  # Remove port
    if domain in BLOCKED_DOMAINS:
        return False

    return True


def preserve_utm_params(
    target_url: str,
    utm_params: dict[str, str],
) -> str:
    """
    Append UTM params to target URL if not already present.

    Preserves any existing params on the target URL.
    """
    if not utm_params:
        return target_url

    parsed = urlparse(target_url)
    existing_params = parse_qs(parsed.query, keep_blank_values=True)

    # Only add UTM params that aren't already on the URL
    params_to_add = {}
    for key, value in utm_params.items():
        if key not in existing_params and value:
            params_to_add[key] = value

    if not params_to_add:
        return target_url

    # Merge with existing params
    if existing_params:
        # Flatten existing params (parse_qs returns lists)
        merged = {k: v[0] if len(v) == 1 else v for k, v in existing_params.items()}
        merged.update(params_to_add)
        new_query = urlencode(merged, doseq=True)
    else:
        new_query = urlencode(params_to_add)

    # Rebuild URL
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )


def extract_utm_from_request(request: Request) -> dict[str, str]:
    """Extract UTM params from request query string."""
    utm_params = {}
    for param in UTM_PARAMS:
        value = request.query_params.get(param)
        if value:
            utm_params[param] = value
    return utm_params


# --- Event Recording (stub for now) ---


class OutboundEventRecorder:
    """Records outbound click events for analytics."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def record(
        self,
        target_url: str,
        link_id: str | None,
        referrer: str | None,
        timestamp: datetime,
        utm_params: dict[str, str],
    ) -> None:
        """Record an outbound click event."""
        self._events.append(
            {
                "event_type": "outbound_click",
                "target_url": target_url,
                "link_id": link_id,
                "referrer": referrer,
                "timestamp": timestamp.isoformat(),
                "utm_params": utm_params,
            }
        )

    def get_events(self) -> list[dict[str, Any]]:
        """Get all recorded events (for testing)."""
        return self._events.copy()

    def clear(self) -> None:
        """Clear recorded events (for testing)."""
        self._events.clear()


# Global event recorder
_event_recorder = OutboundEventRecorder()


def get_event_recorder() -> OutboundEventRecorder:
    """Get the event recorder."""
    return _event_recorder


def reset_event_recorder() -> None:
    """Reset event recorder (for testing)."""
    global _event_recorder
    _event_recorder = OutboundEventRecorder()


# --- Routes ---


@router.get("/go")
def track_outbound_click(
    request: Request,
    url: str = Query(..., description="Target URL to redirect to"),
    link_id: str | None = Query(None, description="Optional link ID for attribution"),
) -> RedirectResponse:
    """
    Track outbound click and redirect (TA-0038).

    Records the click event and redirects to target URL with UTM params preserved.
    """
    # Validate URL
    if not is_safe_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unsafe URL",
        )

    # Extract UTM params from request
    utm_params = extract_utm_from_request(request)

    # Record the click event
    referrer = request.headers.get("referer")  # Note: HTTP header is "referer"
    _event_recorder.record(
        target_url=url,
        link_id=link_id,
        referrer=referrer,
        timestamp=datetime.now(UTC),
        utm_params=utm_params,
    )

    # Preserve UTM params in target URL
    final_url = preserve_utm_params(url, utm_params)

    # Redirect to target
    return RedirectResponse(
        url=final_url,
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/click/{link_id}")
def track_named_link(
    request: Request,
    link_id: str,
    url: str = Query(..., description="Target URL to redirect to"),
) -> RedirectResponse:
    """
    Track click on a named link (TA-0038).

    Simplified route for named links with pre-registered IDs.
    """
    # Validate URL
    if not is_safe_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unsafe URL",
        )

    # Extract UTM params from request
    utm_params = extract_utm_from_request(request)

    # Record the click event
    referrer = request.headers.get("referer")
    _event_recorder.record(
        target_url=url,
        link_id=link_id,
        referrer=referrer,
        timestamp=datetime.now(UTC),
        utm_params=utm_params,
    )

    # Preserve UTM params in target URL
    final_url = preserve_utm_params(url, utm_params)

    # Redirect to target
    return RedirectResponse(
        url=final_url,
        status_code=status.HTTP_302_FOUND,
    )
