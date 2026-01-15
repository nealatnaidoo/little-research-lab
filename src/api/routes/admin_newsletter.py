"""
Admin newsletter subscribers API endpoints.

Spec refs: E16.4
Test assertions: TA-0084, TA-0085, TA-0086, TA-0087

Endpoints:
- GET /api/admin/newsletter/subscribers - List subscribers
- DELETE /api/admin/newsletter/subscribers/{id} - Delete subscriber (GDPR)
- GET /api/admin/newsletter/subscribers/export - Export CSV
"""

from __future__ import annotations

import csv
import io
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.adapters.sqlite_db import SQLiteNewsletterSubscriberRepo
from src.api.deps import get_current_user, get_newsletter_repo
from src.components.newsletter.models import NewsletterSubscriber, SubscriberStatus
from src.domain.entities import User

router = APIRouter()


# --- Request/Response Models ---


class SubscriberResponse(BaseModel):
    """Newsletter subscriber response (tokens hidden for security)."""

    id: str = Field(..., description="Subscriber ID")
    email: str = Field(..., description="Email address")
    status: str = Field(..., description="Subscription status")
    created_at: str = Field(..., description="Creation timestamp")
    confirmed_at: str | None = Field(None, description="Confirmation timestamp")
    unsubscribed_at: str | None = Field(None, description="Unsubscribe timestamp")


class SubscriberListResponse(BaseModel):
    """Paginated list of subscribers."""

    subscribers: list[SubscriberResponse]
    total: int = Field(..., description="Total matching subscribers")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Page size")


class DeleteResponse(BaseModel):
    """Response for delete operation."""

    success: bool
    message: str


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str


# --- Helper Functions ---


def _subscriber_to_response(subscriber: NewsletterSubscriber) -> SubscriberResponse:
    """Convert subscriber entity to response model (no tokens exposed)."""
    return SubscriberResponse(
        id=str(subscriber.id),
        email=subscriber.email,
        status=subscriber.status.value,
        created_at=subscriber.created_at.isoformat(),
        confirmed_at=(
            subscriber.confirmed_at.isoformat() if subscriber.confirmed_at else None
        ),
        unsubscribed_at=(
            subscriber.unsubscribed_at.isoformat()
            if subscriber.unsubscribed_at else None
        ),
    )


# --- Endpoints ---


@router.get(
    "/subscribers",
    response_model=SubscriberListResponse,
    responses={401: {"model": ErrorResponse}},
    summary="List newsletter subscribers",
    description="List newsletter subscribers with pagination and optional status filter.",
)
def list_subscribers(
    status: Literal["pending", "confirmed", "unsubscribed"] | None = Query(
        None, description="Filter by status"
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    user: User = Depends(get_current_user),
    repo: SQLiteNewsletterSubscriberRepo = Depends(get_newsletter_repo),
) -> SubscriberListResponse:
    """
    List newsletter subscribers (TA-0084).

    Requires admin authentication.
    Supports filtering by status and pagination.
    """
    if status:
        # Convert string to enum
        status_enum = SubscriberStatus(status)
        subscribers = repo.list_by_status(status_enum, limit=limit, offset=offset)
        total = repo.count_by_status(status_enum)
    else:
        subscribers = repo.list_all(limit=limit, offset=offset)
        total = repo.count_all()

    return SubscriberListResponse(
        subscribers=[_subscriber_to_response(s) for s in subscribers],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/subscribers/{subscriber_id}",
    response_model=SubscriberResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    summary="Get subscriber details",
    description="Get details of a specific subscriber.",
)
def get_subscriber(
    subscriber_id: UUID,
    user: User = Depends(get_current_user),
    repo: SQLiteNewsletterSubscriberRepo = Depends(get_newsletter_repo),
) -> SubscriberResponse:
    """Get subscriber by ID (TA-0085)."""
    subscriber = repo.get_by_id(subscriber_id)
    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscriber not found",
        )
    return _subscriber_to_response(subscriber)


@router.delete(
    "/subscribers/{subscriber_id}",
    response_model=DeleteResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    summary="Delete subscriber (GDPR)",
    description="Permanently delete a subscriber and all their data.",
)
def delete_subscriber(
    subscriber_id: UUID,
    user: User = Depends(get_current_user),
    repo: SQLiteNewsletterSubscriberRepo = Depends(get_newsletter_repo),
) -> DeleteResponse:
    """
    Delete subscriber permanently (TA-0086).

    Supports GDPR right to erasure.
    """
    # Verify subscriber exists
    subscriber = repo.get_by_id(subscriber_id)
    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscriber not found",
        )

    # Delete
    success = repo.delete(subscriber_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete subscriber",
        )

    return DeleteResponse(
        success=True,
        message=f"Subscriber {subscriber.email} has been permanently deleted",
    )


@router.get(
    "/subscribers/export/csv",
    responses={401: {"model": ErrorResponse}},
    summary="Export subscribers to CSV",
    description="Export all subscribers to CSV format for admin reporting.",
)
def export_subscribers_csv(
    status: Literal["pending", "confirmed", "unsubscribed"] | None = Query(
        None, description="Filter by status"
    ),
    user: User = Depends(get_current_user),
    repo: SQLiteNewsletterSubscriberRepo = Depends(get_newsletter_repo),
) -> StreamingResponse:
    """
    Export subscribers to CSV (TA-0087).

    Returns CSV file with email, status, and timestamps.
    No tokens are included in export (security).
    """
    # Get all matching subscribers (no pagination for export)
    if status:
        status_enum = SubscriberStatus(status)
        subscribers = repo.list_by_status(status_enum, limit=10000, offset=0)
    else:
        subscribers = repo.list_all(limit=10000, offset=0)

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow(["email", "status", "created_at", "confirmed_at", "unsubscribed_at"])

    # Data rows
    for subscriber in subscribers:
        writer.writerow([
            subscriber.email,
            subscriber.status.value,
            subscriber.created_at.isoformat(),
            subscriber.confirmed_at.isoformat() if subscriber.confirmed_at else "",
            subscriber.unsubscribed_at.isoformat() if subscriber.unsubscribed_at else "",
        ])

    # Create streaming response
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=newsletter_subscribers.csv"},
    )


@router.get(
    "/stats",
    responses={401: {"model": ErrorResponse}},
    summary="Get newsletter stats",
    description="Get subscriber statistics by status.",
)
def get_newsletter_stats(
    user: User = Depends(get_current_user),
    repo: SQLiteNewsletterSubscriberRepo = Depends(get_newsletter_repo),
) -> dict[str, int]:
    """Get subscriber counts by status."""
    return {
        "total": repo.count_all(),
        "pending": repo.count_by_status(SubscriberStatus.PENDING),
        "confirmed": repo.count_by_status(SubscriberStatus.CONFIRMED),
        "unsubscribed": repo.count_by_status(SubscriberStatus.UNSUBSCRIBED),
    }
