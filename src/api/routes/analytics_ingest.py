"""
Analytics Ingestion API Routes (E6.1).

Public endpoint for analytics event ingestion.

Spec refs: E6.1, TA-0034, TA-0035, R4
Test assertions:
- TA-0034: Event validation (allowed types, fields)
- TA-0035: PII prevention (forbidden fields blocked)
"""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from src.adapters.sqlite_db import SQLiteEngagementRepo
from src.components.analytics import (
    AnalyticsIngestionService,
    IngestionConfig,
    InMemoryEventStore,
)
from src.components.engagement import (
    CalculateEngagementInput,
)
from src.components.engagement import (
    run_calculate as calculate_engagement,
)

router = APIRouter()

# Database path for engagement repo
_db_path = os.environ.get("DATABASE_URL", "lrl.db")
if _db_path.startswith("sqlite:///"):
    _db_path = _db_path.replace("sqlite:///", "")


# --- Request/Response Models ---


class EventRequest(BaseModel):
    """Analytics event request."""

    event_type: str = Field(..., description="Event type (page_view, etc.)")
    ts: str | int | float | None = Field(None, description="Event timestamp")
    path: str | None = Field(None, description="Page path")
    content_id: str | None = Field(None, description="Content UUID")
    link_id: str | None = Field(None, description="Link identifier")
    asset_id: str | None = Field(None, description="Asset UUID")
    asset_version_id: str | None = Field(None, description="Asset version UUID")
    referrer: str | None = Field(None, description="Referrer URL")
    utm_source: str | None = Field(None, description="UTM source")
    utm_medium: str | None = Field(None, description="UTM medium")
    utm_campaign: str | None = Field(None, description="UTM campaign")
    utm_content: str | None = Field(None, description="UTM content")
    utm_term: str | None = Field(None, description="UTM term")
    ua_class: str | None = Field(None, description="User agent class")
    # Engagement tracking fields (E14)
    time_on_page: int | float | None = Field(None, description="Time on page in seconds")
    scroll_depth: int | float | None = Field(None, description="Max scroll depth 0-100%")

    model_config = ConfigDict(extra="allow")


class EventResponse(BaseModel):
    """Success response."""

    ok: bool = True


class ErrorResponse(BaseModel):
    """Error response."""

    ok: bool = False
    errors: list[dict[str, Any]]


# --- Dependencies ---


# Shared event store (in production, use a proper store)
_event_store = InMemoryEventStore()


def get_ingestion_service() -> AnalyticsIngestionService:
    """Get analytics ingestion service dependency."""
    return AnalyticsIngestionService(
        event_store=_event_store,
        config=IngestionConfig(),
    )


def get_client_key(request: Request) -> str:
    """Extract client key from request for rate limiting."""
    # Use X-Forwarded-For if behind proxy, otherwise client host
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# --- Routes ---


@router.post(
    "/event",
    response_model=EventResponse,
    responses={
        400: {"model": ErrorResponse},
        429: {"description": "Rate limit exceeded"},
    },
)
def ingest_event(
    request: Request,
    body: EventRequest,
    service: AnalyticsIngestionService = Depends(get_ingestion_service),
) -> EventResponse | ErrorResponse:
    """
    Ingest an analytics event.

    TA-0034: Validates event type and allowed fields.
    TA-0035: Rejects forbidden fields (PII).

    Rate limited: 600 requests per 60 seconds per client.
    """
    client_key = get_client_key(request)

    # Convert Pydantic model to dict (includes extra fields for validation)
    data = body.model_dump(exclude_none=False)

    # Remove None values but keep explicit ones for validation
    data = {k: v for k, v in data.items() if v is not None}

    event, errors = service.ingest(data, client_key=client_key)

    if errors:
        # Check for rate limit error
        if any(e.code == "rate_limit_exceeded" for e in errors):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
            )

        # Return validation errors
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "errors": [
                    {
                        "code": e.code,
                        "message": e.message,
                        "field": e.field_name,
                    }
                    for e in errors
                ],
            },
        )

    # Process engagement data if present (E14)
    if body.time_on_page is not None and body.scroll_depth is not None and body.content_id:
        try:
            engagement_repo = SQLiteEngagementRepo(_db_path)
            engagement_input = CalculateEngagementInput(
                content_id=UUID(body.content_id),
                time_on_page_seconds=float(body.time_on_page),
                scroll_depth_percent=float(body.scroll_depth),
            )
            calculate_engagement(engagement_input, repo=engagement_repo)
        except Exception:
            # Don't fail the request if engagement tracking fails
            pass

    return EventResponse(ok=True)


@router.post("/batch", response_model=dict[str, Any])
def ingest_batch(
    request: Request,
    events: list[dict[str, Any]],
    service: AnalyticsIngestionService = Depends(get_ingestion_service),
) -> dict[str, Any]:
    """
    Ingest multiple analytics events.

    Returns results for each event.
    """
    client_key = get_client_key(request)

    results = []
    for i, event_data in enumerate(events):
        event, errors = service.ingest(event_data, client_key=client_key)
        if errors:
            results.append(
                {
                    "index": i,
                    "ok": False,
                    "errors": [
                        {"code": e.code, "message": e.message, "field": e.field_name}
                        for e in errors
                    ],
                }
            )
        else:
            results.append({"index": i, "ok": True})

    return {
        "ok": all(r["ok"] for r in results),
        "results": results,
    }
