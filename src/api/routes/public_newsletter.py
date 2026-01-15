"""
Public newsletter endpoints for subscription management.

Spec refs: E16.1, E16.2, E16.3
Test assertions: TA-0074 to TA-0083

Endpoints:
- POST /api/public/newsletter/subscribe - Subscribe to newsletter
- GET /newsletter/confirm - Confirm subscription (redirect)
- GET /newsletter/unsubscribe - Unsubscribe (redirect)
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from src.adapters.sqlite_db import SQLiteNewsletterSubscriberRepo
from src.api.deps import (
    InMemoryRateLimiter,
    NewsletterEmailSender,
    get_newsletter_email_sender,
    get_newsletter_repo,
    get_rate_limiter,
)
from src.components.newsletter.models import (
    ConfirmInput,
    NewsletterConfig,
    SubscribeInput,
    UnsubscribeInput,
)

router = APIRouter()


# --- Request/Response Models ---


class SubscribeRequest(BaseModel):
    """Request body for newsletter subscription."""

    email: str = Field(..., description="Email address to subscribe")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Basic email format validation."""
        v = v.strip()
        if not v or "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v


class SubscribeResponse(BaseModel):
    """Response for subscription request."""

    success: bool = Field(..., description="Whether the request was processed successfully")
    message: str = Field(..., description="Human-readable message")


class ConfirmResponse(BaseModel):
    """Response for confirmation request."""

    success: bool
    message: str


class UnsubscribeResponse(BaseModel):
    """Response for unsubscribe request."""

    success: bool
    message: str


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str
    code: str


# --- Helper Functions ---



# --- Helper Functions ---


def get_newsletter_config() -> NewsletterConfig:
    """Get newsletter configuration from environment."""
    base_url = os.environ.get("BASE_URL", "http://localhost:8000")
    site_name = os.environ.get("SITE_NAME", "Little Research Lab")

    return NewsletterConfig(
        base_url=base_url,
        site_name=site_name,
        confirmation_path="/newsletter/confirm",
        unsubscribe_path="/newsletter/unsubscribe",
        confirmation_token_expiry_hours=48,
        rate_limit_per_ip_per_hour=10,
    )


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check X-Forwarded-For header (proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


# --- Subscribe Endpoint (TA-0074, TA-0075, TA-0076) ---


@router.post(
    "/newsletter/subscribe",
    response_model=SubscribeResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    summary="Subscribe to newsletter",
    description="Start the double opt-in subscription flow. Sends confirmation email.",
)
def subscribe_to_newsletter(
    request_body: SubscribeRequest,
    request: Request,
    repo: SQLiteNewsletterSubscriberRepo = Depends(get_newsletter_repo),
    email_sender: NewsletterEmailSender = Depends(get_newsletter_email_sender),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
) -> SubscribeResponse:
    """
    Subscribe to the newsletter (TA-0074, TA-0075, TA-0076).

    Double opt-in flow:
    1. Validate email format and check for disposable domains
    2. Check rate limit (10 attempts per IP per hour)
    3. Create pending subscriber
    4. Send confirmation email
    5. Return success (no email in response per privacy requirements)

    If already subscribed, returns success without revealing subscription status.
    """
    from src.components.newsletter.component import run

    client_ip = get_client_ip(request)
    config = get_newsletter_config()

    input = SubscribeInput(
        email=request_body.email,
        ip_address=client_ip,
    )

    result = run(
        input,
        repo=repo,
        email_sender=email_sender,
        rate_limiter=rate_limiter,
        config=config,
    )

    # Type guard for mypy
    if not isinstance(result, (type(None), bool)) and hasattr(result, "success"):
        if not result.success and hasattr(result, "errors"):
            # Check for rate limit error
            for error in result.errors:
                if error.code == "RATE_LIMIT":
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=error.message,
                    )
                elif error.code in ("EMPTY_EMAIL", "INVALID_FORMAT", "EMAIL_TOO_LONG"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error.message,
                    )
                elif error.code == "DISPOSABLE_EMAIL":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Please use a permanent email address",
                    )

            # Generic error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to process subscription",
            )

    # Always return same message to not reveal subscription status (privacy)
    return SubscribeResponse(
        success=True,
        message="Please check your email to confirm your subscription",
    )


# --- Confirm Endpoint (TA-0077, TA-0078, TA-0079, TA-0080) ---


@router.get(
    "/newsletter/confirm",
    response_model=ConfirmResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or expired token"},
    },
    summary="Confirm newsletter subscription",
    description="Confirm subscription via token from confirmation email.",
)
def confirm_subscription(
    token: str,
    repo: SQLiteNewsletterSubscriberRepo = Depends(get_newsletter_repo),
    email_sender: NewsletterEmailSender = Depends(get_newsletter_email_sender),
) -> ConfirmResponse:
    """
    Confirm newsletter subscription (TA-0077, TA-0078, TA-0079, TA-0080).

    Validates token and transitions subscriber from pending to confirmed.
    Idempotent - already confirmed subscriptions return success.
    """
    from src.components.newsletter.component import run

    config = get_newsletter_config()
    input = ConfirmInput(token=token)
    
    result = run(
        input,
        repo=repo,
        email_sender=email_sender,
        config=config,
    )

    if hasattr(result, "success") and not result.success:
        if hasattr(result, "errors"):
            for error in result.errors:
                if error.code in ("INVALID_TOKEN", "TOKEN_EXPIRED"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error.message,
                    )
                elif error.code == "MISSING_TOKEN":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Confirmation token is required",
                    )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to confirm subscription",
        )

    if hasattr(result, "already_confirmed") and result.already_confirmed:
        return ConfirmResponse(
            success=True,
            message="Your subscription was already confirmed",
        )

    return ConfirmResponse(
        success=True,
        message="Your subscription is now confirmed. Welcome!",
    )


# --- Unsubscribe Endpoint (TA-0081, TA-0082, TA-0083) ---


@router.get(
    "/newsletter/unsubscribe",
    response_model=UnsubscribeResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid token"},
    },
    summary="Unsubscribe from newsletter",
    description="Unsubscribe via token from newsletter emails.",
)
def unsubscribe_from_newsletter(
    token: str,
    repo: SQLiteNewsletterSubscriberRepo = Depends(get_newsletter_repo),
) -> UnsubscribeResponse:
    """
    Unsubscribe from newsletter (TA-0081, TA-0082, TA-0083).

    Validates token and transitions subscriber to unsubscribed.
    Idempotent - already unsubscribed returns success.
    """
    from src.components.newsletter.component import run

    input = UnsubscribeInput(token=token)
    result = run(input, repo=repo)

    if hasattr(result, "success") and not result.success:
        if hasattr(result, "errors"):
            for error in result.errors:
                if error.code == "INVALID_TOKEN":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error.message,
                    )
                elif error.code == "MISSING_TOKEN":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Unsubscribe token is required",
                    )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to process unsubscribe request",
        )

    if hasattr(result, "already_unsubscribed") and result.already_unsubscribed:
        return UnsubscribeResponse(
            success=True,
            message="You were already unsubscribed",
        )

    return UnsubscribeResponse(
        success=True,
        message="You have been unsubscribed. Sorry to see you go!",
    )
